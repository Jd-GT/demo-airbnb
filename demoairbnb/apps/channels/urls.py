from django.urls import path

from .views import PropertyICalFeedViewSet


feed_list = PropertyICalFeedViewSet.as_view(
    {"get": "list", "post": "create"}
)
feed_detail = PropertyICalFeedViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)
feed_sync_now = PropertyICalFeedViewSet.as_view({"post": "sync_now"})
feed_sync_all = PropertyICalFeedViewSet.as_view({"post": "sync_all"})


urlpatterns = [
    path(
        "tenants/<uuid:tenant_id>/channels/ical-feeds/",
        feed_list,
        name="ical-feed-list",
    ),
    path(
        "tenants/<uuid:tenant_id>/channels/ical-feeds/sync-all/",
        feed_sync_all,
        name="ical-feed-sync-all",
    ),
    path(
        "tenants/<uuid:tenant_id>/channels/ical-feeds/<uuid:feed_id>/",
        feed_detail,
        name="ical-feed-detail",
    ),
    path(
        "tenants/<uuid:tenant_id>/channels/ical-feeds/<uuid:feed_id>/sync-now/",
        feed_sync_now,
        name="ical-feed-sync-now",
    ),
]
