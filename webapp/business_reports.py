import datetime

from sqlalchemy import inspect, text

from webapp.extensions import db
from webapp.models import Interchange


def ensure_interchange_port_trip_column():
    inspector = inspect(db.engine)
    columns = [column['name'] for column in inspector.get_columns('interchange')]
    if 'PortTrip' not in columns:
        db.session.execute(text("""
            ALTER TABLE interchange
            ADD COLUMN PortTrip INT DEFAULT 0
        """))
        db.session.commit()


def parse_interchange_time(value):
    if not value:
        return None
    cleaned = str(value).strip()
    for fmt in ('%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M%p'):
        try:
            parsed = datetime.datetime.strptime(cleaned.upper(), fmt)
            return parsed.hour * 60 + parsed.minute
        except ValueError:
            continue
    digits = ''.join(ch for ch in cleaned if ch.isdigit())
    if len(digits) in (3, 4):
        hour = int(digits[:-2])
        minute = int(digits[-2:])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour * 60 + minute
    return None


def interchange_service_date(row):
    if not row.Date:
        return None
    if isinstance(row.Date, datetime.datetime):
        return row.Date.date()
    return row.Date


def interchange_terminal_key(row):
    return (row.Path or row.Source or row.Company or '').strip().lower()


def is_port_gate_move(row):
    gate_type = (row.Type or '').lower()
    return any(token in gate_type for token in ['in', 'out', 'dray'])


def assign_port_trip_sequence(rows, start_count=1):
    """Assign a shared sequential trip number to each matching port-visit group."""
    for row in rows:
        row.PortTrip = None

    groups = {}
    for row in rows:
        service_date = interchange_service_date(row)
        if not service_date or not is_port_gate_move(row):
            continue
        key = (
            service_date,
            (row.TruckNumber or '').strip().lower(),
            (row.Driver or '').strip().lower(),
            interchange_terminal_key(row),
        )
        groups.setdefault(key, []).append(row)

    trip_groups = []
    for key in groups:
        group_rows = groups[key]
        group_rows.sort(key=lambda item: (
            parse_interchange_time(item.Time) if parse_interchange_time(item.Time) is not None else 99999,
            item.id,
        ))
        current_trip_start = None
        current_rows = []
        for row in group_rows:
            row_time = parse_interchange_time(row.Time)
            if not current_rows:
                current_rows = [row]
                current_trip_start = row_time
            elif row_time is not None and current_trip_start is not None and abs(row_time - current_trip_start) > 180:
                trip_groups.append(current_rows)
                current_rows = [row]
                current_trip_start = row_time
            else:
                current_rows.append(row)
        if current_rows:
            trip_groups.append(current_rows)

    trip_groups.sort(key=lambda group: (
        interchange_service_date(group[0]),
        parse_interchange_time(group[0].Time) if parse_interchange_time(group[0].Time) is not None else 99999,
        group[0].id,
    ))
    trip_number = start_count
    for trip_rows in trip_groups:
        for row in trip_rows:
            row.PortTrip = trip_number
        trip_number += 1
    return trip_number - start_count


def recalculate_interchange_port_trips(start_date=None, end_date=None, start_count=1):
    """Backfill Interchange.PortTrip with yearly sequence numbers.

    Matching gate-ticket rows for the same driver/truck/terminal/date and close
    gate time share the same PortTrip number. The next distinct port visit gets
    the next integer. For a full-year baseline, pass January 1 through December 31
    and start_count=1.
    """
    ensure_interchange_port_trip_column()
    query = Interchange.query
    if start_date:
        query = query.filter(Interchange.Date >= datetime.datetime.combine(start_date, datetime.time.min))
    if end_date:
        query = query.filter(Interchange.Date <= datetime.datetime.combine(end_date, datetime.time.max))
    rows = query.order_by(
        Interchange.Date.asc(),
        Interchange.TruckNumber.asc(),
        Interchange.Driver.asc(),
        Interchange.id.asc(),
    ).all()
    trips = assign_port_trip_sequence(rows, start_count=start_count)
    db.session.commit()
    return {'rows_reviewed': len(rows), 'port_trips': trips}


def rebaseline_interchange_port_trips_for_year(year):
    start_date = datetime.date(year, 1, 1)
    end_date = datetime.date(year, 12, 31)
    return recalculate_interchange_port_trips(start_date, end_date, start_count=1)
