import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import func

from webapp.extensions import db
from webapp.models import ChassisLocationObservation, Vehicles


def ensure_chassis_location_table():
    ChassisLocationObservation.__table__.create(bind=db.engine, checkfirst=True)


def parse_observed_at(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('observed_at is required')
    normalized = value.strip().replace('Z', '+00:00')
    try:
        parsed = datetime.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError('observed_at must be an ISO-8601 datetime') from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return parsed


def parse_coordinate(value, name, minimum, maximum):
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f'{name} must be numeric') from exc
    if not minimum <= parsed <= maximum:
        raise ValueError(f'{name} is out of range')
    return parsed


def import_observations(payloads):
    ensure_chassis_location_table()
    imported_at = datetime.datetime.utcnow()
    inserted = 0
    duplicates = 0
    results = []
    for index, payload in enumerate(payloads):
        if not isinstance(payload, dict):
            raise ValueError(f'observations[{index}] must be an object')
        chassis_id = str(payload.get('chassis_id') or '').strip()
        airtag_name = str(payload.get('airtag_name') or '').strip()
        if not chassis_id or not airtag_name:
            raise ValueError(f'observations[{index}] requires chassis_id and airtag_name')
        vehicle = Vehicles.query.filter(
            Vehicles.Unit == chassis_id,
            Vehicles.Type == 'Chassis',
            Vehicles.Active == 1,
        ).first()
        if vehicle is None:
            raise ValueError(f'unknown active chassis: {chassis_id}')
        configured_tag = (vehicle.Title or '').strip()
        if configured_tag and configured_tag.casefold() != airtag_name.casefold():
            raise ValueError(f'AirTag {airtag_name!r} is not assigned to chassis {chassis_id}')
        observed_at = parse_observed_at(payload.get('observed_at'))
        latitude = parse_coordinate(payload.get('latitude'), 'latitude', Decimal('-90'), Decimal('90'))
        longitude = parse_coordinate(payload.get('longitude'), 'longitude', Decimal('-180'), Decimal('180'))
        existing = ChassisLocationObservation.query.filter_by(
            VehicleId=vehicle.id,
            ObservedAt=observed_at,
        ).first()
        if existing is not None:
            duplicates += 1
            results.append({'chassis_id': chassis_id, 'status': 'duplicate'})
            continue
        db.session.add(ChassisLocationObservation(
            VehicleId=vehicle.id,
            ChassisId=chassis_id,
            AirTagName=airtag_name,
            Latitude=latitude,
            Longitude=longitude,
            ObservedAt=observed_at,
            ImportedAt=imported_at,
        ))
        inserted += 1
        results.append({'chassis_id': chassis_id, 'status': 'inserted'})
    db.session.commit()
    return inserted, duplicates, results


def chassis_location_rows(now=None):
    ensure_chassis_location_table()
    now = now or datetime.datetime.utcnow()
    latest = db.session.query(
        ChassisLocationObservation.VehicleId.label('vehicle_id'),
        func.max(ChassisLocationObservation.ObservedAt).label('observed_at'),
    ).group_by(ChassisLocationObservation.VehicleId).subquery()
    rows = db.session.query(Vehicles, ChassisLocationObservation).outerjoin(
        latest, latest.c.vehicle_id == Vehicles.id,
    ).outerjoin(
        ChassisLocationObservation,
        (ChassisLocationObservation.VehicleId == latest.c.vehicle_id) &
        (ChassisLocationObservation.ObservedAt == latest.c.observed_at),
    ).filter(
        Vehicles.Type == 'Chassis',
        Vehicles.Active == 1,
    ).order_by(Vehicles.Unit, Vehicles.id).all()

    output = []
    for vehicle, observation in rows:
        age_minutes = None
        freshness = 'missing'
        if observation is not None:
            age_minutes = max(0, int((now - observation.ObservedAt).total_seconds() // 60))
            freshness = 'current' if age_minutes < 60 else ('aging' if age_minutes < 240 else 'stale')
        output.append({
            'vehicle': vehicle,
            'observation': observation,
            'age_minutes': age_minutes,
            'freshness': freshness,
        })
    return output


def age_label(minutes):
    if minutes is None:
        return 'No location received'
    if minutes < 1:
        return 'Last seen just now'
    if minutes < 60:
        return f'Last seen {minutes} minute{"s" if minutes != 1 else ""} ago'
    hours = minutes // 60
    if hours < 24:
        return f'Last seen {hours} hour{"s" if hours != 1 else ""} ago'
    days = hours // 24
    return f'Last seen {days} day{"s" if days != 1 else ""} ago'
