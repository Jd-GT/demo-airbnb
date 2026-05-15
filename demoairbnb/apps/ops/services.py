"""Operations services: task auto-creation, template rendering, PDF voucher."""

from __future__ import annotations

import io
import re
from datetime import date
from decimal import Decimal

from django.db import transaction

from .models import MessageTemplate, Task, TaskStatus, TaskType


# ---------- Auto-task generation ----------

@transaction.atomic
def ensure_cleaning_task_for_reservation(reservation) -> Task | None:
    """Create the post-checkout cleaning task if it doesn't exist yet.

    Called from the booking layer when a reservation is created confirmed
    or moves to CHECKED_OUT. Idempotent: returns the existing task on
    subsequent calls.
    """
    existing = Task.all_objects.filter(
        tenant_id=reservation.tenant_id,
        reservation=reservation,
        type=TaskType.CLEANING.value,
    ).first()
    if existing:
        return existing
    return Task.all_objects.create(
        tenant_id=reservation.tenant_id,
        property=reservation.property,
        reservation=reservation,
        type=TaskType.CLEANING.value,
        title=f'Limpieza post check-out — {reservation.property.name}',
        due_date=reservation.check_out,
        notes=(
            f'Reserva {reservation.id}\n'
            f'Huésped: {reservation.guest.name}\n'
            f'Check-out: {reservation.check_out}'
        ),
    )


# ---------- Template rendering ----------

PLACEHOLDER_RE = re.compile(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}')


def build_reservation_context(reservation) -> dict[str, str]:
    return {
        'guest_name': reservation.guest.name,
        'property_name': reservation.property.name,
        'property_address': reservation.property.address,
        'check_in': str(reservation.check_in),
        'check_out': str(reservation.check_out),
        'nights': str(reservation.nights),
        'total_amount': f'{reservation.total_amount:.2f}',
        'balance_due': f'{reservation.get_balance_due():.2f}',
        'amount_paid': f'{reservation.amount_paid:.2f}',
        'reservation_id': str(reservation.id),
        'tenant_name': reservation.tenant.name,
    }


def render_template(body: str, context: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        key = match.group(1)
        return context.get(key, match.group(0))

    return PLACEHOLDER_RE.sub(replace, body)


def render_message_for_reservation(
    template: MessageTemplate, reservation
) -> dict[str, str]:
    ctx = build_reservation_context(reservation)
    return {
        'channel': template.channel,
        'subject': render_template(template.subject or '', ctx),
        'body': render_template(template.body, ctx),
    }


# ---------- Voucher PDF ----------

def build_voucher_pdf(reservation) -> bytes:
    """Generate an A4 voucher PDF for a reservation using reportlab."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise RuntimeError(
            'reportlab no está instalado. pip install reportlab'
        ) from exc

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f'Voucher reserva {reservation.id}',
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleGold', parent=styles['Title'],
        textColor=colors.HexColor('#B08D57'),
    )
    label_style = ParagraphStyle(
        'Label', parent=styles['Normal'], textColor=colors.grey, fontSize=9,
    )

    story = []
    story.append(Paragraph(reservation.tenant.name, title_style))
    story.append(Paragraph('Comprobante de reserva', styles['Heading2']))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph(
        f'<b>Reserva #</b> {reservation.id}', styles['Normal']
    ))
    story.append(Paragraph(
        f'<b>Estado:</b> {reservation.status} '
        f'(pago: {reservation.payment_status})', styles['Normal']
    ))
    story.append(Spacer(1, 0.3 * cm))

    info_data = [
        ['Huésped', reservation.guest.name],
        ['Propiedad', reservation.property.name],
        ['Dirección', reservation.property.address],
        ['Check-in', str(reservation.check_in)],
        ['Check-out', str(reservation.check_out)],
        ['Noches', str(reservation.nights)],
    ]
    info_table = Table(info_data, colWidths=[4 * cm, 12 * cm])
    info_table.setStyle(
        TableStyle(
            [
                ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph('Detalle de cargos', styles['Heading3']))
    line_data = [['Descripción', 'Cant.', 'Precio', 'Subtotal']]
    for line in reservation.lines.all():
        line_data.append(
            [
                line.description,
                f'{line.quantity}',
                f'{line.unit_price:.2f}',
                f'{line.line_subtotal:.2f}',
            ]
        )
    line_data.append(
        ['', '', 'Subtotal', f'{reservation.subtotal_amount:.2f}']
    )
    if reservation.cleaning_fee:
        line_data.append(
            ['', '', 'Limpieza', f'{reservation.cleaning_fee:.2f}']
        )
    if reservation.tax_total:
        line_data.append(
            ['', '', 'Impuestos', f'{reservation.tax_total:.2f}']
        )
    line_data.append(['', '', 'TOTAL', f'{reservation.total_amount:.2f}'])
    line_data.append(['', '', 'Pagado', f'{reservation.amount_paid:.2f}'])
    line_data.append(['', '', 'Saldo', f'{reservation.get_balance_due():.2f}'])

    line_table = Table(line_data, colWidths=[8 * cm, 2 * cm, 3 * cm, 3 * cm])
    line_table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F2937')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (-2, -3), (-1, -1), 'Helvetica-Bold'),
            ]
        )
    )
    story.append(line_table)

    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            'Documento generado automáticamente. '
            'No es un comprobante fiscal sino un resumen de la reserva.',
            label_style,
        )
    )

    doc.build(story)
    return buf.getvalue()
