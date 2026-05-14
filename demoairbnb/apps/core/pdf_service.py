"""
PDF generation service using ReportLab.
Generates professional PDFs for reservation vouchers and profitability reports.
"""

from io import BytesIO
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# Color scheme matching the app branding
GOLD_COLOR = colors.HexColor('#C9A227')
DARK_COLOR = colors.HexColor('#1a4a4b')
LIGHT_BG = colors.HexColor('#f5f1e8')


def generate_reservation_voucher_pdf(
    guest_name: str,
    property_name: str,
    check_in: str,
    check_out: str,
    nights: int,
    subtotal: Decimal,
    cleaning_fee: Decimal,
    total_amount: Decimal,
    confirmation_code: str,
    amenities: List[str] = None,
    cancellation_policy: str = "Flexible",
) -> bytes:
    """
    Generate a professional reservation voucher PDF.
    
    Args:
        guest_name: Full name of the guest
        property_name: Name of the property
        check_in: Check-in date (ISO format or readable string)
        check_out: Check-out date (ISO format or readable string)
        nights: Number of nights
        subtotal: Subtotal amount
        cleaning_fee: Cleaning fee amount
        total_amount: Total payment amount
        confirmation_code: Reservation confirmation code
        amenities: List of property amenities
        cancellation_policy: Cancellation policy description
    
    Returns:
        PDF content as bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=GOLD_COLOR,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=DARK_COLOR,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK_COLOR,
        spaceAfter=4,
    )
    
    # Build content
    elements = []
    
    # Header
    elements.append(Paragraph("VOUCHER DE RESERVA", title_style))
    elements.append(Spacer(1, 0.15*inch))
    
    # Confirmation code box
    conf_data = [
        [Paragraph(f"<b>CÓDIGO: {confirmation_code}</b>", 
                  ParagraphStyle('ConfCode', parent=styles['Normal'], fontSize=11, 
                               textColor=GOLD_COLOR, alignment=TA_CENTER))]
    ]
    conf_table = Table(conf_data, colWidths=[6*inch])
    conf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('BORDER', (0, 0), (-1, -1), 1, GOLD_COLOR),
    ]))
    elements.append(conf_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Guest and property info
    elements.append(Paragraph("INFORMACIÓN DEL HUÉSPED", heading_style))
    guest_data = [
        ["Nombre:", Paragraph(guest_name, normal_style)],
        ["Propiedad:", Paragraph(property_name, normal_style)],
    ]
    guest_table = Table(guest_data, colWidths=[1.5*inch, 4.5*inch])
    guest_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BG),
        ('TEXTCOLOR', (0, 0), (0, -1), DARK_COLOR),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(guest_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # Stay details
    elements.append(Paragraph("DETALLES DE ESTADÍA", heading_style))
    stay_data = [
        ["Entrada:", check_in, "Salida:", check_out],
        ["Noches:", str(nights), "Noches totales", f"{nights} noches"],
    ]
    stay_table = Table(stay_data, colWidths=[1.2*inch, 1.3*inch, 1.2*inch, 2.3*inch])
    stay_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('TEXTCOLOR', (0, 0), (-1, -1), DARK_COLOR),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(stay_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # Pricing breakdown
    elements.append(Paragraph("RESUMEN DE PAGO", heading_style))
    price_data = [
        ["Concepto", "Valor"],
        [f"Subtotal ({nights} noches)", f"${float(subtotal):,.2f}"],
        ["Tarifa de limpieza", f"${float(cleaning_fee):,.2f}"],
        [Paragraph("<b>TOTAL</b>", normal_style), 
         Paragraph(f"<b>${float(total_amount):,.2f}</b>", 
                  ParagraphStyle('Total', parent=normal_style, textColor=GOLD_COLOR))],
    ]
    price_table = Table(price_data, colWidths=[3.5*inch, 2.5*inch])
    price_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_BG),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(price_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # Amenities if provided
    if amenities:
        elements.append(Paragraph("SERVICIOS Y COMODIDADES", heading_style))
        amenities_text = "<br/>".join([f"• {a}" for a in amenities])
        elements.append(Paragraph(amenities_text, normal_style))
        elements.append(Spacer(1, 0.15*inch))
    
    # Cancellation policy
    elements.append(Paragraph("POLÍTICA DE CANCELACIÓN", heading_style))
    elements.append(Paragraph(cancellation_policy, normal_style))
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    elements.append(Paragraph(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", footer_style))
    
    # Build PDF
    doc.build(elements)
    return buffer.getvalue()


def generate_property_report_pdf(
    property_name: str,
    period: str,
    total_revenue: Decimal,
    occupancy_rate: float,
    nights_booked: int,
    num_reservations: int,
    avg_daily_rate: Decimal,
    operating_expenses: Decimal = None,
    net_profit: Decimal = None,
) -> bytes:
    """
    Generate a professional property profitability report PDF.
    
    Args:
        property_name: Name of the property
        period: Period description (e.g., "Enero 2026")
        total_revenue: Total revenue amount
        occupancy_rate: Occupancy percentage (0-100)
        nights_booked: Number of nights booked
        num_reservations: Number of reservations
        avg_daily_rate: Average daily rate (ADR)
        operating_expenses: Optional operating expenses
        net_profit: Optional net profit
    
    Returns:
        PDF content as bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=GOLD_COLOR,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=DARK_COLOR,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    
    heading_style = ParagraphStyle(
        'ReportHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=DARK_COLOR,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'ReportNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK_COLOR,
        spaceAfter=4,
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("REPORTE DE RENTABILIDAD", title_style))
    elements.append(Paragraph(f"{property_name} - {period}", subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # KPI Summary
    elements.append(Paragraph("INDICADORES CLAVE", heading_style))
    
    kpi_data = [
        ["Métrica", "Valor"],
        ["Ingresos Totales", f"${float(total_revenue):,.2f}"],
        ["Tasa de Ocupación", f"{occupancy_rate:.1f}%"],
        ["Noches Reservadas", str(nights_booked)],
        ["Número de Reservas", str(num_reservations)],
        ["ADR (Tarifa Diaria Promedio)", f"${float(avg_daily_rate):,.2f}"],
    ]
    
    if operating_expenses:
        kpi_data.append(["Gastos Operativos", f"${float(operating_expenses):,.2f}"])
    
    if net_profit:
        kpi_data.append(["Utilidad Neta", f"${float(net_profit):,.2f}"])
    
    kpi_table = Table(kpi_data, colWidths=[3.5*inch, 2.5*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_BG),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, colors.white]),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Analysis
    elements.append(Paragraph("ANÁLISIS", heading_style))
    analysis_text = f"""
    <b>Ocupación:</b> Con una tasa de ocupación del {occupancy_rate:.1f}%, la propiedad ha generado 
    ${float(total_revenue):,.2f} en ingresos durante el período.<br/><br/>
    
    <b>Desempeño de Reservas:</b> Se registraron {num_reservations} reservas con un total de 
    {nights_booked} noches reservadas, resultando en un ADR (Tarifa Diaria Promedio) de 
    ${float(avg_daily_rate):,.2f}.<br/><br/>
    """
    
    if operating_expenses and net_profit:
        profit_margin = (float(net_profit) / float(total_revenue) * 100) if total_revenue > 0 else 0
        analysis_text += f"""
        <b>Rentabilidad:</b> Después de gastos operativos de ${float(operating_expenses):,.2f}, 
        la utilidad neta es ${float(net_profit):,.2f}, representando un margen de {profit_margin:.1f}%.
        """
    
    elements.append(Paragraph(analysis_text, normal_style))
    
    # Footer
    elements.append(Spacer(1, 0.2*inch))
    footer_style = ParagraphStyle(
        'ReportFooter',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    elements.append(Paragraph(
        f"Reporte generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Confidencial",
        footer_style
    ))
    
    # Build PDF
    doc.build(elements)
    return buffer.getvalue()


def html_to_pdf(html_string: str) -> bytes:
    """
    Legacy function for compatibility. 
    Note: ReportLab doesn't directly support HTML conversion.
    Use generate_reservation_voucher_pdf or generate_property_report_pdf instead.
    
    Args:
        html_string: HTML content (ignored, for backward compatibility)
    
    Returns:
        Empty PDF bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = [Paragraph("No HTML support with ReportLab", getSampleStyleSheet()['Normal'])]
    doc.build(elements)
    return buffer.getvalue()
