"""Ops admin: tasks and message templates."""

from django.contrib import admin

from .models import MessageTemplate, Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'tenant', 'property', 'type', 'status', 'due_date',
        'assigned_to',
    )
    list_filter = ('status', 'type', 'tenant')
    search_fields = ('title', 'notes')
    date_hierarchy = 'due_date'


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'channel', 'is_active')
    list_filter = ('channel', 'is_active', 'tenant')
    search_fields = ('name',)
