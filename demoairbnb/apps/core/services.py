from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from .constants import SystemRole
from .models import (
    InvitationCode,
    InvitationCodePurpose,
    Tenant,
    TenantRole,
    User,
    default_admin_permissions,
    default_read_permissions,
)

# Only Google Calendar is kept as a real integration target. The rest of the
# providers (Airbnb, Booking, Stripe, Mailchimp...) were mocks that the team
# decided to remove until a real implementation exists. See
# documentacion/CHANGELOG.md.
DEFAULT_TENANT_INTEGRATIONS = [
    {
        'id': 'google_calendar',
        'name': 'Google Calendar',
        'description': (
            'Sincroniza reservas confirmadas con un calendario de Google '
            'para que el equipo vea check-ins/check-outs en tiempo real.'
        ),
        'status': 'pending',
        'icon': '📅',
        'color': '#4285F4',
        'last_sync': None,
        'details': 'Conecta tu cuenta de Google desde Configuración → Integraciones.',
    },
]
VALID_INTEGRATION_STATUSES = {'connected', 'pending', 'error'}


def build_default_integration_config() -> dict:
    return {
        'integrations': [
            integration.copy() for integration in DEFAULT_TENANT_INTEGRATIONS
        ]
    }


def normalize_integrations_config(integration_config: dict | None) -> list[dict]:
    ordered_ids = [integration['id'] for integration in DEFAULT_TENANT_INTEGRATIONS]
    integrations_by_id = {
        integration['id']: integration.copy()
        for integration in DEFAULT_TENANT_INTEGRATIONS
    }

    raw_items = []
    if isinstance(integration_config, dict):
        candidate = integration_config.get('integrations', [])
        if isinstance(candidate, list):
            raw_items = candidate

    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue

        integration_id = raw_item.get('id')
        if not integration_id:
            continue

        base_item = integrations_by_id.get(
            integration_id,
            {
                'id': integration_id,
                'name': str(integration_id).replace('-', ' ').title(),
                'description': 'Integracion personalizada',
                'status': 'pending',
                'icon': '🔌',
                'color': '#8A9A9B',
            },
        ).copy()

        status = raw_item.get('status', base_item['status'])
        if status not in VALID_INTEGRATION_STATUSES:
            status = 'pending'

        base_item.update(
            {
                'name': raw_item.get('name', base_item['name']),
                'description': raw_item.get('description', base_item['description']),
                'status': status,
                'icon': raw_item.get('icon', base_item['icon']),
                'color': raw_item.get('color', base_item['color']),
                'last_sync': raw_item.get('last_sync', base_item.get('last_sync')),
                'details': raw_item.get('details', base_item.get('details')),
            }
        )
        integrations_by_id[integration_id] = base_item
        if integration_id not in ordered_ids:
            ordered_ids.append(integration_id)

    return [integrations_by_id[integration_id] for integration_id in ordered_ids]


@transaction.atomic
def seed_default_roles(tenant: Tenant) -> tuple[TenantRole, TenantRole]:
    admin_role, _ = TenantRole.all_objects.get_or_create(
        tenant=tenant,
        name='Admin Total',
        defaults={'permissions': default_admin_permissions(), 'is_default': False},
    )
    readonly_role, _ = TenantRole.all_objects.get_or_create(
        tenant=tenant,
        name='Solo Lectura',
        defaults={'permissions': default_read_permissions(), 'is_default': True},
    )
    return admin_role, readonly_role


@transaction.atomic
def create_tenant_with_owner(
    *,
    name: str,
    subdomain: str,
    owner_email: str,
    owner_password: str,
    owner_full_name: str,
    branding_config: dict | None = None,
    integration_config: dict | None = None,
) -> tuple[Tenant, User]:
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
def create_tenant_user(
    *,
    tenant: Tenant,
    email: str,
    password: str,
    full_name: str,
    system_role: str = SystemRole.MEMBER.value,
    role: TenantRole | None = None,
) -> User:
    if system_role == SystemRole.MEMBER.value and role is None:
        role = TenantRole.all_objects.filter(tenant=tenant, is_default=True).first()

    if role and role.tenant_id != tenant.id:
        raise ValidationError({'role': 'Role must belong to the same tenant.'})

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
        if data.get('system_role') and data['system_role'] != SystemRole.OWNER.value:
            raise ValidationError(
                {'system_role': 'Primary owner cannot be downgraded.'}
            )
        if 'is_active' in data and data['is_active'] is False:
            raise ValidationError({'is_active': 'Primary owner cannot be deactivated.'})

    for key, value in data.items():
        setattr(user, key, value)
    user.save()
    return user


def resolve_invitation_code(raw_code: str) -> InvitationCode:
    """Look up a code, normalising case/spaces. Raises ValidationError if not usable."""
    if not raw_code:
        raise ValidationError({'invitation_code': 'Invitation code is required.'})
    normalized = str(raw_code).strip().upper()
    code = InvitationCode.objects.filter(code=normalized).first()
    if not code:
        raise ValidationError({'invitation_code': 'Invalid invitation code.'})
    if not code.is_usable:
        if code.is_expired:
            raise ValidationError(
                {'invitation_code': 'This invitation code has expired.'}
            )
        if code.is_exhausted:
            raise ValidationError(
                {'invitation_code': 'This invitation code has reached its usage limit.'}
            )
        raise ValidationError(
            {'invitation_code': 'This invitation code is no longer active.'}
        )
    return code


@transaction.atomic
def issue_create_tenant_code(
    *,
    created_by: User | None = None,
    notes: str = '',
    max_uses: int = 1,
    expires_at=None,
    code: str | None = None,
) -> InvitationCode:
    """Create a code that authorises someone to register a brand-new tenant."""
    invite = InvitationCode(
        purpose=InvitationCodePurpose.CREATE_TENANT.value,
        max_uses=max_uses,
        expires_at=expires_at,
        notes=notes,
        created_by=created_by,
    )
    if code:
        invite.code = code
    invite.save()
    return invite


@transaction.atomic
def issue_join_tenant_code(
    *,
    tenant: Tenant,
    created_by: User | None = None,
    role: TenantRole | None = None,
    notes: str = '',
    max_uses: int = 1,
    expires_at=None,
    code: str | None = None,
) -> InvitationCode:
    """Create a code that authorises someone to join an existing tenant."""
    invite = InvitationCode(
        purpose=InvitationCodePurpose.JOIN_TENANT.value,
        tenant=tenant,
        role=role,
        max_uses=max_uses,
        expires_at=expires_at,
        notes=notes,
        created_by=created_by,
    )
    if code:
        invite.code = code
    invite.save()
    return invite
