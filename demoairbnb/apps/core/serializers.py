from __future__ import annotations

import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .constants import SystemRole, validate_permissions_map
from .integrations import GoogleCalendarCredential
from .models import (
    InvitationCode,
    InvitationCodePurpose,
    Tenant,
    TenantRole,
    User,
)
from .services import (
    create_tenant_user,
    create_tenant_with_owner,
    resolve_invitation_code,
    update_tenant_user,
)


SUBDOMAIN_PATTERN = re.compile(r'^[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])?$')
SUBDOMAIN_HELP = (
    'Use solo letras minúsculas, números y guiones. '
    'No incluya puntos ni dominios completos. Ejemplo: "caribe-rentals", '
    'no "caribe-rentals.com".'
)


def normalize_subdomain(value: str) -> str:
    if not value:
        return ''
    cleaned = value.strip().lower()
    cleaned = cleaned.replace(' ', '-')
    return cleaned


def validate_subdomain(value: str) -> str:
    cleaned = normalize_subdomain(value)
    if not SUBDOMAIN_PATTERN.match(cleaned):
        raise serializers.ValidationError(SUBDOMAIN_HELP)
    return cleaned


class TenantSerializer(serializers.ModelSerializer):
    """Tenant payload. `integration_config` is admin-only because it can
    contain API tokens; non-admin members get an empty dict instead of the
    raw config. Branding is public to all members of the tenant.
    """

    class Meta:
        model = Tenant
        fields = [
            'id',
            'name',
            'subdomain',
            'branding_config',
            'integration_config',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not (user and (user.is_superuser or getattr(user, 'is_owner', False))):
            # Hide raw integration tokens from members.
            data['integration_config'] = {}
        return data


class TenantCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    subdomain = serializers.SlugField(max_length=80)
    branding_config = serializers.JSONField(required=False)
    integration_config = serializers.JSONField(required=False)
    owner_email = serializers.EmailField()
    owner_full_name = serializers.CharField(max_length=160)
    owner_password = serializers.CharField(min_length=8, write_only=True)

    def create(self, validated_data):
        tenant, owner = create_tenant_with_owner(**validated_data)
        self.context['owner'] = owner
        return tenant

    def to_representation(self, instance):
        data = TenantSerializer(instance).data
        owner = self.context.get('owner')
        if owner:
            data['owner'] = {
                'id': str(owner.id),
                'email': owner.email,
                'full_name': owner.full_name,
                'system_role': owner.system_role,
            }
        return data


class TenantRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantRole
        fields = ['id', 'name', 'permissions', 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_permissions(self, value):
        try:
            return validate_permissions_map(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc


class TenantRoleSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantRole
        fields = ['id', 'name']


class TenantUserSerializer(serializers.ModelSerializer):
    role = TenantRoleSimpleSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'full_name',
            'system_role',
            'is_active',
            'is_primary_owner',
            'role',
            'date_joined',
        ]
        read_only_fields = fields


class TenantUserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=160)
    password = serializers.CharField(min_length=8, write_only=True)
    system_role = serializers.ChoiceField(
        choices=[role.value for role in SystemRole], default=SystemRole.MEMBER.value
    )
    role_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        tenant = self.context['tenant']
        role_id = attrs.get('role_id')
        role = None
        if role_id:
            role = TenantRole.all_objects.filter(id=role_id, tenant=tenant).first()
            if not role:
                raise serializers.ValidationError(
                    {'role_id': 'Role not found for tenant.'}
                )

        if attrs['system_role'] == SystemRole.MEMBER.value and role is None:
            # Will fallback to default role if any.
            pass

        attrs['role'] = role
        return attrs

    def create(self, validated_data):
        tenant = self.context['tenant']
        role = validated_data.pop('role', None)
        validated_data.pop('role_id', None)
        try:
            return create_tenant_user(tenant=tenant, role=role, **validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

    def to_representation(self, instance):
        return TenantUserSerializer(instance).data


class TenantUserUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=160, required=False)
    system_role = serializers.ChoiceField(
        choices=[role.value for role in SystemRole], required=False
    )
    is_active = serializers.BooleanField(required=False)
    role_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        user = self.instance
        tenant = self.context['tenant']

        if 'role_id' in attrs:
            role_id = attrs.pop('role_id')
            if role_id is None:
                attrs['role'] = None
            else:
                role = TenantRole.all_objects.filter(id=role_id, tenant=tenant).first()
                if not role:
                    raise serializers.ValidationError(
                        {'role_id': 'Role not found for tenant.'}
                    )
                attrs['role'] = role

        if (
            attrs.get('system_role') == SystemRole.MEMBER.value
            and attrs.get('role') is None
            and user.role is None
        ):
            raise serializers.ValidationError({'role_id': 'Members must have a role.'})

        return attrs

    def update(self, instance, validated_data):
        try:
            return update_tenant_user(user=instance, data=validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

    def to_representation(self, instance):
        return TenantUserSerializer(instance).data


class UserRegistrationSerializer(serializers.Serializer):
    """Public signup. Always requires a valid InvitationCode.

    The code itself decides what kind of registration is happening:
    - CREATE_TENANT: registers a brand-new tenant + its primary owner.
      Requires `tenant_name` and `tenant_subdomain`.
    - JOIN_TENANT: registers a member inside the tenant the code points to.
      `tenant_subdomain_join` is optional but, if provided, must match the
      tenant on the code (to prevent confusion).

    There is no public "create a tenant without a code" path.
    """

    invitation_code = serializers.CharField(max_length=32)
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=160)
    password = serializers.CharField(min_length=8, write_only=True)

    # Required only when the code is CREATE_TENANT.
    tenant_name = serializers.CharField(max_length=160, required=False, allow_blank=True)
    tenant_subdomain = serializers.CharField(
        max_length=80,
        required=False,
        allow_blank=True,
        help_text=SUBDOMAIN_HELP,
    )

    # Optional confirmation when the code is JOIN_TENANT.
    tenant_subdomain_join = serializers.CharField(
        max_length=80, required=False, allow_blank=True
    )

    def validate(self, attrs):
        from django.contrib.auth import get_user_model

        user_model = get_user_model()

        try:
            invite = resolve_invitation_code(attrs.get('invitation_code'))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

        attrs['_invite'] = invite

        if user_model.objects.filter(email__iexact=attrs['email']).exists():
            raise serializers.ValidationError(
                {'email': 'Este email ya está registrado.'}
            )

        if invite.purpose == InvitationCodePurpose.CREATE_TENANT.value:
            tenant_name = (attrs.get('tenant_name') or '').strip()
            tenant_subdomain_raw = attrs.get('tenant_subdomain') or ''
            errors = {}
            if not tenant_name:
                errors['tenant_name'] = (
                    'El nombre de la empresa es obligatorio cuando se crea una nueva.'
                )
            try:
                subdomain = validate_subdomain(tenant_subdomain_raw)
            except serializers.ValidationError as exc:
                errors['tenant_subdomain'] = exc.detail
                subdomain = None

            if subdomain and Tenant.objects.filter(subdomain=subdomain).exists():
                errors['tenant_subdomain'] = (
                    'Este subdominio ya está en uso. Elige otro.'
                )

            if errors:
                raise serializers.ValidationError(errors)

            attrs['tenant_name'] = tenant_name
            attrs['tenant_subdomain'] = subdomain

        else:  # JOIN_TENANT
            target = invite.tenant
            if target is None:
                raise serializers.ValidationError(
                    {'invitation_code': 'This code is not linked to a tenant.'}
                )
            join_hint = (attrs.get('tenant_subdomain_join') or '').strip().lower()
            if join_hint and join_hint != target.subdomain:
                raise serializers.ValidationError(
                    {
                        'tenant_subdomain_join': (
                            f"El código pertenece a la empresa '{target.subdomain}', "
                            'no coincide con lo que ingresaste.'
                        )
                    }
                )
            attrs['tenant_subdomain_join'] = target.subdomain

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        invite: InvitationCode = validated_data.pop('_invite')
        email = validated_data['email']
        full_name = validated_data['full_name']
        password = validated_data['password']

        if invite.purpose == InvitationCodePurpose.CREATE_TENANT.value:
            tenant, owner = create_tenant_with_owner(
                name=validated_data['tenant_name'],
                subdomain=validated_data['tenant_subdomain'],
                owner_email=email,
                owner_full_name=full_name,
                owner_password=password,
            )
            invite.consume()
            return {
                'tenant': TenantSerializer(tenant).data,
                'user': TenantUserSerializer(owner).data,
                'message': 'Empresa creada exitosamente.',
            }

        # JOIN_TENANT branch
        tenant = invite.tenant
        role = invite.role
        if role is None:
            role = TenantRole.all_objects.filter(
                tenant=tenant, is_default=True
            ).first()
        if role is None:
            from .constants import PermissionLevel, modules_default_permissions

            role = TenantRole.all_objects.create(
                tenant=tenant,
                name='Miembro',
                permissions=modules_default_permissions(PermissionLevel.READ),
                is_default=True,
            )

        try:
            user = create_tenant_user(
                tenant=tenant,
                email=email,
                full_name=full_name,
                password=password,
                role=role,
                system_role=SystemRole.MEMBER.value,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

        invite.consume()

        return {
            'tenant': TenantSerializer(tenant).data,
            'user': TenantUserSerializer(user).data,
            'message': 'Te uniste a la empresa exitosamente.',
        }


class InvitationCodeSerializer(serializers.ModelSerializer):
    """Used by tenant admins to manage their JOIN codes."""

    role_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    role = TenantRoleSimpleSerializer(read_only=True)
    tenant_subdomain = serializers.CharField(
        source='tenant.subdomain', read_only=True
    )
    is_usable = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_exhausted = serializers.BooleanField(read_only=True)

    class Meta:
        model = InvitationCode
        fields = [
            'id',
            'code',
            'purpose',
            'tenant_subdomain',
            'role',
            'role_id',
            'max_uses',
            'uses_count',
            'expires_at',
            'is_active',
            'is_usable',
            'is_expired',
            'is_exhausted',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'code',
            'purpose',
            'tenant_subdomain',
            'role',
            'uses_count',
            'is_usable',
            'is_expired',
            'is_exhausted',
            'created_at',
            'updated_at',
        ]

    def validate_max_uses(self, value):
        if value < 1:
            raise serializers.ValidationError('max_uses must be at least 1.')
        return value


class InvitationCodeCreateSerializer(serializers.Serializer):
    """Owners/admins of a tenant create JOIN_TENANT codes for their team."""

    role_id = serializers.UUIDField(required=False, allow_null=True)
    max_uses = serializers.IntegerField(min_value=1, default=1)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        tenant = self.context['tenant']
        role = None
        role_id = attrs.pop('role_id', None)
        if role_id:
            role = TenantRole.all_objects.filter(id=role_id, tenant=tenant).first()
            if not role:
                raise serializers.ValidationError(
                    {'role_id': 'Role not found for tenant.'}
                )
        attrs['role'] = role
        return attrs

    def create(self, validated_data):
        from .services import issue_join_tenant_code

        tenant = self.context['tenant']
        creator = self.context.get('user')
        return issue_join_tenant_code(
            tenant=tenant,
            created_by=creator,
            role=validated_data['role'],
            max_uses=validated_data['max_uses'],
            expires_at=validated_data.get('expires_at'),
            notes=validated_data.get('notes', ''),
        )

    def to_representation(self, instance):
        return InvitationCodeSerializer(instance).data


class GoogleCalendarCredentialSerializer(serializers.ModelSerializer):
    """Tenant-scoped Google Calendar credential. The refresh token is
    write-only; it's encrypted at rest and never read back through the API.
    """

    refresh_token = serializers.CharField(
        write_only=True, required=False, allow_blank=True,
    )
    has_refresh_token = serializers.SerializerMethodField()

    class Meta:
        model = GoogleCalendarCredential
        fields = [
            'id',
            'calendar_id',
            'is_active',
            'refresh_token',
            'has_refresh_token',
            'last_sync_at',
            'last_sync_status',
            'last_sync_error',
        ]
        read_only_fields = [
            'id', 'last_sync_at', 'last_sync_status', 'last_sync_error',
            'has_refresh_token',
        ]

    def get_has_refresh_token(self, obj) -> bool:
        return bool(obj.refresh_token_encrypted)

    def update(self, instance, validated_data):
        refresh = validated_data.pop('refresh_token', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if refresh:
            instance.set_refresh_token(refresh)
        instance.save()
        return instance

    def create(self, validated_data):
        refresh = validated_data.pop('refresh_token', None)
        instance = GoogleCalendarCredential(**validated_data)
        if refresh:
            instance.set_refresh_token(refresh)
        instance.save()
        return instance


class IntegrationItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    status = serializers.ChoiceField(choices=['connected', 'pending', 'error'])
    icon = serializers.CharField()
    color = serializers.CharField()
    last_sync = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    details = serializers.CharField(required=False, allow_blank=True, allow_null=True)
