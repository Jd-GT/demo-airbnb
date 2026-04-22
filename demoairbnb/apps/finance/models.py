"""Finance domain models for Sprint 2+."""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantAwareModel
from apps.inventory.models import Property


class PropertyProfitabilityReport(TenantAwareModel):
    """Profit & Loss report per property for a given period."""

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="profitability_reports"
    )
    year = models.IntegerField()
    month = models.IntegerField()

    # Revenue
    gross_revenue = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Ingresos totales brutos"
    )
    commissions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Comisiones OTA, gastos transaccionales",
    )
    net_revenue = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Ingresos netos"
    )

    # Expenses
    cleaning_costs = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Costos de limpieza"
    )
    maintenance_costs = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Costos de mantenimiento"
    )
    utilities_costs = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Servicios (agua, luz, internet)"
    )
    platform_fees = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Cuota plataforma (Airbnb, Booking, etc.)",
    )
    property_management_fee = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Cuota gestión"
    )
    other_expenses = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Otros gastos"
    )

    # Totals
    total_expenses = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Total gastos"
    )
    net_profit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Utilidad neta"
    )
    profit_margin = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Margen de utilidad (%)",
    )

    # Metrics
    occupied_nights = models.IntegerField(default=0, help_text="Noches ocupadas")
    total_nights = models.IntegerField(default=0, help_text="Total noches en período")
    occupancy_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, help_text="Tasa ocupación (%)"
    )
    avg_daily_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Tarifa diaria promedio (ADR)",
    )
    revenue_per_available_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Ingresos por noche disponible (RevPAR)",
    )

    class Meta:
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(
                fields=["property", "year", "month"],
                name="unique_property_profitability_period",
            )
        ]

    def __str__(self) -> str:
        return f"{self.property.name} - {self.year}/{self.month:02d}"


class Voucher(TenantAwareModel):
    """Voucher/Receipt for guest stays or transactions."""

    STATUS_CHOICES = [
        ("issued", "Emitido"),
        ("sent", "Enviado"),
        ("downloaded", "Descargado"),
        ("voided", "Anulado"),
    ]

    reference_number = models.CharField(
        max_length=50, unique=True, help_text="Número único de referencia"
    )
    voucher_type = models.CharField(
        max_length=20,
        choices=[
            ("stay", "Comprobante de Estadía"),
            ("payment", "Recibo de Pago"),
            ("invoice", "Factura"),
        ],
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="issued")

    # Related data
    guest_name = models.CharField(max_length=160)
    guest_email = models.EmailField()
    property_name = models.CharField(max_length=160)

    # Financial data
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Dates
    issue_date = models.DateField(auto_now_add=True)
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)

    # PDF storage
    pdf_file = models.FileField(
        upload_to="vouchers/%Y/%m/",
        null=True,
        blank=True,
        help_text="PDF generado almacenado",
    )

    # Metadata
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-issue_date"]

    def __str__(self) -> str:
        return f"{self.reference_number} - {self.guest_name}"

