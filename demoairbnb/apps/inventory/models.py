from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TenantAwareModel


class Amenity(TenantAwareModel):
    name = models.CharField(max_length=120)
    icon_key = models.CharField(max_length=80, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "name"], name="tenant_unique_amenity_name")
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Property(TenantAwareModel):
    name = models.CharField(max_length=160)
    address = models.TextField()
    capacity_adults = models.PositiveIntegerField(default=1)
    capacity_kids = models.PositiveIntegerField(default=0)
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    cleaning_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
    )
    amenities = models.ManyToManyField(Amenity, related_name="properties", blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "name"], name="tenant_unique_property_name"),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
