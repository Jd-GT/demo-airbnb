from __future__ import annotations

import secrets
import string
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from simple_history.models import HistoricalRecords

from .constants import (
    PermissionLevel,
    SystemRole,
    modules_default_permissions,
    validate_permissions_map,
)
from .managers import TenantAwareManager, UserManager


class TimeStampedUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Tenant(TimeStampedUUIDModel):
    name = models.CharField(max_length=160)
    subdomain = models.SlugField(max_length=80, unique=True)
    branding_config = models.JSONField(default=dict, blank=True)
    integration_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class TenantAwareModel(TimeStampedUUIDModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    objects = TenantAwareManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


class TenantRole(TenantAwareModel):
    name = models.CharField(max_length=120)
    permissions = models.JSONField(default=dict)
    is_default = models.BooleanField(default=False)
    history = HistoricalRecords()

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'], name='tenant_role_unique_name'
            ),
            models.UniqueConstraint(
                fields=['tenant'],
                condition=Q(is_default=True),
                name='tenant_single_default_role',
            ),
        ]

    def clean(self):
        try:
            self.permissions = validate_permissions_map(self.permissions)
        except ValueError as exc:
            raise ValidationError({'permissions': str(exc)}) from exc

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.tenant.name} - {self.name}'


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=160)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True,
    )
    role = models.ForeignKey(
        TenantRole,
        on_delete=models.SET_NULL,
        related_name='users',
        null=True,
        blank=True,
    )
    system_role = models.CharField(
        max_length=12,
        choices=[(role.value, role.value) for role in SystemRole],
        default=SystemRole.MEMBER.value,
    )
    is_primary_owner = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords(excluded_fields=['password', 'last_login'])

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ['email']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant'],
                condition=Q(is_primary_owner=True),
                name='single_primary_owner_per_tenant',
            )
        ]

    def clean(self):
        if (
            self.system_role == SystemRole.OWNER.value
            and not self.tenant
            and not self.is_superuser
        ):
            raise ValidationError({'tenant': 'Owner users must belong to a tenant.'})

        if self.system_role == SystemRole.MEMBER.value:
            if self.tenant and not self.role:
                raise ValidationError({'role': 'Member users must have a tenant role.'})
            if self.tenant and self.role and self.role.tenant_id != self.tenant_id:
                raise ValidationError({'role': 'Role must belong to the same tenant.'})

        if self.system_role != SystemRole.MEMBER.value:
            self.role = None

        if self.is_primary_owner:
            self.system_role = SystemRole.OWNER.value
            self.is_active = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def is_owner(self) -> bool:
        return self.system_role == SystemRole.OWNER.value

    def can_access_module(self, module: str, required_level: PermissionLevel) -> bool:
        if self.is_superuser or self.is_owner:
            return True

        if not self.role:
            return False

        granted_level = self.role.permissions.get(module, PermissionLevel.NONE.value)
        hierarchy = {
            PermissionLevel.NONE.value: 0,
            PermissionLevel.READ.value: 1,
            PermissionLevel.WRITE.value: 2,
            PermissionLevel.ADMIN.value: 3,
        }
        return hierarchy.get(granted_level, 0) >= hierarchy[required_level.value]

    def __str__(self) -> str:
        return self.email


class EmailTemplate(TenantAwareModel):
    """Email/SMS message templates per tenant."""

    TYPE_CHOICES = [
        ("booking_confirmation", "Confirmación de Reserva"),
        ("booking_reminder", "Recordatorio de Reserva"),
        ("booking_cancellation", "Cancelación de Reserva"),
        ("guest_welcome", "Bienvenida Huésped"),
        ("guest_review_request", "Solicitud de Reseña"),
        ("owner_daily_summary", "Resumen Diario Propietario"),
        ("payment_receipt", "Recibo de Pago"),
        ("custom", "Personalizado"),
    ]

    name = models.CharField(max_length=120, help_text="Nombre interno de la plantilla")
    template_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        help_text="Tipo de plantilla para categorización",
    )
    subject = models.CharField(
        max_length=255,
        blank=True,
        help_text="Asunto del email. Soporta variables: {guest_name}, {property_name}, etc.",
    )
    body = models.TextField(
        help_text="Cuerpo del mensaje. Soporta variables: {guest_name}, {property_name}, {check_in}, {check_out}, etc.",
    )
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False, help_text="Plantilla por defecto para su tipo"
    )
    variables_used = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de variables usadas: ['guest_name', 'property_name']",
    )

    class Meta:
        ordering = ["template_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "template_type"],
                condition=Q(is_default=True),
                name="tenant_single_default_email_template",
            ),
            models.UniqueConstraint(
                fields=["tenant", "name"],
                name="tenant_email_template_unique_name",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tenant.name} - {self.name}"


class GoogleCalendarCredential(TimeStampedUUIDModel):
    """OAuth2 credential and sync state for a tenant's Google Calendar integration."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("connected", "Connected"),
        ("error", "Error"),
    ]

    tenant = models.OneToOneField(
        Tenant, on_delete=models.CASCADE, related_name="google_calendar_credential"
    )
    refresh_token_encrypted = models.TextField()
    calendar_id = models.CharField(max_length=255, default="primary")
    google_account_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="pending"
    )
    last_sync_error = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"GoogleCalendarCredential({self.tenant.name})"


def default_admin_permissions() -> dict[str, str]:
    return modules_default_permissions(PermissionLevel.ADMIN)


def default_read_permissions() -> dict[str, str]:
    """Read access on operational modules; users/finance start at NONE."""
    from .constants import safe_readonly_permissions

    return safe_readonly_permissions()


def _generate_code(length: int = 12) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class InvitationCodePurpose(models.TextChoices):
    CREATE_TENANT = 'CREATE_TENANT', 'Crear nueva empresa (tenant)'
    JOIN_TENANT = 'JOIN_TENANT', 'Unirse a empresa existente'


class InvitationCode(TimeStampedUUIDModel):
    """Codes that gate the public signup flow.

    - CREATE_TENANT codes: tenant is null. Only the platform super-admin can
      issue them. They allow registering a brand-new tenant. Without one, no
      tenant can be created from the public API.
    - JOIN_TENANT codes: tenant is set. Owners/admins of that tenant issue
      them to invite new members.
    """

    code = models.CharField(max_length=32, unique=True, db_index=True)
    purpose = models.CharField(
        max_length=20,
        choices=InvitationCodePurpose.choices,
        default=InvitationCodePurpose.CREATE_TENANT.value,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='invitation_codes',
        null=True,
        blank=True,
    )
    role = models.ForeignKey(
        'TenantRole',
        on_delete=models.SET_NULL,
        related_name='invitation_codes',
        null=True,
        blank=True,
        help_text='Optional role to assign when JOIN_TENANT code is used.',
    )
    max_uses = models.PositiveIntegerField(default=1)
    uses_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='invitation_codes_created',
        null=True,
        blank=True,
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['purpose', 'is_active']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(max_uses__gte=1),
                name='invitationcode_max_uses_positive',
            ),
        ]

    def __str__(self) -> str:
        target = self.tenant.subdomain if self.tenant_id else 'NEW-TENANT'
        return f'{self.code} → {target} ({self.purpose})'

    def clean(self):
        if self.purpose == InvitationCodePurpose.CREATE_TENANT.value:
            if self.tenant_id:
                raise ValidationError(
                    {'tenant': 'CREATE_TENANT codes must not be linked to a tenant.'}
                )
            if self.role_id:
                raise ValidationError(
                    {'role': 'CREATE_TENANT codes cannot pre-assign a role.'}
                )
        elif self.purpose == InvitationCodePurpose.JOIN_TENANT.value:
            if not self.tenant_id:
                raise ValidationError(
                    {'tenant': 'JOIN_TENANT codes require a target tenant.'}
                )
            if self.role_id and self.role.tenant_id != self.tenant_id:
                raise ValidationError(
                    {'role': 'Role must belong to the same tenant as the code.'}
                )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = _generate_code()
        self.code = self.code.strip().upper()
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and timezone.now() >= self.expires_at)

    @property
    def is_exhausted(self) -> bool:
        return self.uses_count >= self.max_uses

    @property
    def is_usable(self) -> bool:
        return self.is_active and not self.is_expired and not self.is_exhausted

    def consume(self) -> None:
        """Atomically increment uses_count and deactivate if exhausted."""
        InvitationCode.objects.filter(pk=self.pk).update(
            uses_count=F('uses_count') + 1
        )
        self.refresh_from_db(fields=['uses_count'])
        if self.is_exhausted:
            InvitationCode.objects.filter(pk=self.pk).update(is_active=False)
            self.is_active = False
