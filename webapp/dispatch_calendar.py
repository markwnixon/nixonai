import datetime

from sqlalchemy import or_, text

from webapp import db
from webapp.CCC_system_setup import scac
from webapp.models import Drivers, Drops, Orders, Pins, Vehicles


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


def schedule_row(order_id):
    ensure_dispatch_calendar_tables()
    return db.session.execute(
        text('SELECT * FROM dispatch_calendar_schedule WHERE OrderId = :order_id'),
        {'order_id': order_id},
    ).mappings().first()


def scheduled_datetime(order, schedule=None):
    # Date mapping:
    # 1. dispatch_calendar_schedule.ScheduledDate/Time is the planning override used by this calendar.
    # 2. Orders.Date2/Time2 is the existing requested/delivery date used by Class8.
    # 3. Orders.Date is a fallback so otherwise-active jobs are still visible.
    if schedule and schedule.get('ScheduledDate'):
        return combine_date_time(schedule.get('ScheduledDate'), schedule.get('ScheduledTime'))
    if order.Date2:
        return combine_date_time(order.Date2, order.Time2)
    return date_to_datetime(order.Date)


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


def order_to_event(order, schedule=None):
    start = scheduled_datetime(order, schedule)
    if start is None:
        return None
    lfd = date_to_datetime(order.Date4)
    pin_status = pin_status_for_order(order)
    delivery_city_state = order_delivery_city_state(order)
    container_label = clean_text(order.Container) or clean_text(order.Booking) or order.Jo
    title_bits = [
        container_label,
        delivery_city_state,
    ]
    if order.Driver:
        title_bits.append(order.Driver)
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

    today = datetime.date.today()
    if lfd:
        days_to_lfd = (lfd.date() - today).days
        if days_to_lfd < 0:
            event_class.append('dispatch-lfd-past')
        elif days_to_lfd <= 2:
            event_class.append('dispatch-lfd-near')

    return {
        'id': str(order.id),
        'title': ' | '.join([part for part in title_bits if part]),
        'start': start.isoformat(),
        'allDay': start.time() == datetime.time.min,
        'classNames': event_class,
        'extendedProps': {
            'jo': order.Jo,
            'company_code': order_company_code(order),
            'container': order.Container or '',
            'customer': order.Company or '',
            'shipper': order.Shipper or '',
            'delivery': order.Delivery or '',
            'delivery_location': order_delivery_location(order),
            'delivery_city_state': delivery_city_state,
            'city': order_city(order),
            'driver': order.Driver or '',
            'truck': order.Truck or '',
            'appointment_time': order.Time2 or '',
            'status': order.Status or '',
            'pull_status': pull_status,
            'haul_type': order.HaulType or '',
            'last_free_day': format_date(order.Date4),
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
    if start_dt:
        query = query.filter(or_(Orders.Date2 >= start_dt, Orders.Date >= start_dt))
    if end_dt:
        query = query.filter(or_(Orders.Date2 < end_dt, Orders.Date < end_dt))
    return query


def filtered_orders(start=None, end=None, filters=None):
    orders = active_orders_query(start, end, filters).order_by(Orders.Date2.asc(), Orders.Date.asc()).limit(1000).all()
    return [order for order in orders if is_active_order(order)]


def calendar_events(start=None, end=None, filters=None):
    ensure_dispatch_calendar_tables()
    orders = filtered_orders(start, end, filters)
    events = []
    for order in orders:
        event = order_to_event(order, schedule_row(order.id))
        if event is not None:
            events.append(event)
    return events


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
    old_value = {
        'Driver': order.Driver,
        'Truck': order.Truck,
        'Status': order.Status,
    }
    order.Driver = clean_text(data.get('driver'))
    order.Truck = clean_text(data.get('truck'))
    order.Status = clean_text(data.get('status')) or order.Status
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
    grouped = {}
    today = datetime.date.today()
    for event in events:
        date_key = event['start'][:10]
        bucket = grouped.setdefault(date_key, {
            'date': date_key,
            'scheduled': 0,
            'driver_capacity': driver_count,
            'truck_capacity': truck_count,
            'capacity': daily_capacity,
            'over_capacity': False,
            'lfd_near': 0,
            'lfd_past': 0,
        })
        bucket['scheduled'] += 1
        lfd = parse_date(event['extendedProps'].get('last_free_day'))
        if lfd:
            diff = (lfd - today).days
            if diff < 0:
                bucket['lfd_past'] += 1
            elif diff <= 2:
                bucket['lfd_near'] += 1
    for bucket in grouped.values():
        bucket['over_capacity'] = bool(bucket['capacity'] and bucket['scheduled'] > bucket['capacity'])
    return list(grouped.values())
