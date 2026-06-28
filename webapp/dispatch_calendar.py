import datetime

from sqlalchemy import or_, text

from webapp import db
from webapp.CCC_system_setup import scac
from webapp.models import Drivers, Drops, Orders, People, Pins, PortClosed, Vehicles


DATE_FORMAT = '%Y-%m-%d'


def ensure_dispatch_calendar_tables():
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS dispatch_calendar_schedule (
            id INT AUTO_INCREMENT PRIMARY KEY,
            OrderId INT NOT NULL UNIQUE,
            ScheduledDate DATE,
            ScheduledTime VARCHAR(20),
            Notes TEXT,
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_dispatch_calendar_order (OrderId),
            INDEX idx_dispatch_calendar_date (ScheduledDate)
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS dispatch_calendar_audit (
            id INT AUTO_INCREMENT PRIMARY KEY,
            OrderId INT NOT NULL,
            Username VARCHAR(45),
            Action VARCHAR(45),
            OldValue TEXT,
            NewValue TEXT,
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_dispatch_calendar_audit_order (OrderId)
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS dispatch_calendar_notes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            NoteDate DATE NOT NULL,
            NoteType VARCHAR(45) NOT NULL,
            Driver VARCHAR(200),
            Port VARCHAR(100),
            CloseTime VARCHAR(20),
            Notes TEXT,
            CreatedBy VARCHAR(45),
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_dispatch_calendar_notes_date (NoteDate),
            INDEX idx_dispatch_calendar_notes_type (NoteType)
        )
    """))
    db.session.commit()


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value[:10], DATE_FORMAT).date()
    except:
        return None


def parse_datetime(value):
    if not value:
        return None
    try:
        normalized = value.replace('Z', '+00:00')
        return datetime.datetime.fromisoformat(normalized).replace(tzinfo=None)
    except:
        date_value = parse_date(value)
        if date_value:
            return datetime.datetime.combine(date_value, datetime.time.min)
    return None


def date_to_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min)
    return None


def format_date(value):
    value = date_to_datetime(value)
    return value.strftime(DATE_FORMAT) if value else ''


def combine_date_time(date_value, time_value):
    base = date_to_datetime(date_value)
    if base is None:
        return None
    clean_time = (time_value or '').strip()
    for fmt in ['%H:%M', '%I:%M %p', '%I:%M%p', '%H%M']:
        try:
            parsed = datetime.datetime.strptime(clean_time.upper(), fmt).time()
            return datetime.datetime.combine(base.date(), parsed)
        except:
            pass
    return base


def clean_text(value):
    return (value or '').strip()


def is_terminal_location(value):
    text_value = clean_text(value).lower()
    terminal_terms = ['seagirt', 'marine terminal', 'terminal', 'port of baltimore']
    return any(term in text_value for term in terminal_terms)


def city_state_text(value):
    text_value = clean_text(value)
    if not text_value:
        return ''
    lines = [clean_text(line) for line in text_value.replace('\r', '\n').split('\n') if clean_text(line)]
    if lines:
        text_value = lines[-1]
    parts = [part.strip() for part in text_value.split(',') if part.strip()]
    if len(parts) >= 2:
        city = parts[-2]
        state_zip = parts[-1].split()
        state = state_zip[0] if state_zip else ''
        return f'{city}, {state}' if state else city
    tokens = text_value.split()
    if len(tokens) >= 2 and len(tokens[-1]) == 2:
        return f'{" ".join(tokens[:-1])}, {tokens[-1]}'
    if len(tokens) >= 3 and tokens[-1].isdigit() and len(tokens[-2]) == 2:
        return f'{" ".join(tokens[:-2])}, {tokens[-2]}'
    return text_value


def order_company_code(order):
    return (order.Jo or '')[:1]


def is_active_order(order):
    status_text = (order.Status or '').lower()
    if any(term in status_text for term in ['cancel', 'closed', 'complete', 'void']):
        return False
    if order.Istat is not None:
        try:
            return int(order.Istat) < 4
        except:
            pass
    return True


def is_calendar_visible_order(order, filters=None):
    filters = filters or {}
    range_filter = clean_text(filters.get('range')) or 'calendar'
    if range_filter != 'calendar':
        return is_active_order(order)
    status_text = (order.Status or '').lower()
    return not any(term in status_text for term in ['cancel', 'void'])


def invoice_status_class(order):
    try:
        istat = int(order.Istat or 0)
    except:
        istat = 0
    if istat >= 5:
        return 'dispatch-paid'
    if istat >= 1:
        return 'dispatch-invoiced'
    return ''


def schedule_row(order_id):
    ensure_dispatch_calendar_tables()
    return db.session.execute(
        text('SELECT * FROM dispatch_calendar_schedule WHERE OrderId = :order_id'),
        {'order_id': order_id},
    ).mappings().first()


def scheduled_datetime(order, schedule=None):
    # Date mapping:
    # 1. dispatch_calendar_schedule.ScheduledDate/Time is the planning override used by this calendar.
    # 2. Orders.Date3/Time3 is the delivery date/time set on the order.
    if schedule and schedule.get('ScheduledDate'):
        return combine_date_time(schedule.get('ScheduledDate'), schedule.get('ScheduledTime'))
    if order.Date3:
        return combine_date_time(order.Date3, order.Time3)
    return None


def is_export_order(order):
    text_bits = [
        order.HaulType,
        order.Type,
        order.Booking,
        order.BOL,
    ]
    text_value = ' '.join([clean_text(value).lower() for value in text_bits if clean_text(value)])
    return 'export' in text_value or 'exp' in text_value


def is_import_order(order):
    return 'import' in clean_text(order.HaulType).lower()


def is_drop_pick_order(order):
    haul_type = clean_text(order.HaulType).lower()
    return 'dp' in haul_type or 'drop' in haul_type


def add_business_days(start_date, days):
    if start_date is None:
        return None
    current = start_date
    added = 0
    while added < days:
        current = current + datetime.timedelta(days=1)
        if current.weekday() >= 5:
            continue
        day_start = datetime.datetime.combine(current, datetime.time.min)
        day_end = day_start + datetime.timedelta(days=1)
        if PortClosed.query.filter((PortClosed.Date >= day_start) & (PortClosed.Date < day_end)).first() is not None:
            continue
        added += 1
    return current


def first_available_label(order):
    return 'Earliest Return' if is_export_order(order) else 'First Available'


def port_deadline_label(order):
    return 'Cutoff Date' if is_export_order(order) else 'Last Free Day'


def export_calendar_date_line(order, hstat):
    erd = format_date(order.Date4)
    cutoff = format_date(order.Date5)
    due_back = format_date(order.Date7)
    cutoff_date = date_to_datetime(order.Date5)
    due_back_date = date_to_datetime(order.Date7)
    due_back_is_earlier = bool(
        cutoff_date is not None and
        due_back_date is not None and
        due_back_date.date() < cutoff_date.date()
    )

    if hstat >= 2:
        parts = []
        if due_back:
            parts.append(f'Due Back {due_back}')
        if cutoff:
            parts.append(f'Cutoff {cutoff}')
        return ' | '.join(parts)

    if hstat >= 1 and due_back_is_earlier:
        parts = []
        if due_back:
            parts.append(f'Due Back {due_back}')
        if cutoff:
            parts.append(f'Cutoff {cutoff}')
        return ' | '.join(parts)

    parts = []
    if erd:
        parts.append(f'ERD {erd}')
    if cutoff:
        parts.append(f'Cutoff {cutoff}')
    return ' | '.join(parts)


def pin_status_for_order(order):
    if not order.Container and not order.Booking:
        return ''
    query = Pins.query
    filters = []
    if order.Container:
        filters.append(Pins.InCon == order.Container)
        filters.append(Pins.OutCon == order.Container)
    if order.Booking:
        filters.append(Pins.InBook == order.Booking)
        filters.append(Pins.OutBook == order.Booking)
    if not filters:
        return ''
    pin = query.filter(or_(*filters)).order_by(Pins.Date.desc()).first()
    if pin is None:
        return ''
    if pin.Active in [1, '1', True]:
        return 'PIN active'
    return 'PIN recorded'


def order_delivery_location(order):
    name = clean_text(order.Company2) or clean_text(order.Delivery)
    city = clean_text(order.Location3)
    if name and city and city.lower() not in name.lower():
        return f'{name} - {city}'
    if name:
        return name
    if city:
        return city
    return clean_text(order.Delivery) or clean_text(order.Location)


def order_delivery_city_state(order):
    drop = None
    if order.Lid:
        drop = Drops.query.get(order.Lid)
    if drop is None and order.Company2:
        drop = Drops.query.filter(Drops.Entity == order.Company2).first()
    if drop is not None:
        for value in [drop.Addr2, drop.Addr1]:
            parsed = city_state_text(value)
            if parsed and not is_terminal_location(parsed):
                return parsed
    for value in [order.Location3, order.Delivery, order.Dropblock2, order.Location]:
        parsed = city_state_text(value)
        if parsed and not is_terminal_location(parsed):
            return parsed
    return ''


def order_city(order):
    candidates = [order.Location3, order.Company2, order.Delivery, order.Location]
    for candidate in candidates:
        text_value = clean_text(candidate)
        if text_value:
            return text_value
    return ''


def calendar_compact_customer(order):
    customer_names = [clean_text(order.Shipper), clean_text(order.Company)]
    if any('global business' in name.lower() for name in customer_names if name):
        return True
    customer = None
    for name in customer_names:
        if not name:
            continue
        customer = People.query.filter(People.Company == name).first()
        if customer is not None:
            break
    if customer is None:
        return False
    flag_text = ' '.join([
        clean_text(customer.Temp1),
        clean_text(customer.Temp2),
        clean_text(customer.Source),
    ]).lower()
    return any(flag in flag_text for flag in [
        'calendar_compact',
        'compact_calendar',
        'calendar_no_city',
        'no_city_calendar',
    ])


def order_to_event(order, schedule=None):
    start = scheduled_datetime(order, schedule)
    if start is None:
        return None
    port_deadline = date_to_datetime(order.Date5)
    due_back = date_to_datetime(order.Date7)
    pin_status = pin_status_for_order(order)
    delivery_city_state = order_delivery_city_state(order)
    container_label = clean_text(order.Container) or clean_text(order.Booking) or order.Jo
    compact_calendar = calendar_compact_customer(order)
    shipper_label = clean_text(order.Shipper) or clean_text(order.Company)
    location_bits = []
    if delivery_city_state and not compact_calendar:
        location_bits.append(delivery_city_state)
    if order.Time3 and not compact_calendar:
        location_bits.append(f'Appt {order.Time3}')
    calendar_title_line = ' | '.join([part for part in [
        container_label,
        shipper_label,
        ' '.join(location_bits),
    ] if part])
    calendar_appointment_line = ' | '.join([part for part in [
        container_label,
        delivery_city_state if not compact_calendar else '',
        f'Appt {order.Time3}' if order.Time3 else '',
    ] if part])
    hstat = order.Hstat if order.Hstat is not None else 0
    try:
        hstat = int(hstat)
    except:
        hstat = 0
    if hstat >= 2:
        pull_status = 'returned'
        event_class = ['dispatch-event', 'dispatch-returned']
    elif hstat == 1:
        pull_status = 'pulled'
        event_class = ['dispatch-event', 'dispatch-pulled']
    else:
        pull_status = 'unpulled'
        event_class = ['dispatch-event', 'dispatch-unpulled']
    split_export_booking = bool(
        is_export_order(order) and
        clean_text(order.BOL) and
        clean_text(order.BOL) != clean_text(order.Booking)
    )
    if hstat >= 2 and split_export_booking:
        event_class.append('dispatch-returned-split-booking')
    invoice_class = invoice_status_class(order)
    if invoice_class:
        event_class.append(invoice_class)

    today = datetime.date.today()
    if hstat >= 1 and hstat < 2 and due_back:
        days_to_due_back = (due_back.date() - today).days
        if days_to_due_back < 0:
            event_class.append('dispatch-due-back-past')
        elif days_to_due_back <= 2:
            event_class.append('dispatch-due-back-near')
    elif hstat < 1 and port_deadline:
        days_to_deadline = (port_deadline.date() - today).days
        if days_to_deadline < 0:
            event_class.append('dispatch-lfd-past')
        elif days_to_deadline <= 2:
            event_class.append('dispatch-lfd-near')

    deadline_label = 'Due Back' if hstat >= 1 else port_deadline_label(order)
    deadline_date = format_date(order.Date7 if hstat >= 1 else order.Date5)
    calendar_date_line = export_calendar_date_line(order, hstat) if is_export_order(order) else (
        f'{deadline_label} {deadline_date}' if deadline_date else ''
    )

    return {
        'id': str(order.id),
        'title': calendar_title_line,
        'start': start.isoformat(),
        'allDay': start.time() == datetime.time.min,
        'classNames': event_class,
        'extendedProps': {
            'jo': order.Jo,
            'company_code': order_company_code(order),
            'container': order.Container or '',
            'booking': order.Booking or '',
            'in_booking': order.BOL or '',
            'booking_display_mode': 'split' if split_export_booking else 'single',
            'customer': order.Company or '',
            'shipper': order.Shipper or '',
            'calendar_title_line': calendar_title_line,
            'calendar_appointment_line': calendar_appointment_line,
            'calendar_compact': compact_calendar,
            'delivery': order.Delivery or '',
            'delivery_location': order_delivery_location(order),
            'delivery_city_state': delivery_city_state,
            'city': order_city(order),
            'driver': order.Driver or '',
            'truck': order.Truck or '',
            'appointment_time': order.Time3 or '',
            'status': order.Status or '',
            'invoice_status': order.Istat or 0,
            'pull_status': pull_status,
            'haul_type': order.HaulType or '',
            'is_import': is_import_order(order),
            'is_export': is_export_order(order),
            'is_drop_pick': is_drop_pick_order(order),
            'pull_date_label': 'Pulled Date' if hstat >= 1 else 'Anticipated Pull',
            'pull_date': format_date(order.Date),
            'return_date_label': 'Returned Date' if hstat >= 2 else 'Anticipated Return',
            'return_date': format_date(order.Date2),
            'delivery_date_label': 'Delivery Date',
            'delivery_date': format_date(order.Date3),
            'first_available_label': first_available_label(order),
            'first_available_date': format_date(order.Date4),
            'port_deadline_label': port_deadline_label(order),
            'port_deadline_date': format_date(order.Date5),
            'last_free_day': format_date(order.Date5),
            'ship_arrive_date': format_date(order.Date6),
            'due_back_date': format_date(order.Date7),
            'secondary_action_date': format_date(order.Date8),
            'deadline_label': deadline_label,
            'deadline_date': deadline_date,
            'calendar_date_line': calendar_date_line,
            'pin_status': pin_status,
            'notes': schedule.get('Notes') if schedule else '',
            'scheduled_date': start.strftime(DATE_FORMAT),
            'scheduled_time': start.strftime('%H:%M') if start.time() != datetime.time.min else '',
        },
    }


def active_orders_query(start=None, end=None, filters=None):
    filters = filters or {}
    query = Orders.query
    driver = clean_text(filters.get('driver'))
    if driver:
        query = query.filter(Orders.Driver == driver)
    customer = clean_text(filters.get('customer'))
    if customer:
        query = query.filter(Orders.Company == customer)
    status = clean_text(filters.get('status'))
    if status:
        query = query.filter(Orders.Status.contains(status))
    terminal = clean_text(filters.get('terminal'))
    if terminal:
        query = query.filter(or_(Orders.Pickup.contains(terminal), Orders.Location.contains(terminal)))
    search = clean_text(filters.get('search'))
    if search:
        query = query.filter(or_(
            Orders.Container.contains(search),
            Orders.Booking.contains(search),
            Orders.Jo.contains(search),
            Orders.BOL.contains(search),
        ))
    start_dt = datetime.datetime.combine(start, datetime.time.min) if isinstance(start, datetime.date) else start
    end_dt = datetime.datetime.combine(end + datetime.timedelta(days=1), datetime.time.min) if isinstance(end, datetime.date) else end
    scheduled_order_ids = []
    if start or end:
        schedule_query = text("""
            SELECT OrderId
            FROM dispatch_calendar_schedule
            WHERE (:start_date IS NULL OR ScheduledDate >= :start_date)
              AND (:end_date IS NULL OR ScheduledDate <= :end_date)
        """)
        scheduled_order_ids = [
            row.get('OrderId') for row in db.session.execute(schedule_query, {
                'start_date': start,
                'end_date': end,
            }).mappings().all()
        ]
    if start_dt:
        query = query.filter(or_(
            Orders.Date3 >= start_dt,
            Orders.id.in_(scheduled_order_ids) if scheduled_order_ids else False,
        ))
    if end_dt:
        query = query.filter(or_(
            Orders.Date3 < end_dt,
            Orders.id.in_(scheduled_order_ids) if scheduled_order_ids else False,
        ))
    return query


def filtered_orders(start=None, end=None, filters=None):
    orders = active_orders_query(start, end, filters).order_by(Orders.Date3.asc()).limit(2000).all()
    return [order for order in orders if is_calendar_visible_order(order, filters)]


def calendar_events(start=None, end=None, filters=None):
    ensure_dispatch_calendar_tables()
    orders = filtered_orders(start, end, filters)
    events = []
    for order in orders:
        event = order_to_event(order, schedule_row(order.id))
        if event is not None:
            event_date = parse_date(event.get('start', '')[:10])
            if start and event_date and event_date < start:
                continue
            if end and event_date and event_date > end:
                continue
            events.append(event)
    events.extend(port_closure_events(start, end))
    events.extend(calendar_note_events(start, end))
    return events


def port_closures(start=None, end=None):
    query = PortClosed.query
    if start:
        query = query.filter(PortClosed.Date >= start)
    if end:
        query = query.filter(PortClosed.Date <= end)
    return query.order_by(PortClosed.Date.asc(), PortClosed.id.asc()).all()


def port_closure_events(start=None, end=None):
    events = []
    for closure in port_closures(start, end):
        events.append({
            'id': f'port-closed-{closure.id}',
            'title': f"Port closed: {closure.Reason or 'Port closed'}",
            'start': format_date(closure.Date),
            'allDay': True,
            'editable': False,
            'classNames': ['dispatch-special-note', 'dispatch-note-port_closed', 'dispatch-port-closure'],
            'extendedProps': {
                'is_port_closure': True,
                'closure_id': closure.id,
                'note_type': 'port_closed',
                'port': 'Port',
                'notes': closure.Reason or '',
                'note_date': format_date(closure.Date),
            },
        })
    return events


def note_label(note):
    note_type = note.get('NoteType') or ''
    if note_type == 'driver_off':
        return f"Driver off: {note.get('Driver') or 'Unassigned'}"
    if note_type == 'port_closed':
        return f"Port closed: {note.get('Port') or 'Port'}"
    if note_type == 'port_early_close':
        time_text = f" at {note.get('CloseTime')}" if note.get('CloseTime') else ''
        return f"Port closes early{time_text}: {note.get('Port') or 'Port'}"
    return 'Dispatch note'


def calendar_note_events(start=None, end=None):
    query = text("""
        SELECT id, NoteDate, NoteType, Driver, Port, CloseTime, Notes
        FROM dispatch_calendar_notes
        WHERE (:start_date IS NULL OR NoteDate >= :start_date)
          AND (:end_date IS NULL OR NoteDate <= :end_date)
        ORDER BY NoteDate, id
    """)
    rows = db.session.execute(query, {
        'start_date': start,
        'end_date': end,
    }).mappings().all()
    events = []
    for row in rows:
        if row.get('NoteType') == 'port_closed':
            continue
        class_names = ['dispatch-special-note', f"dispatch-note-{row.get('NoteType')}"]
        events.append({
            'id': f"note-{row.get('id')}",
            'title': note_label(row),
            'start': format_date(row.get('NoteDate')),
            'allDay': True,
            'editable': False,
            'classNames': class_names,
            'extendedProps': {
                'is_note': True,
                'note_id': row.get('id'),
                'note_type': row.get('NoteType') or '',
                'driver': row.get('Driver') or '',
                'port': row.get('Port') or '',
                'close_time': row.get('CloseTime') or '',
                'notes': row.get('Notes') or '',
                'note_date': format_date(row.get('NoteDate')),
            },
        })
    return events


def calendar_notes(start=None, end=None):
    ensure_dispatch_calendar_tables()
    query = text("""
        SELECT id, NoteDate, NoteType, Driver, Port, CloseTime, Notes
        FROM dispatch_calendar_notes
        WHERE (:start_date IS NULL OR NoteDate >= :start_date)
          AND (:end_date IS NULL OR NoteDate <= :end_date)
        ORDER BY NoteDate, NoteType, Driver, Port, id
    """)
    rows = db.session.execute(query, {
        'start_date': start,
        'end_date': end,
    }).mappings().all()
    return [{
        'id': row.get('id'),
        'date': format_date(row.get('NoteDate')),
        'type': row.get('NoteType') or '',
        'label': note_label(row),
        'driver': row.get('Driver') or '',
        'port': row.get('Port') or '',
        'close_time': row.get('CloseTime') or '',
        'notes': row.get('Notes') or '',
    } for row in rows]


def sync_port_closed(note_date, note_type, port, notes):
    if note_type != 'port_closed':
        return
    existing = PortClosed.query.filter(PortClosed.Date == note_date).first()
    reason = clean_text(notes) or f"{clean_text(port) or 'Port'} closed"
    if existing is None:
        db.session.add(PortClosed(Date=note_date, Reason=reason))
    else:
        existing.Reason = reason


def remove_port_closed_if_unused(note_date):
    remaining = db.session.execute(text("""
        SELECT COUNT(*) AS note_count
        FROM dispatch_calendar_notes
        WHERE NoteDate = :note_date AND NoteType = 'port_closed'
    """), {'note_date': note_date}).scalar() or 0
    if remaining == 0:
        PortClosed.query.filter(PortClosed.Date == note_date).delete()


def save_calendar_note(data, username=None):
    ensure_dispatch_calendar_tables()
    note_id = data.get('id')
    note_date = parse_date(data.get('date'))
    end_date = parse_date(data.get('end_date')) if data.get('end_date') else note_date
    note_type = clean_text(data.get('type'))
    if note_date is None:
        return {'ok': False, 'error': 'Note date is required.'}, 400
    if end_date is None:
        return {'ok': False, 'error': 'End date is invalid.'}, 400
    if end_date < note_date:
        return {'ok': False, 'error': 'End date cannot be before start date.'}, 400
    if note_id and end_date != note_date:
        return {'ok': False, 'error': 'Edit one existing note at a time. Clear the form to add a new range.'}, 400
    if (end_date - note_date).days > 45:
        return {'ok': False, 'error': 'Date range cannot exceed 45 days.'}, 400
    if note_type not in ['driver_off', 'port_closed', 'port_early_close']:
        return {'ok': False, 'error': 'Choose driver off, port closed, or early close.'}, 400
    driver = clean_text(data.get('driver'))
    port = clean_text(data.get('port')) or 'Baltimore Seagirt'
    close_time = clean_text(data.get('close_time'))
    notes = clean_text(data.get('notes'))
    if note_type == 'driver_off' and not driver:
        return {'ok': False, 'error': 'Choose the driver who is off.'}, 400

    now = datetime.datetime.utcnow()
    old_date = None
    old_type = None
    if note_id:
        existing = db.session.execute(
            text('SELECT NoteDate, NoteType FROM dispatch_calendar_notes WHERE id = :note_id'),
            {'note_id': note_id},
        ).mappings().first()
        if existing is None:
            return {'ok': False, 'error': 'Calendar note was not found.'}, 404
        old_date = existing.get('NoteDate')
        old_type = existing.get('NoteType')
        db.session.execute(text("""
            UPDATE dispatch_calendar_notes
            SET NoteDate = :note_date,
                NoteType = :note_type,
                Driver = :driver,
                Port = :port,
                CloseTime = :close_time,
                Notes = :notes,
                UpdatedAt = :updated_at
            WHERE id = :note_id
        """), {
            'note_id': note_id,
            'note_date': note_date,
            'note_type': note_type,
            'driver': driver,
            'port': port,
            'close_time': close_time,
            'notes': notes,
            'updated_at': now,
        })
        saved_id = int(note_id)
    else:
        saved_id = None
        current_date = note_date
        while current_date <= end_date:
            result = db.session.execute(text("""
                INSERT INTO dispatch_calendar_notes
                    (NoteDate, NoteType, Driver, Port, CloseTime, Notes, CreatedBy, CreatedAt, UpdatedAt)
                VALUES
                    (:note_date, :note_type, :driver, :port, :close_time, :notes, :created_by, :created_at, :updated_at)
            """), {
                'note_date': current_date,
                'note_type': note_type,
                'driver': driver,
                'port': port,
                'close_time': close_time,
                'notes': notes,
                'created_by': username,
                'created_at': now,
                'updated_at': now,
            })
            saved_id = saved_id or result.lastrowid
            sync_port_closed(current_date, note_type, port, notes)
            current_date = current_date + datetime.timedelta(days=1)

    if note_id:
        sync_port_closed(note_date, note_type, port, notes)
    if old_type == 'port_closed' and (old_date != note_date or note_type != 'port_closed'):
        remove_port_closed_if_unused(old_date)
    db.session.commit()
    return {
        'ok': True,
        'created_count': (end_date - note_date).days + 1 if not note_id else 1,
        'note': calendar_notes(note_date, end_date)[0] if saved_id else None,
    }, 200


def delete_calendar_note(note_id):
    ensure_dispatch_calendar_tables()
    existing = db.session.execute(
        text('SELECT NoteDate, NoteType FROM dispatch_calendar_notes WHERE id = :note_id'),
        {'note_id': note_id},
    ).mappings().first()
    if existing is None:
        return {'ok': False, 'error': 'Calendar note was not found.'}, 404
    note_date = existing.get('NoteDate')
    note_type = existing.get('NoteType')
    db.session.execute(
        text('DELETE FROM dispatch_calendar_notes WHERE id = :note_id'),
        {'note_id': note_id},
    )
    if note_type == 'port_closed':
        remove_port_closed_if_unused(note_date)
    db.session.commit()
    return {'ok': True}, 200


def audit_change(order_id, username, action, old_value, new_value):
    db.session.execute(
        text("""
            INSERT INTO dispatch_calendar_audit (OrderId, Username, Action, OldValue, NewValue, CreatedAt)
            VALUES (:order_id, :username, :action, :old_value, :new_value, :created_at)
        """),
        {
            'order_id': order_id,
            'username': username,
            'action': action,
            'old_value': old_value,
            'new_value': new_value,
            'created_at': datetime.datetime.utcnow(),
        },
    )


def upsert_schedule(order_id, scheduled_date, scheduled_time=None, notes=None, username=None, action='schedule_update'):
    ensure_dispatch_calendar_tables()
    existing = schedule_row(order_id)
    now = datetime.datetime.utcnow()
    old_value = dict(existing) if existing else {}
    if existing:
        db.session.execute(
            text("""
                UPDATE dispatch_calendar_schedule
                SET ScheduledDate = :scheduled_date,
                    ScheduledTime = :scheduled_time,
                    Notes = :notes,
                    UpdatedAt = :updated_at
                WHERE OrderId = :order_id
            """),
            {
                'order_id': order_id,
                'scheduled_date': scheduled_date,
                'scheduled_time': scheduled_time,
                'notes': notes if notes is not None else existing.get('Notes'),
                'updated_at': now,
            },
        )
    else:
        db.session.execute(
            text("""
                INSERT INTO dispatch_calendar_schedule
                    (OrderId, ScheduledDate, ScheduledTime, Notes, CreatedAt, UpdatedAt)
                VALUES
                    (:order_id, :scheduled_date, :scheduled_time, :notes, :created_at, :updated_at)
            """),
            {
                'order_id': order_id,
                'scheduled_date': scheduled_date,
                'scheduled_time': scheduled_time,
                'notes': notes,
                'created_at': now,
                'updated_at': now,
            },
        )
    new_value = {
        'ScheduledDate': scheduled_date.strftime(DATE_FORMAT) if scheduled_date else '',
        'ScheduledTime': scheduled_time or '',
        'Notes': notes or '',
    }
    audit_change(order_id, username, action, str(old_value), str(new_value))
    db.session.commit()


def move_event(order_id, start_value, username=None):
    order = Orders.query.get(order_id)
    if order is None or not is_active_order(order):
        return {'ok': False, 'error': 'Order not found or inactive.'}, 404
    new_start = parse_datetime(start_value)
    if new_start is None:
        return {'ok': False, 'error': 'Invalid scheduled date.'}, 400
    scheduled_time = new_start.strftime('%H:%M') if new_start.time() != datetime.time.min else ''
    upsert_schedule(order.id, new_start.date(), scheduled_time, username=username, action='move')
    return {'ok': True, 'event': order_to_event(order, schedule_row(order.id))}, 200


def update_event(order_id, data, username=None):
    order = Orders.query.get(order_id)
    if order is None or not is_active_order(order):
        return {'ok': False, 'error': 'Order not found or inactive.'}, 404
    scheduled_date = parse_date(data.get('scheduled_date'))
    if scheduled_date is None:
        return {'ok': False, 'error': 'Scheduled delivery date is required.'}, 400
    scheduled_time = clean_text(data.get('scheduled_time'))
    order_date_fields = {
        'Date': parse_date(data.get('pull_date')),
        'Date2': parse_date(data.get('return_date')),
        'Date3': parse_date(data.get('delivery_date')),
        'Date4': parse_date(data.get('first_available_date')),
        'Date5': parse_date(data.get('port_deadline_date')),
        'Date6': parse_date(data.get('ship_arrive_date')),
        'Date7': parse_date(data.get('due_back_date')),
        'Date8': parse_date(data.get('secondary_action_date')),
    }
    try:
        hstat = int(order.Hstat or 0)
    except:
        hstat = 0
    import_job = is_import_order(order)
    drop_pick_job = is_drop_pick_order(order)
    previous_pull_date = format_date(order.Date)
    previous_ship_arrive = format_date(order.Date6)
    old_value = {
        'Driver': order.Driver,
        'Truck': order.Truck,
        'Status': order.Status,
        'Date': format_date(order.Date),
        'Date2': format_date(order.Date2),
        'Date3': format_date(order.Date3),
        'Time3': order.Time3,
        'Date4': format_date(order.Date4),
        'Date5': format_date(order.Date5),
        'Date6': format_date(order.Date6),
        'Date7': format_date(order.Date7),
        'Date8': format_date(order.Date8),
    }
    order.Driver = clean_text(data.get('driver'))
    order.Truck = clean_text(data.get('truck'))
    order.Status = clean_text(data.get('status')) or order.Status
    order.Date = date_to_datetime(order_date_fields['Date'])
    order.Date2 = date_to_datetime(order_date_fields['Date2'])
    order.Date3 = date_to_datetime(order_date_fields['Date3'])
    order.Date4 = date_to_datetime(order_date_fields['Date4'])
    order.Date5 = date_to_datetime(order_date_fields['Date5'])
    if import_job:
        order.Date6 = date_to_datetime(order_date_fields['Date6'])
    pull_date_changed = previous_pull_date != format_date(date_to_datetime(order_date_fields['Date']))
    if order_date_fields['Date'] and (pull_date_changed or order_date_fields['Date7'] is None):
        order.Date7 = date_to_datetime(add_business_days(order_date_fields['Date'], 4))
    else:
        order.Date7 = date_to_datetime(order_date_fields['Date7'])
    if drop_pick_job:
        order.Date8 = date_to_datetime(order_date_fields['Date8'])
    ship_arrive_changed = import_job and hstat < 1 and previous_ship_arrive != format_date(order.Date6)
    if ship_arrive_changed and order.Date6:
        order.Date4 = order.Date6
        order.Date5 = date_to_datetime(add_business_days(order.Date6.date(), 3))
    order.Time3 = clean_text(data.get('delivery_time'))
    order.UserMod = username
    db.session.commit()
    upsert_schedule(
        order.id,
        scheduled_date,
        scheduled_time,
        notes=clean_text(data.get('notes')),
        username=username,
        action='modal_update',
    )
    audit_change(order.id, username, 'order_fields_update', str(old_value), str({
        'Driver': order.Driver,
        'Truck': order.Truck,
        'Status': order.Status,
        'Date': format_date(order.Date),
        'Date2': format_date(order.Date2),
        'Date3': format_date(order.Date3),
        'Time3': order.Time3,
        'Date4': format_date(order.Date4),
        'Date5': format_date(order.Date5),
        'Date6': format_date(order.Date6),
        'Date7': format_date(order.Date7),
        'Date8': format_date(order.Date8),
    }))
    db.session.commit()
    return {'ok': True, 'event': order_to_event(order, schedule_row(order.id))}, 200


def filter_options():
    orders = Orders.query.order_by(Orders.Company).limit(5000).all()
    customers = sorted({order.Company for order in orders if order.Company})
    statuses = sorted({order.Status for order in orders if order.Status and len(order.Status) < 80})
    terminals = sorted({value for order in orders for value in [order.Pickup, order.Location] if value})
    drivers = Drivers.query.filter((Drivers.Active == 1) | (Drivers.Active == None)).order_by(Drivers.Name).all()
    trucks = Vehicles.query.filter((Vehicles.Active == 1) | (Vehicles.Active == None)).order_by(Vehicles.Unit).all()
    return {
        'customers': customers[:500],
        'statuses': statuses[:200],
        'terminals': terminals[:300],
        'drivers': drivers,
        'trucks': trucks,
    }


def active_capacity():
    driver_count = Drivers.query.filter(Drivers.Active == 1).count()
    truck_count = Vehicles.query.filter((Vehicles.Active == 1) & (Vehicles.Type == 'Tractor')).count()
    if driver_count == 0:
        driver_count = Drivers.query.count()
    if truck_count == 0:
        truck_count = Vehicles.query.filter(Vehicles.Type == 'Tractor').count()
    if truck_count == 0:
        truck_count = Vehicles.query.count()
    return driver_count or 0, truck_count or 0


def capacity_summary(start=None, end=None, filters=None):
    events = calendar_events(start, end, filters)
    driver_count, truck_count = active_capacity()
    daily_capacity = min(driver_count, truck_count) if driver_count and truck_count else max(driver_count, truck_count)
    notes = calendar_notes(start, end)
    note_map = {}
    for note in notes:
        bucket = note_map.setdefault(note['date'], {'driver_off': 0, 'port_closed': 0, 'port_early_close': 0})
        if note['type'] in bucket:
            bucket[note['type']] += 1
    for closure in port_closures(start, end):
        date_key = format_date(closure.Date)
        bucket = note_map.setdefault(date_key, {'driver_off': 0, 'port_closed': 0, 'port_early_close': 0})
        bucket['port_closed'] = max(1, bucket.get('port_closed', 0))
    grouped = {}
    today = datetime.date.today()
    for event in events:
        props = event.get('extendedProps', {})
        if props.get('is_note') or props.get('is_port_closure'):
            continue
        date_key = event['start'][:10]
        date_notes = note_map.get(date_key, {})
        adjusted_capacity = max(0, daily_capacity - int(date_notes.get('driver_off', 0) or 0))
        if date_notes.get('port_closed'):
            adjusted_capacity = 0
        bucket = grouped.setdefault(date_key, {
            'date': date_key,
            'scheduled': 0,
            'driver_capacity': driver_count,
            'truck_capacity': truck_count,
            'capacity': adjusted_capacity,
            'over_capacity': False,
            'lfd_near': 0,
            'lfd_past': 0,
            'due_back_near': 0,
            'due_back_past': 0,
            'driver_off': date_notes.get('driver_off', 0),
            'port_closed': date_notes.get('port_closed', 0),
            'port_early_close': date_notes.get('port_early_close', 0),
        })
        bucket['scheduled'] += 1
        pull_status = event['extendedProps'].get('pull_status')
        if pull_status == 'unpulled':
            lfd = parse_date(event['extendedProps'].get('last_free_day'))
            if lfd:
                diff = (lfd - today).days
                if diff < 0:
                    bucket['lfd_past'] += 1
                elif diff <= 2:
                    bucket['lfd_near'] += 1
        elif pull_status == 'pulled':
            due_back = parse_date(event['extendedProps'].get('due_back_date'))
            if due_back:
                diff = (due_back - today).days
                if diff < 0:
                    bucket['due_back_past'] += 1
                elif diff <= 2:
                    bucket['due_back_near'] += 1
    for bucket in grouped.values():
        bucket['over_capacity'] = bool(bucket['capacity'] and bucket['scheduled'] > bucket['capacity'])
        if bucket['capacity'] == 0 and bucket['scheduled'] > 0:
            bucket['over_capacity'] = True
    return list(grouped.values())
