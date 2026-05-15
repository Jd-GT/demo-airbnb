from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.booking.models import Reservation

from .models import (
    AnalyticAccount,
    AnalyticLine,
    AnalyticLineCategory,
    EXPENSE_CATEGORIES,
    Payment,
    PaymentMethod,
    PaymentType,
    Tax,
    TaxType,
)


# ---------- Analytics ----------

class FinanceAnalyticsQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(required=False, min_value=2000, max_value=2100)
    month = serializers.IntegerField(required=False, min_value=1, max_value=12)


class MonthlyRevenuePointSerializer(serializers.Serializer):
    month_index = serializers.IntegerField()
    month = serializers.CharField()
    ingresos = serializers.DecimalField(max_digits=14, decimal_places=2)


class RevenueByPropertySerializer(serializers.Serializer):
    property_id = serializers.UUIDField()
    name = serializers.CharField()
    ingresos = serializers.DecimalField(max_digits=14, decimal_places=2)


class FinanceAnalyticsSerializer(serializers.Serializer):
    monthly_revenue_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    annual_revenue_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    monthly_revenue_series = MonthlyRevenuePointSerializer(many=True)
    revenue_by_property = RevenueByPropertySerializer(many=True)


# ---------- Tax ----------

class TaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = [
            'id',
            'name',
            'value',
            'type',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ---------- Cost centers (AnalyticAccount) ----------

class AnalyticAccountSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = AnalyticAccount
        fields = [
            'id',
            'name',
            'property',
            'property_name',
            'is_active',
            'balance',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'property_name', 'balance', 'created_at', 'updated_at']

    def get_balance(self, obj) -> str:
        return str(obj.get_balance())


class AnalyticLineSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = AnalyticLine
        fields = [
            'id',
            'account',
            'account_name',
            'date',
            'amount',
            'category',
            'description',
            'reference_type',
            'reference_id',
            'created_at',
        ]
        read_only_fields = ['id', 'account_name', 'created_at']


class ExpenseCreateSerializer(serializers.Serializer):
    """Manual expense entry: creates a negative AnalyticLine in some account."""

    account_id = serializers.UUIDField()
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))
    category = serializers.ChoiceField(
        choices=[c for c in AnalyticLineCategory.choices if c[0] in EXPENSE_CATEGORIES],
    )
    description = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        tenant_id = self.context['tenant_id']
        account = AnalyticAccount.all_objects.filter(
            id=attrs['account_id'], tenant_id=tenant_id
        ).first()
        if not account:
            raise serializers.ValidationError(
                {'account_id': 'Cost center not found for tenant.'}
            )
        attrs['account'] = account
        return attrs

    def create(self, validated_data):
        from .services import register_expense

        request = self.context['request']
        return register_expense(
            tenant_id=self.context['tenant_id'],
            account=validated_data['account'],
            amount=validated_data['amount'],
            category=validated_data['category'],
            date=validated_data['date'],
            description=validated_data.get('description', ''),
            recorded_by=request.user,
        )

    def to_representation(self, instance):
        return AnalyticLineSerializer(instance).data


# ---------- Payment ----------

class PaymentSerializer(serializers.ModelSerializer):
    reservation_label = serializers.SerializerMethodField()
    is_lodging = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id',
            'reservation',
            'reservation_label',
            'date',
            'amount',
            'type',
            'is_lodging',
            'method',
            'reference',
            'notes',
            'recorded_by',
            'created_at',
        ]
        read_only_fields = [
            'id', 'reservation_label', 'is_lodging',
            'recorded_by', 'created_at',
        ]

    def get_reservation_label(self, obj) -> str:
        return f'{obj.reservation.guest.name} — {obj.reservation.property.name}'

    def get_is_lodging(self, obj) -> bool:
        from .models import LODGING_PAYMENT_TYPES
        return obj.type in LODGING_PAYMENT_TYPES


class PaymentCreateSerializer(serializers.Serializer):
    reservation_id = serializers.UUIDField()
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    type = serializers.ChoiceField(
        choices=[c[0] for c in PaymentType.choices], default=PaymentType.ADVANCE.value
    )
    method = serializers.ChoiceField(
        choices=[c[0] for c in PaymentMethod.choices], default=PaymentMethod.CASH.value
    )
    reference = serializers.CharField(required=False, allow_blank=True, default='')
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        tenant_id = self.context['tenant_id']
        reservation = Reservation.all_objects.filter(
            id=attrs['reservation_id'], tenant_id=tenant_id
        ).first()
        if not reservation:
            raise serializers.ValidationError(
                {'reservation_id': 'Reservation not found for tenant.'}
            )
        attrs['reservation'] = reservation
        return attrs

    def create(self, validated_data):
        from .services import register_payment

        request = self.context['request']
        return register_payment(
            reservation=validated_data['reservation'],
            amount=validated_data['amount'],
            method=validated_data['method'],
            type=validated_data['type'],
            date=validated_data['date'],
            reference=validated_data.get('reference', ''),
            notes=validated_data.get('notes', ''),
            recorded_by=request.user,
        )

    def to_representation(self, instance):
        return PaymentSerializer(instance).data


# ---------- P&L ----------

class ProfitAndLossQuerySerializer(serializers.Serializer):
    account_id = serializers.UUIDField(required=False)
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)


class ProfitAndLossSerializer(serializers.Serializer):
    income = serializers.DecimalField(max_digits=14, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=14, decimal_places=2)
    net = serializers.DecimalField(max_digits=14, decimal_places=2)
    by_category = serializers.DictField(
        child=serializers.DecimalField(max_digits=14, decimal_places=2)
    )
