from __future__ import annotations

from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .constants import SystemRole, validate_permissions_map
from .models import Tenant, TenantRole, User, EmailTemplate
from .services import create_tenant_user, create_tenant_with_owner, update_tenant_user


def serialize_auth_user(user: User) -> dict[str, str | None]:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "system_role": user.system_role,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
    }


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True, trim_whitespace=False)

    default_error_messages = {
        "invalid_credentials": "Unable to log in with the provided credentials.",
        "inactive": "This user account is inactive.",
    }

    def validate(self, attrs):
        request = self.context.get("request")
        user = authenticate(
            request=request,
            username=attrs["email"],
            password=attrs["password"],
        )

        if user is None:
            raise serializers.ValidationError(
                {"detail": self.error_messages["invalid_credentials"]},
                code="authorization",
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": self.error_messages["inactive"]},
                code="authorization",
            )

        attrs["user"] = user
        return attrs


class PersonalizedTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        access_token = data["access"]
        refresh_token = data["refresh"]

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": serialize_auth_user(self.user),
            # Keep SimpleJWT's default keys for existing clients already using them.
            "access": access_token,
            "refresh": refresh_token,
        }


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "subdomain", "branding_config", "integration_config", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


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
        self.context["owner"] = owner
        return tenant

    def to_representation(self, instance):
        data = TenantSerializer(instance).data
        owner = self.context.get("owner")
        if owner:
            data["owner"] = {
                "id": str(owner.id),
                "email": owner.email,
                "full_name": owner.full_name,
                "system_role": owner.system_role,
            }
        return data


class TenantRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantRole
        fields = ["id", "name", "permissions", "is_default", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_permissions(self, value):
        try:
            return validate_permissions_map(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc


class TenantRoleSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantRole
        fields = ["id", "name"]


class TenantUserSerializer(serializers.ModelSerializer):
    role = TenantRoleSimpleSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "system_role",
            "is_active",
            "is_primary_owner",
            "role",
            "date_joined",
        ]
        read_only_fields = fields


class TenantUserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=160)
    password = serializers.CharField(min_length=8, write_only=True)
    system_role = serializers.ChoiceField(choices=[role.value for role in SystemRole], default=SystemRole.MEMBER.value)
    role_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        tenant = self.context["tenant"]
        role_id = attrs.get("role_id")
        role = None
        if role_id:
            role = TenantRole.all_objects.filter(id=role_id, tenant=tenant).first()
            if not role:
                raise serializers.ValidationError({"role_id": "Role not found for tenant."})

        if attrs["system_role"] == SystemRole.MEMBER.value and role is None:
            # Will fallback to default role if any.
            pass

        attrs["role"] = role
        return attrs

    def create(self, validated_data):
        tenant = self.context["tenant"]
        role = validated_data.pop("role", None)
        validated_data.pop("role_id", None)
        try:
            return create_tenant_user(tenant=tenant, role=role, **validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

    def to_representation(self, instance):
        return TenantUserSerializer(instance).data


class TenantUserUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=160, required=False)
    system_role = serializers.ChoiceField(choices=[role.value for role in SystemRole], required=False)
    is_active = serializers.BooleanField(required=False)
    role_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        user = self.instance
        tenant = self.context["tenant"]

        if "role_id" in attrs:
            role_id = attrs.pop("role_id")
            if role_id is None:
                attrs["role"] = None
            else:
                role = TenantRole.all_objects.filter(id=role_id, tenant=tenant).first()
                if not role:
                    raise serializers.ValidationError({"role_id": "Role not found for tenant."})
                attrs["role"] = role

        if attrs.get("system_role") == SystemRole.MEMBER.value and attrs.get("role") is None and user.role is None:
            raise serializers.ValidationError({"role_id": "Members must have a role."})

        return attrs

    def update(self, instance, validated_data):
        try:
            return update_tenant_user(user=instance, data=validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

    def to_representation(self, instance):
        return TenantUserSerializer(instance).data


class IntegrationItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    status = serializers.ChoiceField(choices=["connected", "pending", "error"])
    icon = serializers.CharField()
    color = serializers.CharField()
    last_sync = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    details = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = [
            "id",
            "name",
            "template_type",
            "subject",
            "body",
            "is_active",
            "is_default",
            "variables_used",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmailTemplateCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = ["name", "template_type", "subject", "body", "is_active", "variables_used"]

    def create(self, validated_data):
        tenant = self.context["tenant"]
        return EmailTemplate.objects.create(tenant=tenant, **validated_data)


class EmailTemplateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = ["name", "subject", "body", "is_active", "variables_used"]

