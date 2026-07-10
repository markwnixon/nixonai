from sqlalchemy import or_
from webapp import db
from webapp.models import Orders, People


EMAIL_FIELDS = [
    ('Saljp', 'primary_broker_name'),
    ('Emailjp', 'primary_broker_email'),
    ('Saloa', 'support_broker_name'),
    ('Emailoa', 'support_broker_email'),
    ('Salap', 'ap_name'),
    ('Emailap', 'ap_email'),
]


def clean_value(value):
    return str(value).strip() if value is not None else ''


def is_blank_value(value):
    return clean_value(value).lower() in ['', 'none', 'null', 'nan', 'n/a', 'na']


def clean_contact_value(value):
    return '' if is_blank_value(value) else clean_value(value)


def clean_email_value(value):
    value = clean_contact_value(value)
    return value if '@' in value else ''


def active_order_filter():
    return or_(Orders.Hstat < 2, Orders.Hstat.is_(None))


def format_date(value):
    return value.strftime('%Y-%m-%d') if value else ''


def contact_values_from_order(order):
    values = {form_name: clean_contact_value(getattr(order, field_name, None)) for field_name, form_name in EMAIL_FIELDS}
    customer = customer_for_order_shipper(order)
    if customer is None:
        return values
    fallback_map = customer_email_values(customer)
    for key, fallback in fallback_map.items():
        if not clean_email_value(values.get(key)) and fallback:
            values[key] = fallback
    return values


def order_email_values(order):
    return {
        'primary_broker_email': clean_email_value(getattr(order, 'Emailjp', None)),
        'support_broker_email': clean_email_value(getattr(order, 'Emailoa', None)),
        'ap_email': clean_email_value(getattr(order, 'Emailap', None)),
    }


def customer_email_values(customer):
    if customer is None:
        return {
            'primary_broker_email': '',
            'support_broker_email': '',
            'ap_email': '',
        }
    return {
        'primary_broker_email': clean_email_value(customer.Email),
        'support_broker_email': clean_email_value(customer.Associate1),
        'ap_email': clean_email_value(customer.Associate2),
    }


def any_email_defined(email_values):
    return any(email_values.get(key) for key in ['primary_broker_email', 'support_broker_email', 'ap_email'])


def customer_for_order_shipper(order):
    shipper = clean_value(getattr(order, 'Shipper', None))
    if not shipper:
        return None
    return People.query.filter(People.Company == shipper).first()


def active_orders_for_shipper(shipper):
    return (
        Orders.query
        .filter(active_order_filter())
        .filter(Orders.Shipper == clean_value(shipper))
        .order_by(Orders.Date3.desc(), Orders.Date.desc(), Orders.id.desc())
        .all()
    )


def active_job_summary(order):
    return {
        'id': order.id,
        'jo': clean_value(order.Jo),
        'container': clean_value(order.Container),
        'booking': clean_value(order.Booking) or clean_value(order.BOL),
        'delivery_date': format_date(order.Date3),
        'hstat': order.Hstat,
        'delivery_location': clean_value(order.Company2),
    }


def shipper_email_context(shipper):
    shipper = clean_value(shipper)
    if not shipper:
        return None
    orders = active_orders_for_shipper(shipper)
    if not orders:
        return None
    return {
        'shipper': shipper,
        'active_count': len(orders),
        'values': contact_values_from_order(orders[0]),
        'jobs': [active_job_summary(order) for order in orders],
    }


def order_email_context(order_id):
    order = Orders.query.get(order_id)
    if order is None:
        return None
    shipper = clean_value(order.Shipper)
    if not shipper:
        return None
    orders = active_orders_for_shipper(shipper)
    customer = customer_for_order_shipper(order)
    order_emails = order_email_values(order)
    shipper_emails = customer_email_values(customer)
    return {
        'shipper': shipper,
        'selected_jo': clean_value(order.Jo),
        'selected_container': clean_value(order.Container),
        'active_count': len(orders),
        'values': contact_values_from_order(order),
        'jobs': [active_job_summary(active_order) for active_order in orders],
        'no_order_emails': not any_email_defined(order_emails),
        'shipper_emails': shipper_emails,
        'people_match_found': customer is not None,
    }


def validate_contact_payload(payload):
    values = {}
    errors = []
    for _field_name, form_name in EMAIL_FIELDS:
        value = clean_value(payload.get(form_name))
        if len(value) > 45:
            errors.append(f'{form_name.replace("_", " ").title()} must be 45 characters or less.')
        values[form_name] = value
    for form_name in ['primary_broker_email', 'support_broker_email', 'ap_email']:
        value = values.get(form_name)
        if value and '@' not in value:
            errors.append(f'{form_name.replace("_", " ").title()} must be a valid email address.')
    return values, errors


def update_active_shipper_emails(shipper, payload):
    shipper = clean_value(shipper)
    if not shipper:
        return {'ok': False, 'error': 'Choose a shipper first.', 'updated': 0}
    values, errors = validate_contact_payload(payload)
    if errors:
        return {'ok': False, 'error': ' '.join(errors), 'updated': 0}
    orders = (
        Orders.query
        .filter(active_order_filter())
        .filter(Orders.Shipper == shipper)
        .all()
    )
    if not orders:
        return {'ok': False, 'error': 'No active jobs were found for that shipper.', 'updated': 0}
    for order in orders:
        for field_name, form_name in EMAIL_FIELDS:
            setattr(order, field_name, values.get(form_name) or None)
    db.session.commit()
    return {'ok': True, 'error': '', 'updated': len(orders)}
