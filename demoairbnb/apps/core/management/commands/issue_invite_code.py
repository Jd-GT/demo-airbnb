"""Generate an invitation code from the command line.

Examples:
    # New tenant code (default), 1 use, no expiry
    python manage.py issue_invite_code

    # New tenant code with notes, expires in 7 days
    python manage.py issue_invite_code --notes "Lead acme" --expires-days 7

    # Join code for an existing tenant by subdomain
    python manage.py issue_invite_code --join --tenant caribe-rentals --max-uses 5
"""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.core.models import Tenant
from apps.core.services import (
    issue_create_tenant_code,
    issue_join_tenant_code,
)


class Command(BaseCommand):
    help = 'Issue a new invitation code (CREATE_TENANT or JOIN_TENANT).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--join',
            action='store_true',
            help='Generate a JOIN_TENANT code instead of CREATE_TENANT.',
        )
        parser.add_argument(
            '--tenant',
            help='Subdomain of the target tenant (required with --join).',
        )
        parser.add_argument(
            '--max-uses',
            type=int,
            default=1,
            help='Maximum number of times the code can be redeemed (default: 1).',
        )
        parser.add_argument(
            '--expires-days',
            type=int,
            help='Expire the code after N days from now.',
        )
        parser.add_argument('--notes', default='', help='Free-text notes for audit.')
        parser.add_argument(
            '--code',
            help='Optional explicit code value (otherwise auto-generated).',
        )

    def handle(self, *args, **opts):
        expires_at = None
        if opts['expires_days']:
            expires_at = timezone.now() + timedelta(days=opts['expires_days'])

        common = {
            'max_uses': opts['max_uses'],
            'expires_at': expires_at,
            'notes': opts['notes'],
            'code': opts.get('code'),
        }

        if opts['join']:
            if not opts['tenant']:
                raise CommandError('--tenant is required when using --join.')
            tenant = Tenant.objects.filter(subdomain=opts['tenant']).first()
            if not tenant:
                raise CommandError(f"Tenant '{opts['tenant']}' not found.")
            invite = issue_join_tenant_code(tenant=tenant, **common)
            target = f'JOIN  → {tenant.subdomain}'
        else:
            invite = issue_create_tenant_code(**common)
            target = 'CREATE → [new tenant]'

        self.stdout.write(self.style.SUCCESS(f'\nCode generated: {invite.code}'))
        self.stdout.write(f'Purpose:    {target}')
        self.stdout.write(f'Max uses:   {invite.max_uses}')
        self.stdout.write(f'Expires at: {invite.expires_at or "never"}')
        if invite.notes:
            self.stdout.write(f'Notes:      {invite.notes}')
