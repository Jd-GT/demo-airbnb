from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.constants import ModuleKey, PermissionLevel
from apps.core.models import Tenant
from apps.core.permissions import TenantModulePermission

from .models import PropertyICalFeed
from .serializers import PropertyICalFeedSerializer
from .services import sync_all_feeds_for_tenant, sync_ical_feed


class PropertyICalFeedViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD + sync actions for property iCal feeds."""

    serializer_class = PropertyICalFeedSerializer
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.INVENTORY.value
    lookup_url_kwarg = "feed_id"

    def get_tenant(self) -> Tenant:
        return get_object_or_404(Tenant, id=self.kwargs["tenant_id"])

    def get_queryset(self):
        return PropertyICalFeed.all_objects.filter(
            tenant_id=self.kwargs["tenant_id"]
        ).select_related("property", "tenant")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["tenant_id"] = self.kwargs["tenant_id"]
        return context

    def perform_create(self, serializer):
        serializer.save(tenant=self.get_tenant())

    @action(detail=True, methods=["post"], url_path="sync-now")
    def sync_now(self, request, tenant_id, feed_id):
        feed = self.get_object()
        result = sync_ical_feed(feed)
        return Response(
            {
                "feed_id": str(feed.id),
                "created": result["created"],
                "skipped": result["skipped"],
                "errors": result["errors"],
                "last_sync_status": feed.last_sync_status,
                "last_synced_at": feed.last_synced_at.isoformat() if feed.last_synced_at else None,
            }
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="sync-all",
        permission_classes=[permissions.IsAuthenticated, TenantModulePermission],
    )
    def sync_all(self, request, tenant_id):
        tenant = self.get_tenant()
        # require WRITE for bulk sync
        if not request.user.is_superuser and not request.user.is_owner:
            if not request.user.can_access_module(
                ModuleKey.INVENTORY.value, PermissionLevel.WRITE
            ):
                return Response({"detail": "Forbidden."}, status=403)
        aggregate = sync_all_feeds_for_tenant(tenant)
        return Response(aggregate)
