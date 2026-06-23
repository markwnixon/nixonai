import datetime

from sqlalchemy import or_, text

from webapp import db
from webapp.dispatch_calendar import (
    clean_text,
    combine_date_time,
    ensure_dispatch_calendar_tables,
    filter_options as calendar_filter_options,
    format_date,
    parse_date,
    upsert_schedule,
)
from webapp.models import Drivers, Orders, Pins, Vehicles


KANBAN_COLUMNS = [
    ('new_orders', 'New Orders'),
    ('needs_review', 'Needs Review'),
    ('upcoming_deliveries', 'Upcoming Deliveries'),
    ('needs_pin', 'Needs PIN'),
    ('pin_ready', 'PIN Ready'),
    ('in_progress', 'In Progress'),
    ('delivered', 'Delivered'),
    ('invoice_ready', 'Invoice Ready'),
    ('completed', 'Completed'),
]

KANBAN_STATUS_LABELS = dict(KANBAN_COLUMNS)
KANBAN_STATUS_KEYS = {key for key, label in KANBAN_COLUMNS}
LEGACY_STATUS_MAP = {
    'ready_to_dispatch': 'pin_ready',
    'assigned': 'pin_ready',
}


def normalize_workflow_status(status):
    status = clean_text(status)
    return LEGACY_STATUS_MAP.get(status, status)


def ensure_dispatch_kanban_tables():
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS dispatch_kanban_state (
            id INT AUTO_INCREMENT PRIMARY KEY,
            OrderId INT NOT NULL UNIQUE,
            WorkflowStatus VARCHAR(45) NOT NULL,
            Notes TEXT,
            PinReference VARCHAR(100),
            BillingStatus VARCHAR(100),
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_dispatch_kanban_order (OrderId),
            INDEX idx_dispatch_kanban_status (WorkflowStatus)
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS dispatch_kanban_audit (
            id INT AUTO_INCREMENT PRIMARY KEY,
            OrderId INT NOT NULL,
            OldStatus VARCHAR(45),
            NewStatus VARCHAR(45),
            Username VARCHAR(45),
            Reason TEXT,
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_dispatch_kanban_audit_order (OrderId)
        )
    """))
    db.session.commit()


def state_row(order_id):
    ensure_dispatch_kanban_tables()
    return db.session.execute(
        text('SELECT * FROM dispatch_kanban_state WHERE OrderId = :order_id'),
        {'order_id': order_id},
    ).mappings().first()


def rows_by_order_id(table_name, order_ids):
    if not order_ids:
        return {}
    bind_names = [f'id_{idx}' for idx, _ in enumerate(order_ids)]
    placeholders = ', '.join([f':{name}' for name in bind_names])
    params = {name: order_id for name, order_id in zip(bind_names, order_ids)}
    rows = db.session.execute(
        text(f'SELECT * FROM {table_name} WHERE OrderId IN ({placeholders})'),
        params,
    ).mappings().all()
    return {row.get('OrderId'): row for row in rows}


def state_rows_for_orders(order_ids):
    ensure_dispatch_kanban_tables()
    return rows_by_order_id('dispatch_kanban_state', order_ids)


def schedule_rows_for_orders(order_ids):
    ensure_dispatch_calendar_tables()
    return rows_by_order_id('dispatch_calendar_schedule', order_ids)


def pin_lookup_for_orders(orders):
    containers = {clean_text(order.Container) for order in orders if clean_text(order.Container)}
    bookings = {clean_text(order.Booking) for order in orders if clean_text(order.Booking)}
    filters = []
    if containers:
        filters.extend([Pins.InCon.in_(containers), Pins.OutCon.in_(containers)])
    if bookings:
        filters.extend([Pins.InBook.in_(bookings), Pins.OutBook.in_(bookings)])
    if not filters:
        return {}
    lookup = {}
    pins = Pins.query.filter(or_(*filters)).order_by(Pins.Date.desc()).limit(5000).all()
    for pin in pins:
        for value in [pin.InCon, pin.OutCon]:
            key = ('container', clean_text(value))
            if key[1] and key not in lookup:
                lookup[key] = pin
        for value in [pin.InBook, pin.OutBook]:
            key = ('booking', clean_text(value))
            if key[1] and key not in lookup:
                lookup[key] = pin
    return lookup


def pin_from_lookup(order, pin_lookup):
    container = clean_text(order.Container)
    booking = clean_text(order.Booking)
    if container and ('container', container) in pin_lookup:
        return pin_lookup[('container', container)]
    if booking and ('booking', booking) in pin_lookup:
        return pin_lookup[('booking', booking)]
    return None


def pin_row_for_order(order):
    filters = []
    if order.Container:
        filters.extend([Pins.InCon == order.Container, Pins.OutCon == order.Container])
    if order.Booking:
        filters.extend([Pins.InBook == order.Booking, Pins.OutBook == order.Booking])
    if not filters:
        return None
    return Pins.query.filter(or_(*filters)).order_by(Pins.Date.desc()).first()


def pin_reference_for_order(order, state=None, pin=None):
    if state and clean_text(state.get('PinReference')):
        return clean_text(state.get('PinReference'))
    pin = pin or pin_row_for_order(order)
    if pin is None:
        return ''
    refs = [pin.InPin, pin.OutPin, pin.InBook, pin.OutBook]
    return next((clean_text(ref) for ref in refs if clean_text(ref)), '')


def pin_status_for_order(order, state=None, pin=None):
    if pin_reference_for_order(order, state, pin):
        return 'PIN ready'
    pin = pin or pin_row_for_order(order)
    if pin is not None:
        return 'PIN requested'
    return 'Missing PIN'


def has_pin(order, state=None, pin=None):
    return bool(pin_reference_for_order(order, state, pin))


def billing_status_for_order(order, state=None):
    if state and clean_text(state.get('BillingStatus')):
        return clean_text(state.get('BillingStatus'))
    istat = order.Istat if order.Istat is not None else 0
    try:
        istat = int(istat)
    except:
        istat = 0
    if istat >= 9:
        return 'Payment reconciled'
    if istat in [5, 8]:
        return 'Paid'
    if istat in [3, 7]:
        return 'Invoice emailed'
    if istat in [2, 6]:
        return 'Invoice ready'
    if istat == 1:
        return 'Invoice created'
    return 'Not invoiced'


def int_value(value, default=0):
    try:
        return int(value if value is not None else default)
    except:
        return default


def returned_not_invoiced(order):
    return int_value(order.Hstat) == 2 and int_value(order.Istat) < 1


def returned_or_delivered(order):
    return int_value(order.Hstat) >= 2


def order_date(value):
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return None


def kanban_scheduled_datetime(order, schedule=None):
    # Orders date mapping for Kanban:
    # - Date is pull date, or anticipated pull date if not pulled.
    # - Date2 is return date, or anticipated return date if still out.
    # - Date3/Time3 is the delivery appointment.
    # - dispatch_calendar_schedule is the Kanban/planning override when present.
    if schedule and schedule.get('ScheduledDate'):
        return combine_date_time(schedule.get('ScheduledDate'), schedule.get('ScheduledTime'))
    if order.Date3:
        return combine_date_time(order.Date3, order.Time3)
    return None


def kanban_delivery_location(order):
    return clean_text(order.Dropblock2) or clean_text(order.Company2) or clean_text(order.Delivery)


def kanban_pickup_terminal(order):
    return clean_text(order.Dropblock1) or clean_text(order.Company) or clean_text(order.Pickup)


def kanban_city_state_from_block(value):
    text_value = clean_text(value)
    if not text_value:
        return ''
    lines = [clean_text(line) for line in text_value.replace('\r', '\n').split('\n') if clean_text(line)]
    candidates = list(reversed(lines)) if lines else [text_value]
    for candidate in candidates:
        parts = [part.strip() for part in candidate.split(',') if part.strip()]
        if len(parts) >= 2:
            city = parts[-2]
            state = parts[-1].split()[0] if parts[-1].split() else ''
            if city and state and len(state) == 2:
                return f'{city}, {state}'
        tokens = candidate.split()
        if len(tokens) >= 3 and tokens[-1].isdigit() and len(tokens[-2]) == 2:
            return f'{" ".join(tokens[:-2])}, {tokens[-2]}'
        if len(tokens) >= 2 and len(tokens[-1]) == 2:
            return f'{" ".join(tokens[:-1])}, {tokens[-1]}'
    return ''


def kanban_delivery_city_state(order):
    return kanban_city_state_from_block(order.Dropblock2) or clean_text(order.Location3)


def apply_delivery_date_to_order(order, delivery_date, delivery_time=None):
    # When dispatch first sets a delivery appointment, start with same-day pull
    # and return assumptions. Dispatch can later move pull earlier or return later
    # after reviewing the calendar.
    delivery_dt = datetime.datetime.combine(delivery_date, datetime.time.min)
    order.Date3 = delivery_dt
    order.Time3 = clean_text(delivery_time)
    order.Date = delivery_dt
    order.Date2 = delivery_dt


def has_container_identity(order):
    return bool(clean_text(order.Container) or clean_text(order.Booking))


def is_upcoming_delivery(order):
    today = datetime.date.today()
    delivery_date = order_date(order.Date3)
    pull_date = order_date(order.Date)
    return bool((delivery_date and delivery_date > today) or (pull_date and pull_date > today))


def is_active_kanban_order(order, workflow_status):
    # Kanban is an operations board, so invoice/payment status should not hide
    # dispatch work. Completion is controlled by the Kanban workflow state and
    # obvious closed/cancelled order statuses.
    status_text = (order.Status or '').lower()
    if any(term in status_text for term in ['cancel', 'closed', 'void']):
        return False
    return workflow_status != 'completed'


def active_trucks_available():
    return Vehicles.query.filter((Vehicles.Active == 1) & (Vehicles.Type == 'Tractor')).count() > 0


def derived_workflow_status(order, state=None, pin=None):
    # Kanban mapping from existing Class8 fields:
    # - dispatch_kanban_state.WorkflowStatus wins once dispatch has touched the card.
    # - Orders.Hstat drives physical container progress: 0 unpulled, 1 pulled/in progress, 2 returned.
    # - Delivered means returned to port but not invoiced yet: Hstat == 2 and Istat < 1.
    # - Orders.Istat is shown as billing status only; it should not complete dispatch workflow.
    # - PIN status comes from Pins rows or the Kanban PinReference override.
    if state and clean_text(state.get('WorkflowStatus')):
        return normalize_workflow_status(state.get('WorkflowStatus'))

    hstat = int_value(order.Hstat)

    if returned_not_invoiced(order):
        return 'delivered'
    if returned_or_delivered(order):
        return 'completed'
    if hstat == 1:
        return 'in_progress'
    if clean_text(order.Driver):
        return 'pin_ready'
    if has_container_identity(order) and is_upcoming_delivery(order):
        return 'upcoming_deliveries'
    if has_pin(order, state, pin):
        return 'pin_ready'
    if has_container_identity(order):
        return 'needs_pin'
    return 'new_orders'


def order_matches_range(order, range_filter, schedule=None):
    if not range_filter or range_filter in ['all', 'all_active']:
        return True
    target = kanban_scheduled_datetime(order, schedule)
    if target is None:
        return False
    target_date = target.date()
    today = datetime.date.today()
    if range_filter == 'today':
        return target_date == today
    if range_filter == 'tomorrow':
        return target_date == today + datetime.timedelta(days=1)
    if range_filter == '7':
        return today <= target_date <= today + datetime.timedelta(days=7)
    return True


def filtered_orders(filters=None):
    filters = filters or {}
    query = Orders.query
    cutoff = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=30), datetime.time.min)
    query = query.filter(or_(Orders.Date3 >= cutoff, Orders.Date2 >= cutoff, Orders.Date >= cutoff))
    company = clean_text(filters.get('company'))
    if company and company.lower() not in ['all']:
        query = query.filter(Orders.Jo.startswith(company))
    driver = clean_text(filters.get('driver'))
    if driver:
        query = query.filter(Orders.Driver == driver)
    customer = clean_text(filters.get('customer'))
    if customer:
        query = query.filter(or_(Orders.Shipper == customer, Orders.Company == customer))
    terminal = clean_text(filters.get('terminal'))
    if terminal:
        query = query.filter(or_(Orders.Pickup.contains(terminal), Orders.Location.contains(terminal)))
    status_filter = clean_text(filters.get('status'))
    if status_filter and status_filter in KANBAN_STATUS_KEYS:
        pass
    elif status_filter:
        query = query.filter(Orders.Status.contains(status_filter))

    # The Kanban board is for current dispatch work. Older exceptions should be handled
    # deliberately elsewhere instead of making the live workflow board scan years of rows.
    orders = query.order_by(Orders.Date2.desc(), Orders.Date.desc()).limit(800).all()
    order_ids = [order.id for order in orders]
    state_map = state_rows_for_orders(order_ids)
    schedule_map = schedule_rows_for_orders(order_ids)
    pin_lookup = pin_lookup_for_orders(orders)
    output = []
    range_filter = clean_text(filters.get('range'))
    for order in orders:
        state = state_map.get(order.id)
        schedule = schedule_map.get(order.id)
        pin = pin_from_lookup(order, pin_lookup)
        workflow_status = derived_workflow_status(order, state, pin)
        if workflow_status == 'completed' and status_filter != 'completed':
            continue
        if status_filter in KANBAN_STATUS_KEYS and workflow_status != status_filter:
            continue
        if not is_active_kanban_order(order, workflow_status):
            continue
        if not order_matches_range(order, range_filter, schedule):
            continue
        output.append((order, state, workflow_status, schedule, pin))
    return output


def kanban_job_card(order, state=None, workflow_status=None, schedule=None, pin=None):
    workflow_status = workflow_status or derived_workflow_status(order, state, pin)
    planned = kanban_scheduled_datetime(order, schedule)
    pin_status = pin_status_for_order(order, state, pin)
    return {
        'id': order.id,
        'workflow_status': workflow_status,
        'workflow_label': KANBAN_STATUS_LABELS.get(workflow_status, workflow_status),
        'jo': order.Jo,
        'container': order.Container or '',
        'booking': order.Booking or '',
        'customer': order.Shipper or order.Company or '',
        'shipper': order.Shipper or '',
        'steamship_line': order.SSCO or order.Ship or '',
        'pickup_terminal': kanban_pickup_terminal(order),
        'delivery_location': kanban_delivery_location(order),
        'delivery_city_state': kanban_delivery_city_state(order),
        'required_delivery_date': format_date(order.Date3),
        'scheduled_delivery_date': planned.strftime('%Y-%m-%d') if planned else '',
        'scheduled_delivery_time': planned.strftime('%H:%M') if planned and planned.time() != datetime.time.min else '',
        'pull_date': format_date(order.Date),
        'return_date': format_date(order.Date2),
        'last_free_day': format_date(order.Date4),
        'pin_status': pin_status,
        'pin_reference': pin_reference_for_order(order, state, pin),
        'driver': order.Driver or '',
        'truck': order.Truck or '',
        'billing_status': billing_status_for_order(order, state),
        'order_status': order.Status or '',
        'notes': state.get('Notes') if state else '',
    }


def kanban_jobs(filters=None):
    ensure_dispatch_kanban_tables()
    jobs_by_status = {key: [] for key, label in KANBAN_COLUMNS}
    total_jobs = 0
    for order, state, workflow_status, schedule, pin in filtered_orders(filters):
        jobs_by_status.setdefault(workflow_status, []).append(kanban_job_card(order, state, workflow_status, schedule, pin))
        total_jobs += 1
    return {
        'total_jobs': total_jobs,
        'columns': [{'key': key, 'label': label, 'jobs': jobs_by_status.get(key, [])} for key, label in KANBAN_COLUMNS],
    }


def audit_status_change(order_id, old_status, new_status, username, reason=None):
    db.session.execute(
        text("""
            INSERT INTO dispatch_kanban_audit (OrderId, OldStatus, NewStatus, Username, Reason, CreatedAt)
            VALUES (:order_id, :old_status, :new_status, :username, :reason, :created_at)
        """),
        {
            'order_id': order_id,
            'old_status': old_status,
            'new_status': new_status,
            'username': username,
            'reason': reason,
            'created_at': datetime.datetime.utcnow(),
        },
    )


def validate_status_move(order, new_status, state=None, override_pin=False):
    new_status = normalize_workflow_status(new_status)
    if new_status not in KANBAN_STATUS_KEYS:
        return 'Unknown workflow status.'
    if new_status == 'pin_ready' and not has_pin(order, state) and not override_pin:
        return 'Moving to PIN Ready requires a PIN or explicit override.'
    if new_status == 'in_progress':
        if not clean_text(order.Driver):
            return 'Moving to In Progress requires an assigned driver.'
        if active_trucks_available() and not clean_text(order.Truck):
            return 'Moving to In Progress requires an assigned truck.'
    if new_status == 'invoice_ready' and not returned_or_delivered(order):
        return 'Moving to Invoice Ready requires delivered status.'
    return None


def upsert_state(order, workflow_status, username=None, notes=None, pin_reference=None, billing_status=None, reason=None):
    ensure_dispatch_kanban_tables()
    existing = state_row(order.id)
    old_status = derived_workflow_status(order, existing)
    now = datetime.datetime.utcnow()
    if existing:
        db.session.execute(
            text("""
                UPDATE dispatch_kanban_state
                SET WorkflowStatus = :workflow_status,
                    Notes = :notes,
                    PinReference = :pin_reference,
                    BillingStatus = :billing_status,
                    UpdatedAt = :updated_at
                WHERE OrderId = :order_id
            """),
            {
                'order_id': order.id,
                'workflow_status': workflow_status,
                'notes': notes if notes is not None else existing.get('Notes'),
                'pin_reference': pin_reference if pin_reference is not None else existing.get('PinReference'),
                'billing_status': billing_status if billing_status is not None else existing.get('BillingStatus'),
                'updated_at': now,
            },
        )
    else:
        db.session.execute(
            text("""
                INSERT INTO dispatch_kanban_state
                    (OrderId, WorkflowStatus, Notes, PinReference, BillingStatus, CreatedAt, UpdatedAt)
                VALUES
                    (:order_id, :workflow_status, :notes, :pin_reference, :billing_status, :created_at, :updated_at)
            """),
            {
                'order_id': order.id,
                'workflow_status': workflow_status,
                'notes': notes,
                'pin_reference': pin_reference,
                'billing_status': billing_status,
                'created_at': now,
                'updated_at': now,
            },
        )
    audit_status_change(order.id, old_status, workflow_status, username, reason)
    db.session.commit()


def move_job(order_id, new_status, username=None, override_pin=False, reason=None):
    new_status = normalize_workflow_status(new_status)
    order = Orders.query.get(order_id)
    if order is None:
        return {'ok': False, 'error': 'Order not found.'}, 404
    state = state_row(order.id)
    error = validate_status_move(order, new_status, state, override_pin=override_pin)
    if error:
        status = 409 if 'PIN Ready' in error else 400
        return {'ok': False, 'error': error, 'requires_override': status == 409}, status
    upsert_state(order, new_status, username=username, reason=reason)
    return {'ok': True, 'job': kanban_job_card(order, state_row(order.id), new_status)}, 200


def update_job(order_id, data, username=None):
    order = Orders.query.get(order_id)
    if order is None:
        return {'ok': False, 'error': 'Order not found.'}, 404
    state = state_row(order.id)
    workflow_status = normalize_workflow_status(data.get('workflow_status')) or derived_workflow_status(order, state)
    old_fields = {'Driver': order.Driver, 'Truck': order.Truck, 'Status': order.Status}

    order.Driver = clean_text(data.get('driver'))
    order.Truck = clean_text(data.get('truck'))
    order.Status = clean_text(data.get('order_status')) or order.Status
    order.UserMod = username
    db.session.commit()

    scheduled_date = parse_date(data.get('scheduled_delivery_date'))
    if scheduled_date:
        apply_delivery_date_to_order(order, scheduled_date, data.get('scheduled_delivery_time'))
        order.UserMod = username
        db.session.commit()
        upsert_schedule(
            order.id,
            scheduled_date,
            clean_text(data.get('scheduled_delivery_time')),
            notes=clean_text(data.get('notes')),
            username=username,
            action='kanban_update',
        )

    updated_state = state_row(order.id)
    error = validate_status_move(
        order,
        workflow_status,
        updated_state,
        override_pin=bool(data.get('override_pin')),
    )
    if error:
        return {'ok': False, 'error': error}, 400

    upsert_state(
        order,
        workflow_status,
        username=username,
        notes=clean_text(data.get('notes')),
        pin_reference=clean_text(data.get('pin_reference')),
        billing_status=clean_text(data.get('billing_status')),
        reason='modal update',
    )
    audit_status_change(order.id, 'order_fields', 'order_fields', username, str({
        'old': old_fields,
        'new': {'Driver': order.Driver, 'Truck': order.Truck, 'Status': order.Status},
    }))
    db.session.commit()
    return {'ok': True, 'job': kanban_job_card(order, state_row(order.id), workflow_status)}, 200


def kanban_options():
    options = calendar_filter_options()
    customer_rows = (
        db.session.query(Orders.Shipper, Orders.Company)
        .filter((Orders.Shipper.isnot(None)) | (Orders.Company.isnot(None)))
        .limit(2500)
        .all()
    )
    customers = set(options.get('customers', []))
    for shipper, company in customer_rows:
        if clean_text(shipper):
            customers.add(clean_text(shipper))
        elif clean_text(company):
            customers.add(clean_text(company))
    options['customers'] = sorted(customers)
    options['columns'] = [{'key': key, 'label': label} for key, label in KANBAN_COLUMNS]
    options['ranges'] = [
        {'key': 'today', 'label': 'Today'},
        {'key': 'tomorrow', 'label': 'Tomorrow'},
        {'key': '7', 'label': 'Next 7 Days'},
        {'key': 'all_active', 'label': 'Recent Active'},
    ]
    options['companies'] = ['K', 'J', 'N']
    return options
