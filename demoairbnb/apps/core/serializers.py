from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .constants import SystemRole, validate_permissions_map
from .models import Tenant, TenantRole, User
from .services import create_tenant_user, create_tenant_with_owner, update_tenant_user


class TenantSerializer(serializers.ModelSerializer):
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
    REGISTRATION_TYPE_CHOICES = [
        ('new_tenant', 'Crear nuevo tenant/host'),
        ('join_tenant', 'Unirse a tenant existente'),
    ]
    
    registration_type = serializers.ChoiceField(choices=REGISTRATION_TYPE_CHOICES)
    
    # Common fields
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=160)
    password = serializers.CharField(min_length=8, write_only=True)
    
    # For new tenant
    tenant_name = serializers.CharField(max_length=160, required=False)
    tenant_subdomain = serializers.SlugField(max_length=80, required=False)
    
    # For join tenant
    tenant_subdomain_join = serializers.SlugField(max_length=80, required=False)
    invitation_code = serializers.CharField(max_length=32, required=False)

    def validate(self, attrs):
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        reg_type = attrs.get('registration_type')

        tenant_subdomain = attrs.get('tenant_subdomain')
        if isinstance(tenant_subdomain, str):
            attrs['tenant_subdomain'] = tenant_subdomain.strip().lower()

        if reg_type == 'new_tenant':
            if not attrs.get('tenant_name') or not attrs.get('tenant_subdomain'):
                raise serializers.ValidationError({
                    'tenant_name': 'Required for new tenant registration.',
                    'tenant_subdomain': 'Required for new tenant registration.'
                })

            # Check if subdomain already exists
            if Tenant.objects.filter(subdomain=attrs.get('tenant_subdomain')).exists():
                raise serializers.ValidationError({
                    'tenant_subdomain': 'Este subdominio ya está en uso. Elige otro.'
                })

            # Check if email already exists
            if user_model.objects.filter(email=attrs.get('email')).exists():
                raise serializers.ValidationError({
                    'email': 'Este email ya está registrado.'
                })

        elif reg_type == 'join_tenant':
            join_subdomain = (
                attrs.get('tenant_subdomain_join') or attrs.get('tenant_subdomain')
            )
            if isinstance(join_subdomain, str):
                join_subdomain = join_subdomain.strip().lower()

            invite_code = attrs.get('invitation_code')
            if isinstance(invite_code, str):
                invite_code = invite_code.strip().upper()

            if not join_subdomain or not invite_code:
                raise serializers.ValidationError({
                    'tenant_subdomain_join': 'Required to join existing tenant.',
                    'invitation_code': 'Invitation code required.'
                })

            attrs['tenant_subdomain_join'] = join_subdomain
            attrs['invitation_code'] = invite_code

            # Check if subdomain exists
            if not Tenant.objects.filter(subdomain=join_subdomain).exists():
                raise serializers.ValidationError({
                    'tenant_subdomain_join': 'No se encontró una empresa con ese nombre.'
                })

            # Check if email already exists
            if user_model.objects.filter(email=attrs.get('email')).exists():
                raise serializers.ValidationError({
                    'email': 'Este email ya está registrado.'
                })

        return attrs

    def create(self, validated_data):
        reg_type = validated_data.get('registration_type')
        email = validated_data.get('email')
        full_name = validated_data.get('full_name')
        password = validated_data.get('password')

        if reg_type == 'new_tenant':
            tenant, owner = create_tenant_with_owner(
                name=validated_data.get('tenant_name'),
                subdomain=validated_data.get('tenant_subdomain'),
                owner_email=email,
                owner_full_name=full_name,
                owner_password=password
            )
            return {
                'tenant': TenantSerializer(tenant).data,
                'user': TenantUserSerializer(owner).data,
                'message': 'Tenant created successfully'
            }

        elif reg_type == 'join_tenant':
            tenant = Tenant.objects.filter(
                subdomain=validated_data.get('tenant_subdomain_join')
            ).first()

            if not tenant:
                raise serializers.ValidationError({
                    'tenant_subdomain_join': 'Tenant not found.'
                })

            # Validate invitation code
            configured_invite_code = ''
            if tenant.branding_config:
                configured_invite_code = str(
                    tenant.branding_config.get('invitation_code', '')
                ).strip().upper()

            provided_invite_code = str(
                validated_data.get('invitation_code', '')
            ).strip().upper()

            if not configured_invite_code or configured_invite_code != provided_invite_code:
                raise serializers.ValidationError({
                    'invitation_code': 'Invalid invitation code.'
                })

            # Get default role or create one
            default_role = TenantRole.all_objects.filter(
                tenant=tenant,
                is_default=True
            ).first()

            if not default_role:
                from .constants import modules_default_permissions, PermissionLevel
                default_role = TenantRole.all_objects.create(
                    tenant=tenant,
                    name='Miembro',
                    permissions=modules_default_permissions(PermissionLevel.READ),
                    is_default=True
                )

            user = create_tenant_user(
                tenant=tenant,
                email=email,
                full_name=full_name,
                password=password,
                role=default_role,
                system_role='MEMBER'
            )
            
            return {
                'tenant': TenantSerializer(tenant).data,
                'user': TenantUserSerializer(user).data,
                'message': 'Joined tenant successfully'
            }

        raise serializers.ValidationError({'registration_type': 'Invalid registration type.'})


class IntegrationItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    status = serializers.ChoiceField(choices=['connected', 'pending', 'error'])
    icon = serializers.CharField()
    color = serializers.CharField()
    last_sync = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    details = serializers.CharField(required=False, allow_blank=True, allow_null=True)
