import datetime
import os

from sqlalchemy import inspect, or_, text
from werkzeug.utils import secure_filename

from webapp import db
from webapp.CCC_system_setup import addpath, tpath
from webapp.dispatch_calendar import (
    clean_text,
    combine_date_time,
    ensure_dispatch_calendar_tables,
    filter_options as calendar_filter_options,
    format_date,
    parse_date,
    upsert_schedule,
)
from webapp.models import Drivers, Imports, Orders, Pins, Vehicles


KANBAN_COLUMNS = [
    ('new_orders', 'New Orders'),
    ('on_call', 'On Call'),
    ('upcoming_deliveries', 'Upcoming Deliveries'),
    ('port_today', 'Port Today'),
    ('drop_pick', 'Drop-Pick'),
    ('pin_assigned', 'PIN Assigned'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed Need Proof'),
]

KANBAN_STATUS_LABELS = dict(KANBAN_COLUMNS)
KANBAN_STATUS_KEYS = {key for key, label in KANBAN_COLUMNS}
LEGACY_STATUS_MAP = {
    'needs_review': 'on_call',
    'needs_pin': 'port_today',
    'pin_ready': 'pin_assigned',
    'ready_to_dispatch': 'pin_assigned',
    'assigned': 'pin_assigned',
    'delivered': 'in_progress',
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
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS dispatch_kanban_review_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            OrderId INT NOT NULL,
            ReviewDate DATE,
            ReviewType VARCHAR(45),
            Shipline VARCHAR(100),
            Ship VARCHAR(100),
            Voyage VARCHAR(100),
            ArrivalDate DATE,
            ERDDate DATE,
            CutoffDate DATE,
            LineStatus VARCHAR(100),
            CustomsStatus VARCHAR(100),
            OtherHolds VARCHAR(255),
            EquipmentSize VARCHAR(100),
            ReadyForDelivery VARCHAR(45),
            Location VARCHAR(100),
            LFDDate DATE,
            ECCESContainerType VARCHAR(100),
            ECCESChassis VARCHAR(100),
            ECCESAvailTerminal VARCHAR(100),
            ECCESGateIn VARCHAR(100),
            ECCESCBPExamComplete VARCHAR(100),
            ECCESCustomsRelease VARCHAR(100),
            ECCESFreightRelease VARCHAR(100),
            Notes TEXT,
            Username VARCHAR(45),
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_dispatch_kanban_review_order (OrderId),
            INDEX idx_dispatch_kanban_review_created (CreatedAt)
        )
    """))
    review_columns = {column['name'] for column in inspect(db.engine).get_columns('dispatch_kanban_review_log')}
    review_column_defs = {
        'ReviewDate': 'DATE',
        'Shipline': 'VARCHAR(100)',
        'Ship': 'VARCHAR(100)',
        'Voyage': 'VARCHAR(100)',
        'ArrivalDate': 'DATE',
        'ERDDate': 'DATE',
        'CutoffDate': 'DATE',
        'LineStatus': 'VARCHAR(100)',
        'CustomsStatus': 'VARCHAR(100)',
        'OtherHolds': 'VARCHAR(255)',
        'EquipmentSize': 'VARCHAR(100)',
        'ReadyForDelivery': 'VARCHAR(45)',
        'Location': 'VARCHAR(100)',
        'LFDDate': 'DATE',
        'ECCESContainerType': 'VARCHAR(100)',
        'ECCESChassis': 'VARCHAR(100)',
        'ECCESAvailTerminal': 'VARCHAR(100)',
        'ECCESGateIn': 'VARCHAR(100)',
        'ECCESCBPExamComplete': 'VARCHAR(100)',
        'ECCESCustomsRelease': 'VARCHAR(100)',
        'ECCESFreightRelease': 'VARCHAR(100)',
    }
    for column_name, column_def in review_column_defs.items():
        if column_name not in review_columns:
            db.session.execute(text(f'ALTER TABLE dispatch_kanban_review_log ADD COLUMN {column_name} {column_def}'))
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


def import_lookup_for_orders(orders):
    keys = set()
    for order in orders:
        for value in [order.Jo, order.BOL, order.Booking, order.Container]:
            value = clean_text(value)
            if value:
                keys.add(value)
    if not keys:
        return {}
    imports = Imports.query.filter(or_(
        Imports.Jo.in_(keys),
        Imports.BOL.in_(keys),
        Imports.Container.in_(keys),
    )).limit(5000).all()
    lookup = {}
    for import_row in imports:
        for key_name, value in [
            ('jo', import_row.Jo),
            ('bol', import_row.BOL),
            ('container', import_row.Container),
        ]:
            key = (key_name, clean_text(value))
            if key[1] and key not in lookup:
                lookup[key] = import_row
    return lookup


def import_from_lookup(order, import_lookup):
    for key in [
        ('jo', clean_text(order.Jo)),
        ('bol', clean_text(order.BOL) or clean_text(order.Booking)),
        ('container', clean_text(order.Container)),
    ]:
        if key[1] and key in import_lookup:
            return import_lookup[key]
    return None


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


def pin_is_for_today(pin, today=None):
    if pin is None:
        return False
    pin_date = order_date(getattr(pin, 'Date', None))
    return bool(pin_date and pin_date == (today or datetime.date.today()))


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


def is_import_order(order):
    return 'import' in clean_text(getattr(order, 'HaulType', '')).lower()


def is_drop_pick_order(order):
    haul_type = clean_text(getattr(order, 'HaulType', '')).lower()
    return 'dp' in haul_type or 'drop' in haul_type


def next_week_start(today=None):
    today = today or datetime.date.today()
    return today + datetime.timedelta(days=(7 - today.weekday()))


def week_end(today=None):
    today = today or datetime.date.today()
    return today + datetime.timedelta(days=(6 - today.weekday()))


def next_business_day(day):
    current = day + datetime.timedelta(days=1)
    while current.weekday() >= 5:
        current = current + datetime.timedelta(days=1)
    return current


def add_business_days(day, count):
    current = day
    for _ in range(count):
        current = next_business_day(current)
    return current


def pin_planning_cutoff(now=None):
    now = now or datetime.datetime.now()
    close_time = datetime.time(16, 30)
    if now.date().weekday() >= 5:
        return next_business_day(now.date())
    if now.time() >= close_time:
        return next_business_day(now.date())
    return now.date()


def upcoming_delivery_window_end(now=None):
    return add_business_days(pin_planning_cutoff(now), 5)


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


def confirmed_delivery(order, schedule=None):
    return bool(
        kanban_scheduled_datetime(order, schedule) and
        (clean_text(getattr(order, 'Delivery', '')) or clean_text(getattr(order, 'Time3', '')))
    )


def is_upcoming_delivery(order, schedule=None):
    target = kanban_scheduled_datetime(order, schedule)
    if not target:
        return False
    cutoff = pin_planning_cutoff()
    return cutoff < target.date() <= upcoming_delivery_window_end()


def is_new_future_import(order):
    return bool(is_import_order(order) and order_date(getattr(order, 'Date6', None)) and order_date(getattr(order, 'Date6', None)) >= next_week_start())


def has_exam_or_hold(order, import_row=None):
    hold_type = clean_text(getattr(order, 'HoldType', ''))
    return bool(hold_type and hold_type.strip().lower() not in ['', 'no hold', 'none', 'null'])


def is_ecces_hold(order):
    return clean_text(getattr(order, 'HoldType', '')).strip().lower() == 'ecces'


def scheduled_this_week(order, schedule=None):
    target = kanban_scheduled_datetime(order, schedule)
    if target is None:
        return False
    today = datetime.date.today()
    return today <= target.date() <= week_end(today)


def has_delivery_proof(order):
    proof = clean_text(getattr(order, 'Proof', ''))
    return bool(
        (proof and proof.lower() not in ['none required', 'no proof needed']) or
        clean_text(getattr(order, 'Proof2', '')) or
        clean_text(getattr(order, 'DrvProof', ''))
    )


def proof_none_required(order):
    return clean_text(getattr(order, 'Proof', '')).lower() in ['none required', 'no proof needed']


def proof_upload_allowed_for_status(workflow_status):
    return workflow_status in ['in_progress', 'completed']


def ready_to_invoice_documents(order):
    return has_delivery_proof(order) or proof_none_required(order)


def scheduled_for_today(order, schedule=None):
    target = kanban_scheduled_datetime(order, schedule)
    return bool(target and target.date() == datetime.date.today())


def delivery_qualifies_for_port_today(order, schedule=None):
    target = kanban_scheduled_datetime(order, schedule)
    return bool(target and target.date() <= pin_planning_cutoff() and not has_past_placeholder_delivery_date(order, schedule))


def planned_pull_qualifies_for_port_today(order):
    pull_date = order_date(getattr(order, 'Date', None))
    return bool(pull_date and pull_date == pin_planning_cutoff())


def port_today_only_for_planned_pull(order, schedule=None):
    return planned_pull_qualifies_for_port_today(order) and not delivery_qualifies_for_port_today(order, schedule)


def has_past_placeholder_delivery_date(order, schedule=None):
    target = kanban_scheduled_datetime(order, schedule)
    return bool(target and target.date() < datetime.date.today())


def is_active_kanban_order(order, workflow_status):
    # Kanban is an operations board, so invoice/payment status should not hide
    # dispatch work. Completion is controlled by the Kanban workflow state and
    # obvious closed/cancelled order statuses.
    status_text = (order.Status or '').lower()
    if any(term in status_text for term in ['cancel', 'closed', 'void']):
        return False
    if int_value(order.Hstat) >= 2 and ready_to_invoice_documents(order):
        return False
    return True


def active_trucks_available():
    return Vehicles.query.filter((Vehicles.Active == 1) & (Vehicles.Type == 'Tractor')).count() > 0


def derived_workflow_status(order, state=None, pin=None, schedule=None, import_row=None):
    # Kanban mapping from existing Class8 fields:
    # - Physical movement can override an older saved workflow state.
    # - Orders.HoldType is manually maintained; if set to a real hold value it
    #   routes unpulled planning work to On Call. Import line/customs fields do
    #   not change dispatch workflow status by themselves.
    # - Orders.Hstat drives physical container progress: 0 unpulled, 1 pulled/in progress, 2 returned.
    # - Delivered-but-not-returned jobs remain In Progress and show a Delivered alert.
    # - Completed Need Proof means the container has been returned to port, but
    #   proof is still missing. Returned jobs with proof/no-proof-needed leave
    #   the dispatch board.
    # - Orders.Istat is shown as billing status only; it should not complete dispatch workflow.
    # - PIN Assigned is only for a matching Pins row dated today, and physical progress wins.
    saved_status = normalize_workflow_status(state.get('WorkflowStatus')) if state and clean_text(state.get('WorkflowStatus')) else ''
    manual_hold = has_exam_or_hold(order, import_row)
    if saved_status == 'on_call' and not manual_hold:
        saved_status = ''
    if saved_status == 'port_today':
        if not delivery_qualifies_for_port_today(order, schedule) and not planned_pull_qualifies_for_port_today(order):
            saved_status = ''
    if (
        saved_status == 'upcoming_deliveries'
        and not is_upcoming_delivery(order, schedule)
        and not has_past_placeholder_delivery_date(order, schedule)
    ):
        saved_status = ''
    hstat = int_value(order.Hstat)

    if returned_or_delivered(order):
        return 'completed'
    if is_drop_pick_order(order):
        return 'drop_pick'
    if has_delivery_proof(order):
        return 'in_progress'
    if hstat == 1:
        return 'in_progress'
    if manual_hold:
        return 'on_call'
    if has_past_placeholder_delivery_date(order, schedule) and not planned_pull_qualifies_for_port_today(order):
        return 'upcoming_deliveries'
    if pin_is_for_today(pin):
        return 'pin_assigned'
    if delivery_qualifies_for_port_today(order, schedule) or planned_pull_qualifies_for_port_today(order):
        return 'port_today'
    if saved_status and saved_status != 'pin_assigned':
        return saved_status
    if confirmed_delivery(order, schedule):
        planned = kanban_scheduled_datetime(order, schedule)
        if planned and delivery_qualifies_for_port_today(order, schedule):
            return 'port_today'
        if is_upcoming_delivery(order, schedule):
            return 'upcoming_deliveries'
    if is_new_future_import(order):
        return 'new_orders'
    if has_container_identity(order):
        return 'new_orders'
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
    import_lookup = import_lookup_for_orders(orders)
    output = []
    status_updates = 0
    range_filter = clean_text(filters.get('range'))
    for order in orders:
        state = state_map.get(order.id)
        schedule = schedule_map.get(order.id)
        pin = pin_from_lookup(order, pin_lookup)
        import_row = import_from_lookup(order, import_lookup)
        workflow_status = derived_workflow_status(order, state, pin, schedule, import_row)
        if clean_text(getattr(order, 'DisStatus', '')) != workflow_status:
            order.DisStatus = workflow_status
            status_updates += 1
        if status_filter in KANBAN_STATUS_KEYS and workflow_status != status_filter:
            continue
        if not is_active_kanban_order(order, workflow_status):
            continue
        if not order_matches_range(order, range_filter, schedule):
            continue
        output.append((order, state, workflow_status, schedule, pin, import_row))
    if status_updates:
        db.session.commit()
    return output


def kanban_job_card(order, state=None, workflow_status=None, schedule=None, pin=None, import_row=None):
    workflow_status = workflow_status or derived_workflow_status(order, state, pin, schedule, import_row)
    planned = kanban_scheduled_datetime(order, schedule)
    pin_status = pin_status_for_order(order, state, pin)
    return {
        'id': order.id,
        'workflow_status': workflow_status,
        'workflow_label': KANBAN_STATUS_LABELS.get(workflow_status, workflow_status),
        'is_import': is_import_order(order),
        'is_export': not is_import_order(order),
        'jo': order.Jo,
        'container': order.Container or '',
        'container_type': order.Type or '',
        'booking': order.Booking or '',
        'release': clean_text(getattr(order, 'Release', '')),
        'customer': order.Shipper or order.Company or '',
        'shipper': order.Shipper or '',
        'steamship_line': order.SSCO or order.Ship or '',
        'shipline': order.SSCO or '',
        'ship': order.Ship or '',
        'voyage': order.Voyage or '',
        'pickup_terminal': kanban_pickup_terminal(order),
        'delivery_location': kanban_delivery_location(order),
        'delivery_city_state': kanban_delivery_city_state(order),
        'delivery_type': clean_text(getattr(order, 'Delivery', '')),
        'required_delivery_date': format_date(order.Date3),
        'scheduled_delivery_date': planned.strftime('%Y-%m-%d') if planned else '',
        'scheduled_delivery_time': planned.strftime('%H:%M') if planned and planned.time() != datetime.time.min else '',
        'pull_date': format_date(order.Date),
        'return_date': format_date(order.Date2),
        'erd_date': format_date(order.Date4),
        'last_free_day': format_date(order.Date5),
        'cutoff_date': format_date(order.Date5),
        'ship_arrive_date': format_date(order.Date6),
        'due_back_date': format_date(order.Date7),
        'placeholder_delivery_date_alert': has_past_placeholder_delivery_date(order, schedule),
        'placeholder_delivery_date_message': 'Update Placeholder Delivery Date' if has_past_placeholder_delivery_date(order, schedule) else '',
        'pull_today_alert': port_today_only_for_planned_pull(order, schedule),
        'pull_today_message': 'Pull Today' if port_today_only_for_planned_pull(order, schedule) else '',
        'hold_status': clean_text(getattr(order, 'HoldType', '')),
        'is_drop_pick': is_drop_pick_order(order),
        'drop_pick_pulled': is_drop_pick_order(order) and int_value(order.Hstat) >= 1,
        'pin_status': pin_status,
        'pin_reference': pin_reference_for_order(order, state, pin),
        'driver': order.Driver or '',
        'truck': order.Truck or '',
        'billing_status': billing_status_for_order(order, state),
        'proof': clean_text(getattr(order, 'Proof', '')),
        'proof2': clean_text(getattr(order, 'Proof2', '')),
        'driver_proof': clean_text(getattr(order, 'DrvProof', '')),
        'proof_none_required': proof_none_required(order),
        'has_delivery_proof': has_delivery_proof(order),
        'delivered_alert': has_delivery_proof(order) and not returned_or_delivered(order),
        'delivered_message': 'Delivered' if has_delivery_proof(order) and not returned_or_delivered(order) else '',
        'order_status': order.Status or '',
        'notes': state.get('Notes') if state else '',
    }


def kanban_jobs(filters=None):
    ensure_dispatch_kanban_tables()
    jobs_by_status = {key: [] for key, label in KANBAN_COLUMNS}
    total_jobs = 0
    for order, state, workflow_status, schedule, pin, import_row in filtered_orders(filters):
        jobs_by_status.setdefault(workflow_status, []).append(
            kanban_job_card(order, state, workflow_status, schedule, pin, import_row)
        )
        total_jobs += 1
    return {
        'total_jobs': total_jobs,
        'columns': [{'key': key, 'label': label, 'jobs': jobs_by_status.get(key, [])} for key, label in KANBAN_COLUMNS],
    }


def purge_incomplete_review_logs(order):
    if is_ecces_hold(order):
        completeness_condition = """
                  Shipline IS NULL OR TRIM(Shipline) = ''
                  OR ECCESContainerType IS NULL OR TRIM(ECCESContainerType) = ''
                  OR ECCESChassis IS NULL OR TRIM(ECCESChassis) = ''
                  OR ECCESAvailTerminal IS NULL OR TRIM(ECCESAvailTerminal) = ''
                  OR ECCESGateIn IS NULL OR TRIM(ECCESGateIn) = ''
                  OR ECCESCustomsRelease IS NULL OR TRIM(ECCESCustomsRelease) = ''
        """
    elif is_import_order(order):
        completeness_condition = """
                  ArrivalDate IS NULL
                  OR EquipmentSize IS NULL OR TRIM(EquipmentSize) = ''
                  OR Location IS NULL OR TRIM(Location) = ''
                  OR LineStatus IS NULL OR TRIM(LineStatus) = ''
                  OR CustomsStatus IS NULL OR TRIM(CustomsStatus) = ''
                  OR LFDDate IS NULL
        """
    else:
        completeness_condition = 'ERDDate IS NULL OR CutoffDate IS NULL'
    db.session.execute(
        text(f"""
            DELETE FROM dispatch_kanban_review_log
            WHERE OrderId = :order_id
              AND (
                  ReviewDate IS NULL
                  OR {completeness_condition}
                  OR (
                      :is_ecces = 0
                      AND (
                          Shipline IS NULL OR TRIM(Shipline) = ''
                          OR Ship IS NULL OR TRIM(Ship) = ''
                          OR Voyage IS NULL OR TRIM(Voyage) = ''
                      )
                  )
              )
        """),
        {'order_id': order.id, 'is_ecces': 1 if is_ecces_hold(order) else 0},
    )
    db.session.commit()


def review_logs_for_order(order_id):
    ensure_dispatch_kanban_tables()
    order = Orders.query.get(order_id)
    if order is None:
        return {'ok': False, 'error': 'Order not found.'}, 404
    purge_incomplete_review_logs(order)
    rows = db.session.execute(
        text("""
            SELECT id, ReviewDate, ReviewType, Shipline, Ship, Voyage, ArrivalDate, ERDDate, CutoffDate,
                   LineStatus, CustomsStatus, OtherHolds, EquipmentSize, ReadyForDelivery, Location, LFDDate,
                   ECCESContainerType, ECCESChassis, ECCESAvailTerminal, ECCESGateIn, ECCESCBPExamComplete,
                   ECCESCustomsRelease, ECCESFreightRelease,
                   Notes, Username, CreatedAt
            FROM dispatch_kanban_review_log
            WHERE OrderId = :order_id
            ORDER BY CreatedAt DESC, id DESC
            LIMIT 50
        """),
        {'order_id': order_id},
    ).mappings().all()
    return {
        'ok': True,
        'is_import': is_import_order(order),
        'is_ecces_hold': is_ecces_hold(order),
        'reviews': [
            {
                'id': row.get('id'),
                'review_date': format_date(row.get('ReviewDate')) or (
                    row.get('CreatedAt').strftime('%Y-%m-%d') if row.get('CreatedAt') else ''
                ),
                'review_type': clean_text(row.get('ReviewType')),
                'shipline': clean_text(row.get('Shipline')),
                'ship': clean_text(row.get('Ship')),
                'voyage': clean_text(row.get('Voyage')),
                'arrival_date': format_date(row.get('ArrivalDate')),
                'erd_date': format_date(row.get('ERDDate')),
                'cutoff_date': format_date(row.get('CutoffDate')),
                'line_status': clean_text(row.get('LineStatus')),
                'customs_status': clean_text(row.get('CustomsStatus')),
                'other_holds': clean_text(row.get('OtherHolds')),
                'equipment_size': clean_text(row.get('EquipmentSize')),
                'ready_for_delivery': clean_text(row.get('ReadyForDelivery')),
                'location': clean_text(row.get('Location')),
                'lfd_date': format_date(row.get('LFDDate')) or format_date(row.get('CutoffDate')),
                'ecces_container_type': clean_text(row.get('ECCESContainerType')),
                'ecces_chassis': clean_text(row.get('ECCESChassis')),
                'ecces_avail_terminal': clean_text(row.get('ECCESAvailTerminal')),
                'ecces_gate_in': clean_text(row.get('ECCESGateIn')),
                'ecces_cbp_exam_complete': clean_text(row.get('ECCESCBPExamComplete')),
                'ecces_customs_release': clean_text(row.get('ECCESCustomsRelease')),
                'ecces_freight_release': clean_text(row.get('ECCESFreightRelease')),
                'notes': clean_text(row.get('Notes')),
                'username': clean_text(row.get('Username')),
                'created_at': row.get('CreatedAt').strftime('%Y-%m-%d %H:%M') if row.get('CreatedAt') else '',
            }
            for row in rows
        ],
    }, 200


def log_review(order_id, data, username=None):
    ensure_dispatch_kanban_tables()
    order = Orders.query.get(order_id)
    if order is None:
        return {'ok': False, 'error': 'Order not found.'}, 404
    notes = clean_text(data.get('notes'))
    review_type = clean_text(data.get('review_type')) or 'Daily Review'
    review_date = parse_date(data.get('review_date')) or datetime.date.today()
    if not notes:
        return {'ok': False, 'error': 'Review notes are required.'}, 400
    import_row = import_from_lookup(order, import_lookup_for_orders([order])) if is_import_order(order) else None
    import_lfd = parse_date(clean_text(import_row.LFD)) if import_row else None
    db.session.execute(
        text("""
            INSERT INTO dispatch_kanban_review_log
                (OrderId, ReviewDate, ReviewType, Shipline, Ship, Voyage, ArrivalDate, ERDDate, CutoffDate,
                 LineStatus, CustomsStatus, OtherHolds, EquipmentSize, ReadyForDelivery, Location, LFDDate, Notes, Username,
                 CreatedAt)
            VALUES
                (:order_id, :review_date, :review_type, :shipline, :ship, :voyage, :arrival_date, :erd_date,
                 :cutoff_date, :line_status, :customs_status, :other_holds, :equipment_size, :ready_for_delivery,
                 :location, :lfd_date, :notes, :username, :created_at)
        """),
        {
            'order_id': order_id,
            'review_date': review_date,
            'review_type': review_type,
            'shipline': clean_text(order.SSCO),
            'ship': clean_text(order.Ship) or (clean_text(import_row.Vessel) if import_row else ''),
            'voyage': clean_text(order.Voyage) or (clean_text(import_row.Voyage) if import_row else ''),
            'arrival_date': order_date(order.Date6),
            'erd_date': order_date(order.Date4) if not is_import_order(order) else None,
            'cutoff_date': order_date(order.Date5) if not is_import_order(order) else None,
            'line_status': clean_text(import_row.LineStatus) if import_row else '',
            'customs_status': clean_text(import_row.CustomsStatus) if import_row else '',
            'other_holds': clean_text(import_row.OtherHolds) if import_row else '',
            'equipment_size': clean_text(import_row.Size) if import_row else clean_text(order.Type),
            'ready_for_delivery': clean_text(import_row.Ready) if import_row else '',
            'location': clean_text(import_row.Location) if import_row else clean_text(order.Location3),
            'lfd_date': import_lfd or order_date(order.Date5) if is_import_order(order) else None,
            'notes': notes,
            'username': username or 'dispatch',
            'created_at': datetime.datetime.utcnow(),
        },
    )
    db.session.commit()
    return review_logs_for_order(order_id)


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
    if new_status == 'pin_assigned' and not has_pin(order, state) and not override_pin:
        return 'Moving to PIN Assigned requires a PIN or explicit override.'
    if new_status == 'in_progress':
        if not clean_text(order.Driver):
            return 'Moving to In Progress requires an assigned driver.'
        if active_trucks_available() and not clean_text(order.Truck):
            return 'Moving to In Progress requires an assigned truck.'
    if new_status == 'completed':
        if not returned_or_delivered(order):
            return 'Moving to Completed Need Proof requires the container to be returned.'
        if ready_to_invoice_documents(order):
            return 'Returned jobs with proof, or No Proof Needed, are excluded from the Dispatch Kanban.'
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
        status = 409 if 'PIN Assigned' in error else 400
        return {'ok': False, 'error': error, 'requires_override': status == 409}, status
    upsert_state(order, new_status, username=username, reason=reason)
    return {'ok': True, 'job': kanban_job_card(order, state_row(order.id), new_status)}, 200


def update_job(order_id, data, username=None):
    order = Orders.query.get(order_id)
    if order is None:
        return {'ok': False, 'error': 'Order not found.'}, 404
    state = state_row(order.id)
    workflow_status = normalize_workflow_status(data.get('workflow_status')) or derived_workflow_status(order, state)
    old_fields = {
        'Driver': order.Driver,
        'Truck': order.Truck,
        'Status': order.Status,
        'Proof': order.Proof,
        'HoldType': clean_text(getattr(order, 'HoldType', '')),
        'Delivery': clean_text(getattr(order, 'Delivery', '')),
        'Date': format_date(order.Date),
    }

    order.HoldType = clean_text(data.get('hold_type'))
    order.Delivery = clean_text(data.get('delivery_type'))
    order.Driver = clean_text(data.get('driver'))
    order.Truck = clean_text(data.get('truck'))
    order.Status = clean_text(data.get('order_status')) or order.Status
    if bool(data.get('no_proof_needed')):
        order.Proof = 'No Proof Needed'
    elif proof_none_required(order):
        order.Proof = None
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

    planned_pull_date = parse_date(data.get('planned_pull_date'))
    if planned_pull_date:
        order.Date = datetime.datetime.combine(planned_pull_date, datetime.time.min)
        order.UserMod = username
        db.session.commit()

    updated_state = state_row(order.id)
    error = validate_status_move(
        order,
        workflow_status,
        updated_state,
        override_pin=bool(data.get('override_pin')),
    )
    resolved_completed_need_proof = (
        workflow_status == 'completed'
        and returned_or_delivered(order)
        and ready_to_invoice_documents(order)
    )
    if error and not resolved_completed_need_proof:
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
        'new': {
            'Driver': order.Driver,
            'Truck': order.Truck,
            'Status': order.Status,
            'Proof': order.Proof,
            'HoldType': clean_text(getattr(order, 'HoldType', '')),
            'Delivery': clean_text(getattr(order, 'Delivery', '')),
            'Date': format_date(order.Date),
        },
    }))
    db.session.commit()
    return {'ok': True, 'job': kanban_job_card(order, state_row(order.id), workflow_status)}, 200


def upload_proof(order_id, file_storage, username=None):
    order = Orders.query.get(order_id)
    if order is None:
        return {'ok': False, 'error': 'Order not found.'}, 404
    state = state_row(order.id)
    workflow_status = derived_workflow_status(order, state)
    if not proof_upload_allowed_for_status(workflow_status):
        return {'ok': False, 'error': 'Proof uploads are only available for In Progress or Completed Need Proof jobs.'}, 400
    if has_delivery_proof(order) or proof_none_required(order):
        return {'ok': False, 'error': 'This job already has proof or is marked No Proof Needed.'}, 400
    if file_storage is None or not clean_text(getattr(file_storage, 'filename', '')):
        return {'ok': False, 'error': 'Select a proof PDF to upload.'}, 400

    original_name = clean_text(file_storage.filename)
    _, extension = os.path.splitext(original_name)
    if extension.lower() != '.pdf':
        return {'ok': False, 'error': 'Proof upload must be a PDF file.'}, 400

    try:
        old_cache = int(getattr(order, 'Pcache', None) or 0)
    except (TypeError, ValueError):
        old_cache = 0
    new_cache = old_cache + 1
    job_key = clean_text(getattr(order, 'Jo', '')) or clean_text(getattr(order, 'Container', '')) or f'Order_{order.id}'
    safe_job_key = secure_filename(job_key) or f'Order_{order.id}'
    filename = f'Proof_Jo_{safe_job_key}_c{new_cache}.pdf'
    output_path = addpath(tpath('Orders-Proof', filename))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    file_storage.save(output_path)

    order.Proof = filename
    order.Pcache = new_cache
    order.UserMod = username
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
    options['hold_types'] = ['', 'ECCES', 'Line Hold', 'Custom Hold', 'Other Hold', 'Line and Customs Hold']
    options['delivery_types'] = ['Hard Time', 'Soft Time', 'Day Window', 'Upon Notice', 'Placeholder']
    options['ranges'] = [
        {'key': 'today', 'label': 'Today'},
        {'key': 'tomorrow', 'label': 'Tomorrow'},
        {'key': '7', 'label': 'Next 7 Days'},
        {'key': 'all_active', 'label': 'Recent Active'},
    ]
    return options
