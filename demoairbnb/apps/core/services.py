from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from .constants import SystemRole
from .models import Tenant, TenantRole, User, default_admin_permissions, default_read_permissions


DEFAULT_TENANT_INTEGRATIONS = [
    {
        "id": "airbnb",
        "name": "Airbnb API",
        "description": "Sincronizacion de reservas, disponibilidad y precios",
        "status": "connected",
        "icon": "🏠",
        "color": "#FF5A5F",
        "last_sync": "Hace 5 min",
        "details": "12 propiedades sincronizadas",
    },
    {
        "id": "booking",
        "name": "Booking.com API",
        "description": "Canal de reservas y gestion de tarifas",
        "status": "connected",
        "icon": "🔵",
        "color": "#003580",
        "last_sync": "Hace 12 min",
        "details": "10 propiedades sincronizadas",
    },
    {
        "id": "channel",
        "name": "Channel Manager",
        "description": "Distribucion centralizada en multiples canales OTA",
        "status": "pending",
        "icon": "📡",
        "color": "#F59E0B",
        "details": "Configuracion en progreso",
    },
    {
        "id": "stripe",
        "name": "Stripe Payments",
        "description": "Pasarela de pagos para reservas directas",
        "status": "connected",
        "icon": "💳",
        "color": "#635BFF",
        "last_sync": "Hace 1 min",
        "details": "EUR 12,400 procesados este mes",
    },
    {
        "id": "google",
        "name": "Google Calendar",
        "description": "Sincronizacion de calendario con Google",
        "status": "error",
        "icon": "📅",
        "color": "#4285F4",
        "details": "Error de autenticacion - Token expirado",
    },
    {
        "id": "mailchimp",
        "name": "Mailchimp",
        "description": "Marketing por email para huespedes recurrentes",
        "status": "pending",
        "icon": "📧",
        "color": "#FFE01B",
        "details": "Pendiente de activacion",
    },
]
VALID_INTEGRATION_STATUSES = {"connected", "pending", "error"}


def build_default_integration_config() -> dict:
    return {"integrations": [integration.copy() for integration in DEFAULT_TENANT_INTEGRATIONS]}


def normalize_integrations_config(
    integration_config: dict | None,
    *,
    google_credential=None,
) -> list[dict]:
    ordered_ids = [integration["id"] for integration in DEFAULT_TENANT_INTEGRATIONS]
    integrations_by_id = {
        integration["id"]: integration.copy()
        for integration in DEFAULT_TENANT_INTEGRATIONS
    }

    raw_items = []
    if isinstance(integration_config, dict):
        candidate = integration_config.get("integrations", [])
        if isinstance(candidate, list):
            raw_items = candidate

    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue

        integration_id = raw_item.get("id")
        if not integration_id:
            continue

        base_item = integrations_by_id.get(
            integration_id,
            {
                "id": integration_id,
                "name": str(integration_id).replace("-", " ").title(),
                "description": "Integracion personalizada",
                "status": "pending",
                "icon": "🔌",
                "color": "#8A9A9B",
            },
        ).copy()

        status = raw_item.get("status", base_item["status"])
        if status not in VALID_INTEGRATION_STATUSES:
            status = "pending"

        base_item.update(
            {
                "name": raw_item.get("name", base_item["name"]),
                "description": raw_item.get("description", base_item["description"]),
                "status": status,
                "icon": raw_item.get("icon", base_item["icon"]),
                "color": raw_item.get("color", base_item["color"]),
                "last_sync": raw_item.get("last_sync", base_item.get("last_sync")),
                "details": raw_item.get("details", base_item.get("details")),
            }
        )
        integrations_by_id[integration_id] = base_item
        if integration_id not in ordered_ids:
            ordered_ids.append(integration_id)

    if google_credential is not None:
        google_item = integrations_by_id.get("google", {}).copy()
        if google_credential.is_active and google_credential.last_sync_status == "connected":
            status_value = "connected"
            details = (
                f"Conectado como {google_credential.google_account_email}"
                if google_credential.google_account_email
                else "Calendario conectado"
            )
        elif google_credential.last_sync_status == "error":
            status_value = "error"
            details = google_credential.last_sync_error or "Error de sincronización"
        else:
            status_value = "pending"
            details = "Autorización pendiente"

        last_sync = None
        if google_credential.last_sync_at:
            last_sync = google_credential.last_sync_at.isoformat()

        google_item.update(
            {
                "id": "google",
                "name": google_item.get("name", "Google Calendar"),
                "description": google_item.get(
                    "description", "Sincronizacion de calendario con Google"
                ),
                "icon": google_item.get("icon", "📅"),
                "color": google_item.get("color", "#4285F4"),
                "status": status_value,
                "details": details,
                "last_sync": last_sync,
            }
        )
        integrations_by_id["google"] = google_item
    else:
        google_item = integrations_by_id.get("google", {}).copy()
        google_item.update({"status": "pending", "details": "Sin conectar", "last_sync": None})
        integrations_by_id["google"] = google_item

    return [integrations_by_id[integration_id] for integration_id in ordered_ids]


@transaction.atomic
def seed_default_roles(tenant: Tenant) -> tuple[TenantRole, TenantRole]:
    admin_role, _ = TenantRole.all_objects.get_or_create(
        tenant=tenant,
        name="Admin Total",
        defaults={"permissions": default_admin_permissions(), "is_default": False},
    )
    readonly_role, _ = TenantRole.all_objects.get_or_create(
        tenant=tenant,
        name="Solo Lectura",
        defaults={"permissions": default_read_permissions(), "is_default": True},
    )
    return admin_role, readonly_role


@transaction.atomic
def create_tenant_with_owner(*, name: str, subdomain: str, owner_email: str, owner_password: str, owner_full_name: str, branding_config: dict | None = None, integration_config: dict | None = None) -> tuple[Tenant, User]:
    tenant = Tenant.objects.create(
        name=name,
        subdomain=subdomain,
        branding_config=branding_config or {},
        integration_config=integration_config or build_default_integration_config(),
    )

    admin_role, _ = seed_default_roles(tenant)

    owner = User.objects.create_user(
        email=owner_email,
        password=owner_password,
        full_name=owner_full_name,
        tenant=tenant,
        role=admin_role,
        system_role=SystemRole.OWNER.value,
        is_primary_owner=True,
    )
    return tenant, owner


@transaction.atomic
def create_tenant_user(*, tenant: Tenant, email: str, password: str, full_name: str, system_role: str = SystemRole.MEMBER.value, role: TenantRole | None = None) -> User:
    if system_role == SystemRole.MEMBER.value and role is None:
        role = TenantRole.all_objects.filter(tenant=tenant, is_default=True).first()

    if role and role.tenant_id != tenant.id:
        raise ValidationError({"role": "Role must belong to the same tenant."})

    user = User.objects.create_user(
        email=email,
        password=password,
        full_name=full_name,
        tenant=tenant,
        role=role,
        system_role=system_role,
    )
    return user


@transaction.atomic
def update_tenant_user(*, user: User, data: dict):
    if user.is_primary_owner:
        if data.get("system_role") and data["system_role"] != SystemRole.OWNER.value:
            raise ValidationError({"system_role": "Primary owner cannot be downgraded."})
        if "is_active" in data and data["is_active"] is False:
            raise ValidationError({"is_active": "Primary owner cannot be deactivated."})

    for key, value in data.items():
        setattr(user, key, value)
    user.save()
    return user


@transaction.atomic
def create_email_template(
    *,
    tenant: Tenant,
    name: str,
    template_type: str,
    body: str,
    subject: str = "",
    variables_used: list | None = None,
    is_active: bool = True,
) -> "EmailTemplate":
    """Create a new email template for a tenant."""
    from .models import EmailTemplate

    template = EmailTemplate.objects.create(
        tenant=tenant,
        name=name,
        template_type=template_type,
        subject=subject,
        body=body,
        variables_used=variables_used or [],
        is_active=is_active,
    )
    return template


def seed_default_email_templates(tenant: Tenant) -> None:
    """Seed default email templates for a tenant."""
    from .models import EmailTemplate

    default_templates = [
        {
            "name": "Confirmación de Reserva Estándar",
            "template_type": "booking_confirmation",
            "subject": "Reserva Confirmada - {property_name}",
            "body": """Hola {guest_name},

Tu reserva en {property_name} ha sido confirmada.

Detalles:
- Check-in: {check_in}
- Check-out: {check_out}
- Monto Total: ${total_amount}

¡Esperamos tu llegada!

Saludos,
El Equipo de {property_name}""",
            "variables_used": ["guest_name", "property_name", "check_in", "check_out", "total_amount"],
        },
        {
            "name": "Recordatorio de Check-in",
            "template_type": "booking_reminder",
            "subject": "Recordatorio: Tu check-in es hoy en {property_name}",
            "body": """Hola {guest_name},

Este es un recordatorio de que tu check-in es hoy en {property_name}.

Dirección: {property_address}
Hora de check-in: 3:00 PM
Hora de check-out: 11:00 AM

Si tienes preguntas, no dudes en contactarnos.

Saludos,
{property_name}""",
            "variables_used": ["guest_name", "property_name", "property_address"],
        },
        {
            "name": "Bienvenida Huésped",
            "template_type": "guest_welcome",
            "subject": "¡Bienvenido a {property_name}!",
            "body": """Hola {guest_name},

¡Bienvenido a {property_name}! Nos complace recibirte.

WiFi: {wifi_name}
Contraseña WiFi: {wifi_password}

Por favor, respeta las normas de convivencia. Si necesitas ayuda, estamos disponibles 24/7.

¡Que disfrutes tu estadía!""",
            "variables_used": ["guest_name", "property_name", "wifi_name", "wifi_password"],
        },
    ]

    for template_data in default_templates:
        EmailTemplate.all_objects.get_or_create(
            tenant=tenant,
            name=template_data["name"],
            defaults={
                "template_type": template_data["template_type"],
                "subject": template_data["subject"],
                "body": template_data["body"],
                "variables_used": template_data["variables_used"],
                "is_active": True,
            },
        )

