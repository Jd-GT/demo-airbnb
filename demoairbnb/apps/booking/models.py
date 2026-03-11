from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from apps.core.models import TenantAwareModel


class ReservationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    CONFIRMED = "CONFIRMED", "Confirmed"
    CANCELLED = "CANCELLED", "Cancelled"


class Reservation(TenantAwareModel):
    property = models.ForeignKey("inventory.Property", on_delete=models.PROTECT, related_name="reservations")
    guest = models.ForeignKey("crm.Contact", on_delete=models.PROTECT, related_name="guest_reservations")
    agent = models.ForeignKey(
        "crm.Contact",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="agent_reservations",
    )
    check_in = models.DateField()
    check_out = models.DateField()
    nights = models.PositiveIntegerField(default=1)
    subtotal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
    )
    cleaning_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
    )
    status = models.CharField(max_length=16, choices=ReservationStatus.choices, default=ReservationStatus.CONFIRMED)
    created_by = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-check_in", "-created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(check_out__gt=F("check_in")),
                name="reservation_check_out_after_check_in",
            ),
        ]

    def __str__(self) -> str:
        return f"Reservation {self.id}"
