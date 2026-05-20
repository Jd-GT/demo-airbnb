"""URL routes for ops app: tasks, templates, voucher."""

from django.urls import path

from .views import (
    MessageTemplateViewSet,
    RenderReservationMessageView,
    TaskCompleteView,
    TaskViewSet,
    VoucherPDFView,
)

task_list = TaskViewSet.as_view({'get': 'list', 'post': 'create'})
task_detail = TaskViewSet.as_view(
    {
        'get': 'retrieve',
        'patch': 'partial_update',
        'put': 'update',
        'delete': 'destroy',
    }
)

template_list = MessageTemplateViewSet.as_view({'get': 'list', 'post': 'create'})
template_detail = MessageTemplateViewSet.as_view(
    {
        'get': 'retrieve',
        'patch': 'partial_update',
        'put': 'update',
        'delete': 'destroy',
    }
)

urlpatterns = [
    path(
        'tenants/<uuid:tenant_id>/ops/tasks/',
        task_list,
        name='ops-task-list',
    ),
    path(
        'tenants/<uuid:tenant_id>/ops/tasks/<uuid:task_id>/',
        task_detail,
        name='ops-task-detail',
    ),
    path(
        'tenants/<uuid:tenant_id>/ops/tasks/<uuid:task_id>/complete/',
        TaskCompleteView.as_view(),
        name='ops-task-complete',
    ),
    path(
        'tenants/<uuid:tenant_id>/ops/templates/',
        template_list,
        name='ops-template-list',
    ),
    path(
        'tenants/<uuid:tenant_id>/ops/templates/<uuid:template_id>/',
        template_detail,
        name='ops-template-detail',
    ),
    path(
        'tenants/<uuid:tenant_id>/ops/render-message/',
        RenderReservationMessageView.as_view(),
        name='ops-render-message',
    ),
    path(
        'tenants/<uuid:tenant_id>/ops/voucher/<uuid:reservation_id>.pdf',
        VoucherPDFView.as_view(),
        name='ops-voucher-pdf',
    ),
]
