from sqlalchemy import or_

from webapp import db
from webapp.models import Orders


RC_STAGE_LABELS = {
    0: 'No Rate Con Needed',
    1: 'Needs Rate Con',
    2: 'Request Sent',
    3: 'Rate Con Received',
}


def clean_value(value):
    return str(value).strip() if value is not None else ''


def int_value(value, default=0):
    try:
        return int(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def active_order_filter():
    return or_(Orders.Hstat < 2, Orders.Hstat.is_(None))


def format_date(value):
    return value.strftime('%Y-%m-%d') if value else ''


def active_orders_for_shipper(shipper):
    return (
        Orders.query
        .filter(active_order_filter())
        .filter(Orders.Shipper == clean_value(shipper))
        .order_by(Orders.Date3.desc(), Orders.Date.desc(), Orders.id.desc())
        .all()
    )


def active_job_summary(order):
    stage = int_value(getattr(order, 'RCneeded', 0))
    return {
        'id': order.id,
        'jo': clean_value(order.Jo),
        'container': clean_value(order.Container),
        'booking': clean_value(order.Booking) or clean_value(order.BOL),
        'delivery_date': format_date(order.Date3),
        'hstat': order.Hstat,
        'delivery_location': clean_value(order.Company2),
        'rc_stage': stage,
        'rc_label': RC_STAGE_LABELS.get(stage, f'Unknown ({stage})'),
        'eligible': stage in [0, 1],
    }


def order_rc_context(order_id):
    order = Orders.query.get(order_id)
    if order is None:
        return None
    shipper = clean_value(order.Shipper)
    if not shipper:
        return None
    orders = active_orders_for_shipper(shipper)
    return {
        'shipper': shipper,
        'selected_jo': clean_value(order.Jo),
        'selected_container': clean_value(order.Container),
        'selected_stage': int_value(getattr(order, 'RCneeded', 0)),
        'active_count': len(orders),
        'eligible_count': sum(1 for active_order in orders if int_value(getattr(active_order, 'RCneeded', 0)) in [0, 1]),
        'protected_count': sum(1 for active_order in orders if int_value(getattr(active_order, 'RCneeded', 0)) in [2, 3]),
        'jobs': [active_job_summary(active_order) for active_order in orders],
        'stage_labels': RC_STAGE_LABELS,
    }


def update_active_shipper_rc_needed(shipper, selected_stage):
    shipper = clean_value(shipper)
    if not shipper:
        return {'ok': False, 'error': 'Selected order does not have a shipper.', 'updated': 0, 'skipped': 0}
    try:
        selected_stage = int(selected_stage)
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'Rate con selection must be 0 or 1.', 'updated': 0, 'skipped': 0}
    if selected_stage not in [0, 1]:
        return {'ok': False, 'error': 'Rate con selection must be 0 or 1.', 'updated': 0, 'skipped': 0}

    orders = active_orders_for_shipper(shipper)
    if not orders:
        return {'ok': False, 'error': 'No active jobs were found for that shipper.', 'updated': 0, 'skipped': 0}

    updated = 0
    skipped = 0
    for order in orders:
        current_stage = int_value(getattr(order, 'RCneeded', 0))
        if current_stage in [2, 3]:
            skipped += 1
            continue
        if current_stage in [0, 1]:
            order.RCneeded = selected_stage
            updated += 1
    db.session.commit()
    return {'ok': True, 'error': '', 'updated': updated, 'skipped': skipped}
