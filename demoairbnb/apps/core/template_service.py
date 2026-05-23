"""Service for rendering and sending email/message templates."""

from __future__ import annotations

from typing import Any

from jinja2 import Template, TemplateError


def render_template(template_body: str, context: dict[str, Any]) -> str:
    """
    Render a Jinja2 template with the provided context.

    Args:
        template_body: The template string with variables like {{guest_name}}
        context: Dictionary of variables to use in rendering

    Returns:
        Rendered template as string

    Raises:
        TemplateError: If template rendering fails
    """
    try:
        template = Template(template_body)
        return template.render(**context)
    except TemplateError as e:
        raise ValueError(f"Error rendering template: {str(e)}") from e


def render_subject(subject: str, context: dict[str, Any]) -> str:
    """
    Render email subject with template variables.

    Args:
        subject: Email subject with variables
        context: Dictionary of variables

    Returns:
        Rendered subject
    """
    return render_template(subject, context)


def extract_template_variables(text: str) -> list[str]:
    """
    Extract all Jinja2 variable names from a template string.

    Args:
        text: Template string

    Returns:
        List of variable names found
    """
    import re

    # Find all {{variable}} patterns
    pattern = r'\{\{(\s*[\w_\.]+\s*)\}\}'
    matches = re.findall(pattern, text)
    return [m.strip() for m in matches]


class TemplateContext:
    """Helper class to build template context for different events."""

    @staticmethod
    def booking_confirmation(guest_name: str, property_name: str, check_in: str,
                           check_out: str, total_amount: str, confirmation_code: str) -> dict[str, Any]:
        """Context for booking confirmation email."""
        return {
            'guest_name': guest_name,
            'property_name': property_name,
            'check_in': check_in,
            'check_out': check_out,
            'total_amount': total_amount,
            'confirmation_code': confirmation_code,
        }

    @staticmethod
    def booking_reminder(guest_name: str, property_name: str, check_in: str,
                        check_out: str, address: str, wifi_password: str = "") -> dict[str, Any]:
        """Context for booking reminder email."""
        return {
            'guest_name': guest_name,
            'property_name': property_name,
            'check_in': check_in,
            'check_out': check_out,
            'address': address,
            'wifi_password': wifi_password,
        }

    @staticmethod
    def payment_receipt(guest_name: str, property_name: str, reservation_id: str,
                       amount: str, payment_method: str, payment_date: str) -> dict[str, Any]:
        """Context for payment receipt email."""
        return {
            'guest_name': guest_name,
            'property_name': property_name,
            'reservation_id': reservation_id,
            'amount': amount,
            'payment_method': payment_method,
            'payment_date': payment_date,
        }

    @staticmethod
    def owner_summary(owner_name: str, total_revenue: str, new_bookings: int,
                     occupancy_rate: str, date_range: str) -> dict[str, Any]:
        """Context for daily owner summary email."""
        return {
            'owner_name': owner_name,
            'total_revenue': total_revenue,
            'new_bookings': new_bookings,
            'occupancy_rate': occupancy_rate,
            'date_range': date_range,
        }
