"""Synchronize all active iCal feeds.

Usage:
    python manage.py sync_ical_feeds                # all tenants, all active feeds
    python manage.py sync_ical_feeds --tenant <id>  # one tenant only

Schedule via cron / Windows Task Scheduler / Celery beat (e.g. every 30 min).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.channels.models import PropertyICalFeed
from apps.channels.services import sync_ical_feed


class Command(BaseCommand):
    help = "Synchronize external iCal feeds into local reservations."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--tenant",
            dest="tenant_id",
            default=None,
            help="Optional tenant UUID to limit the sync to a single tenant.",
        )

    def handle(self, *args, **options) -> None:
        queryset = PropertyICalFeed.objects.filter(is_active=True).select_related(
            "property", "tenant"
        )
        tenant_id = options.get("tenant_id")
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        total_feeds = queryset.count()
        total_created = 0
        total_skipped = 0
        total_errors = 0

        for feed in queryset:
            self.stdout.write(f"-> {feed.tenant.name} | {feed.property.name} | {feed.label}")
            result = sync_ical_feed(feed)
            total_created += result["created"]
            total_skipped += result["skipped"]
            total_errors += len(result["errors"])
            status_msg = (
                f"   created={result['created']} skipped={result['skipped']} "
                f"errors={len(result['errors'])} status={feed.last_sync_status}"
            )
            if result["errors"]:
                self.stdout.write(self.style.WARNING(status_msg))
                for err in result["errors"]:
                    self.stdout.write(self.style.WARNING(f"     {err}"))
            else:
                self.stdout.write(self.style.SUCCESS(status_msg))

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. feeds={total_feeds} created={total_created} "
                f"skipped={total_skipped} errors={total_errors}"
            )
        )
