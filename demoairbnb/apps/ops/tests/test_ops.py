"""Tests for the ops app: Tasks, MessageTemplate, voucher PDF."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.booking.services import create_reservation
from apps.core.constants import SystemRole
from apps.core.services import create_tenant_user, create_tenant_with_owner
from apps.crm.models import Contact, ContactType
from apps.inventory.models import Property
from apps.ops.models import (
    MessageChannel,
    MessageTemplate,
    Task,
    TaskStatus,
    TaskType,
)


class CleaningTaskAutoCreateTests(APITestCase):
    def test_creating_reservation_creates_cleaning_task(self):
        tenant, owner = create_tenant_with_owner(
            name='Ops Auto', subdomain='ops-auto',
            owner_email='ops@a.com', owner_password='ownerpass123',
            owner_full_name='Ops',
        )
        prop = Property.all_objects.create(
            tenant=tenant, name='Casa', address='X',
            capacity_adults=2, base_price=Decimal('100'),
            cleaning_fee=Decimal('0'),
        )
        guest = Contact.all_objects.create(
            tenant=tenant, name='G', type=ContactType.GUEST.value
        )
        reservation = create_reservation(
            tenant_id=tenant.id, property_obj=prop, guest=guest,
            check_in=date(2026, 7, 1), check_out=date(2026, 7, 4),
            created_by=owner,
        )
        task = Task.all_objects.filter(
            reservation=reservation, type=TaskType.CLEANING.value
        ).first()
        self.assertIsNotNone(task)
        self.assertEqual(task.due_date, date(2026, 7, 4))
        self.assertEqual(task.status, TaskStatus.PENDING.value)


class CleanerScopingTests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name='Cleaner', subdomain='cleaner',
            owner_email='c@c.com', owner_password='ownerpass123',
            owner_full_name='Owner',
        )
        # Cleaner has system_role=CLEANER
        from apps.core.models import User as UserModel

        self.cleaner = UserModel.objects.create_user(
            email='cleaner@c.com',
            password='cleanerpass123',
            full_name='Carlos Cleaner',
            tenant=self.tenant,
            system_role=SystemRole.CLEANER.value,
        )
        prop = Property.all_objects.create(
            tenant=self.tenant, name='Casa', address='X',
            capacity_adults=2, base_price=Decimal('80'),
            cleaning_fee=Decimal('0'),
        )
        guest = Contact.all_objects.create(
            tenant=self.tenant, name='G', type=ContactType.GUEST.value
        )
        # One task assigned to the cleaner, one not
        self.assigned_task = Task.all_objects.create(
            tenant=self.tenant, property=prop,
            type=TaskType.CLEANING.value,
            title='Limpieza A', due_date=date(2026, 8, 1),
            assigned_to=self.cleaner,
        )
        self.other_task = Task.all_objects.create(
            tenant=self.tenant, property=prop,
            type=TaskType.CLEANING.value,
            title='Limpieza B', due_date=date(2026, 8, 2),
        )

    def test_cleaner_only_sees_own_tasks(self):
        self.client.force_authenticate(self.cleaner)
        url = f'/api/tenants/{self.tenant.id}/ops/tasks/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {t['id'] for t in resp.data}
        self.assertEqual(ids, {str(self.assigned_task.id)})

    def test_cleaner_can_complete_own_task(self):
        self.client.force_authenticate(self.cleaner)
        url = (
            f'/api/tenants/{self.tenant.id}/ops/tasks/'
            f'{self.assigned_task.id}/complete/'
        )
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assigned_task.refresh_from_db()
        self.assertEqual(self.assigned_task.status, TaskStatus.DONE.value)
        self.assertIsNotNone(self.assigned_task.completed_at)

    def test_cleaner_cannot_complete_others_task(self):
        self.client.force_authenticate(self.cleaner)
        url = (
            f'/api/tenants/{self.tenant.id}/ops/tasks/'
            f'{self.other_task.id}/complete/'
        )
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class MessageTemplateRenderTests(APITestCase):
    def test_render_replaces_placeholders(self):
        tenant, owner = create_tenant_with_owner(
            name='Templates', subdomain='templates',
            owner_email='t@t.com', owner_password='ownerpass123',
            owner_full_name='Templates',
        )
        prop = Property.all_objects.create(
            tenant=tenant, name='Apto Mar', address='Cra 1 #2-3',
            capacity_adults=2, base_price=Decimal('120'),
            cleaning_fee=Decimal('0'),
        )
        guest = Contact.all_objects.create(
            tenant=tenant, name='Juana Pérez', type=ContactType.GUEST.value
        )
        reservation = create_reservation(
            tenant_id=tenant.id, property_obj=prop, guest=guest,
            check_in=date(2026, 9, 1), check_out=date(2026, 9, 4),
            created_by=owner,
        )
        template = MessageTemplate.all_objects.create(
            tenant=tenant,
            name='Confirmación',
            channel=MessageChannel.WHATSAPP.value,
            subject='Reserva en {{property_name}}',
            body=(
                'Hola {{guest_name}}, confirmamos tu reserva en '
                '{{property_name}} ({{property_address}}) del '
                '{{check_in}} al {{check_out}}. Total: ${{total_amount}}.'
            ),
        )
        self.client.force_authenticate(owner)
        resp = self.client.post(
            f'/api/tenants/{tenant.id}/ops/render-message/',
            {'template_id': str(template.id), 'reservation_id': str(reservation.id)},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        body = resp.data['body']
        self.assertIn('Juana Pérez', body)
        self.assertIn('Apto Mar', body)
        self.assertIn('Cra 1 #2-3', body)
        self.assertIn('2026-09-01', body)
        self.assertEqual(resp.data['subject'], 'Reserva en Apto Mar')


class VoucherPdfTests(APITestCase):
    def test_voucher_pdf_download(self):
        tenant, owner = create_tenant_with_owner(
            name='Voucher', subdomain='voucher',
            owner_email='v@v.com', owner_password='ownerpass123',
            owner_full_name='V',
        )
        prop = Property.all_objects.create(
            tenant=tenant, name='Casa', address='X',
            capacity_adults=2, base_price=Decimal('150'),
            cleaning_fee=Decimal('20'),
        )
        guest = Contact.all_objects.create(
            tenant=tenant, name='G', type=ContactType.GUEST.value
        )
        reservation = create_reservation(
            tenant_id=tenant.id, property_obj=prop, guest=guest,
            check_in=date(2026, 7, 10), check_out=date(2026, 7, 12),
            created_by=owner,
        )
        self.client.force_authenticate(owner)
        url = (
            f'/api/tenants/{tenant.id}/ops/voucher/{reservation.id}.pdf'
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))
