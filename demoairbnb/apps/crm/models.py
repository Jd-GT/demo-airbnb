from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TenantAwareModel


class ContactType(models.TextChoices):
    GUEST = 'GUEST', 'Guest'
    AGENT = 'AGENT', 'Agent'
    PLATFORM = 'PLATFORM', 'Platform'


class LeadStage(models.TextChoices):
    NEW = 'NEW', 'New'
    QUOTED = 'QUOTED', 'Quoted'
    WON = 'WON', 'Won'
    LOST = 'LOST', 'Lost'


class Contact(TenantAwareModel):
    name = models.CharField(max_length=160)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    type = models.CharField(
        max_length=16, choices=ContactType.choices, default=ContactType.GUEST
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Only applies for AGENT type contacts.',
    )

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'email'],
                name='tenant_unique_contact_email',
                condition=~models.Q(email=''),
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Lead(TenantAwareModel):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='leads')
    source = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_leads',
    )
    stage = models.CharField(
        max_length=16, choices=LeadStage.choices, default=LeadStage.NEW
    )
    desired_check_in = models.DateField(null=True, blank=True)
    desired_check_out = models.DateField(null=True, blank=True)
    expected_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Lead {self.id} - {self.contact.name}'
