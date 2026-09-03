from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from webapp.extensions import db
from webapp.models import Orders, users, Pins, Vehicles, Drivers, Driverlog, DispatchDriverMessage, DispatchDriverAssignment, Quoteinput
from webapp.viewfuncs import hasinput
from webapp.CCC_system_setup import addpath, apikeys, scac, tpath
from webapp.services.api_data_service import api_call
from webapp.class8_tasks import get_address_details
from webapp.financial_import_api import (
    financial_import_account_options,
    import_paid_bill_payload,
    lookup_financial_import_rule,
)


import os
import datetime
import json
import requests
import pytz
from datetime import timedelta
from sqlalchemy import text
from urllib.parse import quote_plus

now = datetime.datetime.now()

from flask import Blueprint
api_bp = Blueprint('api_bp', __name__)
APP_TIMEZONE = pytz.timezone('America/New_York')


def _first_present(data, keys, default=''):
    for key in keys:
        value = data.get(key)
        if value not in (None, ''):
            return value
    return default


def _api_driver_identity(data, authenticated_username):
    """Use the user's display name as the canonical driver key for driver-facing APIs."""
    udat = users.query.filter(users.username == authenticated_username).first()
    requested_driver = _first_present(data, ['driver', 'Driver', 'driver_name'])
    display_name = (udat.name if udat is not None else '') or requested_driver
    driver_name = requested_driver
    if udat is not None and (udat.authority or '').lower() == 'driver':
        driver_name = display_name
    elif not driver_name and udat is not None:
        driver_name = display_name
    if udat is not None and requested_driver in [udat.username, udat.name]:
        driver_name = display_name
    if not display_name:
        display_name = driver_name
    return udat, driver_name, display_name


def _api_driver_aliases(driver_name, udat=None):
    aliases = []
    for value in [driver_name, getattr(udat, 'name', None), getattr(udat, 'username', None)]:
        if value and value not in aliases:
            aliases.append(value)
    if driver_name:
        rows = users.query.filter(
            (users.username == driver_name) | (users.name == driver_name)
        ).all()
        for row in rows:
            for value in [row.name, row.username]:
                if value and value not in aliases:
                    aliases.append(value)
    return aliases or [driver_name]


def _parse_driver_log_datetime(data):
    """Accept iOS ISO datetimes, or separate date/time values, and store naive datetimes."""
    value = _first_present(data, ['datetime', 'timestamp', 'gps_time', 'log_datetime'])
    if value:
        if isinstance(value, str):
            value = value.strip()
            if value.endswith('Z'):
                value = value[:-1] + '+00:00'
            parsed = datetime.datetime.fromisoformat(value)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(APP_TIMEZONE)
            return parsed.replace(tzinfo=None)
        if isinstance(value, datetime.datetime):
            if value.tzinfo is not None:
                value = value.astimezone(APP_TIMEZONE)
            return value.replace(tzinfo=None)

    date_value = _first_present(data, ['date', 'Date'])
    time_value = _first_present(data, ['time', 'Time'])
    if date_value and time_value:
        parsed = datetime.datetime.fromisoformat(f'{date_value}T{time_value}')
        return parsed.replace(tzinfo=None)
    if date_value:
        parsed_date = datetime.date.fromisoformat(str(date_value))
        return datetime.datetime.combine(parsed_date, datetime.time())
    return datetime.datetime.now(APP_TIMEZONE).replace(tzinfo=None)


def _driver_log_location(data, log_action):
    if log_action == 'in':
        value = _first_present(data, ['locationstart', 'Locationstart', 'location_start'])
    else:
        value = _first_present(data, ['locationstop', 'Locationstop', 'location_stop'])
    if value:
        return str(value)[:45]

    value = _first_present(data, ['location', 'Location'])
    if value:
        return str(value)[:45]

    lat = _first_present(data, ['lat', 'latitude'])
    lon = _first_present(data, ['lon', 'lng', 'longitude'])
    if lat not in (None, '') and lon not in (None, ''):
        return f'{lat},{lon}'[:45]
    return ''


def _driver_log_coordinates(data):
    value = _first_present(data, ['gps', 'GPS', 'coordinates'])
    if value:
        return str(value)[:45]

    lat = _first_present(data, ['lat', 'latitude'])
    lon = _first_present(data, ['lon', 'lng', 'longitude'])
    if lat not in (None, '') and lon not in (None, ''):
        return f'{lat},{lon}'[:45]
    return ''


def _driver_log_action(data):
    action = _first_present(data, ['action', 'indicator', 'status', 'event', 'direction'])
    action = str(action).strip().lower()
    if action in ['in', 'login', 'log-in', 'log_in', 'clock-in', 'clockin', 'clock_in', 'start', 'gpsin']:
        return 'in'
    if action in ['out', 'logout', 'log-out', 'log_out', 'clock-out', 'clockout', 'clock_out', 'stop', 'gpsout']:
        return 'out'
    return None


def _driver_log_payload(row):
    return {
        'id': row.id,
        'date': row.Date.isoformat() if row.Date else None,
        'driver': row.Driver,
        'clockin': row.Clockin.isoformat() if row.Clockin else None,
        'clockout': row.Clockout.isoformat() if row.Clockout else None,
        'truck': row.Truck,
        'gps_start': row.GPSin,
        'gps_stop': row.GPSout,
        'locationstart': row.Locationstart,
        'locationstop': row.Locationstop,
        'shift': row.Shift,
        'status': row.Status,
    }


def _ensure_dispatch_driver_message_table():
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS dispatch_driver_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Co VARCHAR(12) NULL,
            OrderId INT NULL,
            Jo VARCHAR(25) NULL,
            Container VARCHAR(50) NULL,
            Driver VARCHAR(100) NULL,
            SenderName VARCHAR(100) NULL,
            SenderType VARCHAR(30) NULL,
            MessageText TEXT NULL,
            RouteJson TEXT NULL,
            CreatedAt DATETIME NOT NULL,
            ReadAt DATETIME NULL,
            Active INT NOT NULL DEFAULT 1,
            INDEX idx_dispatch_driver_msg_order (OrderId),
            INDEX idx_dispatch_driver_msg_jo (Jo),
            INDEX idx_dispatch_driver_msg_driver (Driver),
            INDEX idx_dispatch_driver_msg_created (CreatedAt)
        )
    """))
    existing_columns = db.session.execute(text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'dispatch_driver_messages'
    """)).fetchall()
    column_names = [row[0] for row in existing_columns]
    if 'RouteJson' not in column_names:
        db.session.execute(text("ALTER TABLE dispatch_driver_messages ADD COLUMN RouteJson TEXT NULL"))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS dispatch_driver_assignments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Co VARCHAR(12) NULL,
            Driver VARCHAR(100) NULL,
            AssignmentType VARCHAR(45) NULL,
            PrimaryOrderId INT NULL,
            SecondaryOrderId INT NULL,
            PrimaryJo VARCHAR(25) NULL,
            SecondaryJo VARCHAR(25) NULL,
            PrimaryContainer VARCHAR(50) NULL,
            SecondaryContainer VARCHAR(50) NULL,
            RouteOrderId INT NULL,
            DestinationName VARCHAR(100) NULL,
            DestinationAddress VARCHAR(500) NULL,
            MessageText TEXT NULL,
            RouteJson TEXT NULL,
            Status VARCHAR(45) NULL,
            CreatedBy VARCHAR(100) NULL,
            CreatedAt DATETIME NOT NULL,
            Active INT NOT NULL DEFAULT 1,
            INDEX idx_dispatch_driver_assign_driver (Driver),
            INDEX idx_dispatch_driver_assign_primary (PrimaryOrderId),
            INDEX idx_dispatch_driver_assign_secondary (SecondaryOrderId),
            INDEX idx_dispatch_driver_assign_created (CreatedAt)
        )
    """))
    existing_assignment_columns = db.session.execute(text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'dispatch_driver_assignments'
    """)).fetchall()
    assignment_column_names = [row[0] for row in existing_assignment_columns]
    if 'RouteJson' not in assignment_column_names:
        db.session.execute(text("ALTER TABLE dispatch_driver_assignments ADD COLUMN RouteJson TEXT NULL"))
    db.session.commit()


def _message_payload(row, display_name):
    direction = 'outbound'
    if (row.SenderName or '') == display_name or (row.SenderType or '').lower() == 'driver':
        direction = 'inbound'
    route_payload = None
    if getattr(row, 'RouteJson', None):
        try:
            route_payload = json.loads(row.RouteJson)
        except (TypeError, ValueError):
            route_payload = None
    return {
        'id': row.id,
        'co': row.Co,
        'order_id': row.OrderId,
        'jo': row.Jo,
        'container': row.Container,
        'driver': row.Driver,
        'sender_name': row.SenderName,
        'sender_type': row.SenderType,
        'direction': direction,
        'message_flow': 'driver_to_dispatch' if (row.SenderType or '').lower() == 'driver' else 'dispatch_to_driver',
        'message': row.MessageText,
        'route': route_payload,
        'created_at': row.CreatedAt.isoformat() if row.CreatedAt else None,
        'read_at': row.ReadAt.isoformat() if row.ReadAt else None,
    }


def _assignment_payload(row):
    route_payload = None
    if getattr(row, 'RouteJson', None):
        try:
            route_payload = json.loads(row.RouteJson)
        except (TypeError, ValueError):
            route_payload = None
    return {
        'id': row.id,
        'driver': row.Driver,
        'assignment_type': row.AssignmentType,
        'primary_order_id': row.PrimaryOrderId,
        'secondary_order_id': row.SecondaryOrderId,
        'primary_jo': row.PrimaryJo,
        'secondary_jo': row.SecondaryJo,
        'primary_container': row.PrimaryContainer,
        'secondary_container': row.SecondaryContainer,
        'route_order_id': row.RouteOrderId,
        'destination_name': row.DestinationName,
        'destination_address': row.DestinationAddress,
        'message_text': row.MessageText,
        'route': route_payload,
        'status': row.Status,
        'created_by': row.CreatedBy,
        'created_at': row.CreatedAt.isoformat() if row.CreatedAt else None,
    }


def _pending_dispatch_assignments(driver_name):
    _ensure_dispatch_driver_message_table()
    rows = DispatchDriverAssignment.query.filter(
        DispatchDriverAssignment.Driver == driver_name,
        DispatchDriverAssignment.Active == 1,
        DispatchDriverAssignment.Status.in_(['pending', 'draft'])
    ).order_by(DispatchDriverAssignment.CreatedAt, DispatchDriverAssignment.id).all()
    return [_assignment_payload(row) for row in rows]


def _dispatch_order_from_request(data):
    order_id = _first_present(data, ['order_id', 'OrderId', 'id'])
    jo = _first_present(data, ['jo', 'Jo'])
    container = _first_present(data, ['container', 'Container'])

    query = Orders.query
    if order_id:
        try:
            return db.session.get(Orders, int(order_id))
        except (TypeError, ValueError):
            return None
    if jo:
        return query.filter(Orders.Jo == jo).order_by(Orders.id.desc()).first()
    if container:
        return query.filter(Orders.Container == container).order_by(Orders.id.desc()).first()
    return None


def _clean_route_text(value):
    return (value or '').replace('\r', ' ').replace('\n', ' ').strip()


def _parse_coordinate_pair(value):
    if not value:
        return None
    try:
        parts = str(value).replace(';', ',').split(',')
        if len(parts) < 2:
            return None
        return float(parts[0].strip()), float(parts[1].strip())
    except (TypeError, ValueError):
        return None


def _google_distance(origin, destination):
    api_key = ''
    try:
        api_key = apikeys.get('dkey') or ''
    except Exception:
        api_key = ''
    if not api_key or not origin or not destination:
        return None
    try:
        response = requests.get(
            'https://maps.googleapis.com/maps/api/distancematrix/json',
            params={
                'units': 'imperial',
                'origins': origin,
                'destinations': destination,
                'key': api_key,
            },
            timeout=6,
        )
        payload = response.json()
        element = payload['rows'][0]['elements'][0]
        if element.get('status') != 'OK':
            return None
        return {
            'distance_text': element.get('distance', {}).get('text'),
            'duration_text': element.get('duration', {}).get('text'),
            'provider': 'google_distance_matrix',
        }
    except Exception:
        return None


def _route_point_from_value(value):
    if isinstance(value, dict):
        lat = _first_present(value, ['lat', 'latitude'])
        lng = _first_present(value, ['lng', 'lon', 'longitude'])
        if lat not in (None, '') and lng not in (None, ''):
            try:
                lat_float = float(lat)
                lng_float = float(lng)
            except (TypeError, ValueError):
                return None, ''
            return {
                'location': {
                    'latLng': {
                        'latitude': lat_float,
                        'longitude': lng_float,
                    }
                }
            }, f'{lat_float},{lng_float}'

        address = _first_present(value, ['address', 'location', 'name', 'text'])
        if address:
            return {'address': str(address)}, str(address)
        return None, ''

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            lat_float = float(value[0])
            lng_float = float(value[1])
        except (TypeError, ValueError):
            return None, ''
        return {
            'location': {
                'latLng': {
                    'latitude': lat_float,
                    'longitude': lng_float,
                }
            }
        }, f'{lat_float},{lng_float}'

    text_value = _clean_route_text(value)
    if not text_value:
        return None, ''

    coordinates = _parse_coordinate_pair(text_value)
    if coordinates is not None:
        lat_float, lng_float = coordinates
        return {
            'location': {
                'latLng': {
                    'latitude': lat_float,
                    'longitude': lng_float,
                }
            }
        }, f'{lat_float},{lng_float}'

    return {'address': text_value}, text_value


def _route_point_from_request(data, point_names, lat_names, lng_names):
    for point_name in point_names:
        value = data.get(point_name)
        route_point, label = _route_point_from_value(value)
        if route_point:
            return route_point, label

    lat = _first_present(data, lat_names)
    lng = _first_present(data, lng_names)
    if lat not in (None, '') and lng not in (None, ''):
        return _route_point_from_value({'lat': lat, 'lng': lng})
    return None, ''


def _google_duration_seconds(value):
    if not value:
        return None
    try:
        if isinstance(value, str) and value.endswith('s'):
            return int(round(float(value[:-1])))
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _format_route_duration(seconds):
    if seconds is None:
        return ''
    minutes = int(round(seconds / 60.0))
    hours = minutes // 60
    remainder = minutes % 60
    if hours and remainder:
        return f'{hours} hr {remainder} min'
    if hours:
        return f'{hours} hr'
    return f'{remainder} min'


def _format_route_distance(meters):
    if meters is None:
        return ''
    miles = float(meters) / 1609.344
    return f'{miles:.1f} mi'


def _route_api_key():
    try:
        return apikeys.get('dkey') or ''
    except Exception:
        return ''


def _google_routes_payload(origin, destination, avoid_tolls=False, departure_time=None):
    body = {
        'origin': origin,
        'destination': destination,
        'travelMode': 'DRIVE',
        'routingPreference': 'TRAFFIC_AWARE',
        'computeAlternativeRoutes': True,
        'units': 'IMPERIAL',
    }
    if avoid_tolls:
        body['routeModifiers'] = {'avoidTolls': True}
    if departure_time:
        body['departureTime'] = departure_time
    return body


def _normalize_google_route(route, route_set, index):
    duration_seconds = _google_duration_seconds(route.get('duration'))
    static_duration_seconds = _google_duration_seconds(route.get('staticDuration'))
    distance_meters = route.get('distanceMeters')
    polyline = route.get('polyline') or {}
    advisory = route.get('travelAdvisory') or {}
    steps = []
    for leg in route.get('legs') or []:
        for step in leg.get('steps') or []:
            instruction = (step.get('navigationInstruction') or {}).get('instructions') or ''
            steps.append({
                'instruction': instruction,
                'distance_meters': step.get('distanceMeters'),
                'duration_seconds': _google_duration_seconds(step.get('staticDuration') or step.get('duration')),
                'polyline': (step.get('polyline') or {}).get('encodedPolyline'),
            })

    return {
        'route_id': f'{route_set}_{index + 1}',
        'route_set': route_set,
        'description': route.get('description') or '',
        'distance_meters': distance_meters,
        'distance_text': _format_route_distance(distance_meters),
        'duration_seconds': duration_seconds,
        'duration_text': _format_route_duration(duration_seconds),
        'static_duration_seconds': static_duration_seconds,
        'static_duration_text': _format_route_duration(static_duration_seconds),
        'encoded_polyline': polyline.get('encodedPolyline'),
        'has_toll_info': bool(advisory.get('tollInfo')),
        'travel_advisory': advisory,
        'steps': steps,
    }


def _decode_google_polyline(encoded):
    if not encoded:
        return []
    index = 0
    lat = 0
    lng = 0
    coordinates = []
    while index < len(encoded):
        result = 0
        shift = 0
        while True:
            value = ord(encoded[index]) - 63
            index += 1
            result |= (value & 0x1f) << shift
            shift += 5
            if value < 0x20:
                break
        lat += ~(result >> 1) if result & 1 else result >> 1

        result = 0
        shift = 0
        while True:
            value = ord(encoded[index]) - 63
            index += 1
            result |= (value & 0x1f) << shift
            shift += 5
            if value < 0x20:
                break
        lng += ~(result >> 1) if result & 1 else result >> 1
        coordinates.append((lat / 100000.0, lng / 100000.0))
    return coordinates


def _route_crosses_box(points, tollbox):
    if len(points) < 2:
        return False
    lah = max([tollbox[0], tollbox[2]])
    lal = min([tollbox[0], tollbox[2]])
    loh = max([tollbox[1], tollbox[3]])
    lol = min([tollbox[1], tollbox[3]])
    for index in range(1, len(points)):
        la_last, lo_last = points[index - 1]
        la, lo = points[index]
        lanow = la_last
        lonow = lo_last
        lastep = (la - la_last) / 100
        lostep = (lo - lo_last) / 100
        for _step in range(100):
            lanow += lastep
            lonow += lostep
            if lanow > lal and lanow < lah and lonow > lol and lonow < loh:
                return True
    return False


def _route_coordinate_points(coordinates):
    points = []
    for point in coordinates or []:
        if not isinstance(point, dict):
            continue
        lat = _first_present(point, ['latitude', 'lat'])
        lng = _first_present(point, ['longitude', 'lng', 'lon'])
        try:
            points.append((float(lat), float(lng)))
        except (TypeError, ValueError):
            continue
    return points


def _route_cost_inputs():
    qidat = Quoteinput.query.order_by(Quoteinput.id.desc()).first()
    if qidat is None:
        return None
    return {
        'source': 'quoteinput',
        'quoteinput_id': qidat.id,
        'driver_hourly_cost': float(qidat.ph_driver or 0) / 100,
        'fuel_price_per_gallon': float(qidat.fuelpergal or 0) / 100,
        'mpg': float(qidat.mpg or 0) / 100,
        'standard_toll_amount': float(qidat.toll or 0) / 100,
    }


def _route_toll_analysis(route, cost_inputs):
    road_tolls = [
        ('I-76', 0.784),
        ('NJ Tpke', 0.275),
        ('MD-200', 0.35),
    ]
    plaza_tolls = [
        ('FM', [39.267757, -76.610192, 39.261248, -76.563158], cost_inputs['standard_toll_amount']),
        ('BHT', [39.269962, -76.566240, 39.239063, -76.58], cost_inputs['standard_toll_amount']),
        ('FSK', [39.232770, -76.502453, 39.202279, -76.569906], cost_inputs['standard_toll_amount']),
        ('BAY', [39.026893, -76.417512, 38.964938, -76.290104], cost_inputs['standard_toll_amount']),
        ('SUS', [39.478100, -76.112203, 39.608403, -76.062308], cost_inputs['standard_toll_amount']),
        ('NEW', [39.634568, -75.773041, 39.657970, -75.754566], cost_inputs['standard_toll_amount']),
        ('DMB', [39.644216, -75.570003, 39.721472, -75.465073], cost_inputs['standard_toll_amount']),
        ('DTR', [38.932101, -77.243797, 38.942280, -77.230473], 10.50),
    ]
    tolls = []
    total = 0.0

    instruction_steps = route.get('steps') or []
    if route.get('route_name'):
        instruction_steps = instruction_steps + [{
            'instruction': route.get('route_name') or '',
            'distance_meters': route.get('distance_meters') or 0,
        }]

    for step in instruction_steps:
        instruction = step.get('instruction') or ''
        step_miles = (step.get('distance_meters') or 0) / 1609.344
        for road_name, cost_per_mile in road_tolls:
            if road_name in instruction and step_miles:
                amount = step_miles * cost_per_mile
                tolls.append({
                    'code': road_name,
                    'source': 'road_instruction',
                    'amount': round(amount, 2),
                    'basis': f'{step_miles:.1f} mi at ${cost_per_mile:.3f}/mi',
                })
                total += amount

    points = route.get('coordinates') or _decode_google_polyline(route.get('encoded_polyline'))
    for code, tollbox, amount in plaza_tolls:
        if _route_crosses_box(points, tollbox):
            tolls.append({
                'code': code,
                'source': 'route_crossing',
                'amount': round(amount, 2),
                'basis': 'configured toll plaza crossing',
            })
            total += amount

    return {
        'toll_cost': round(total, 2),
        'toll_count': len(tolls),
        'tolls': tolls,
    }


def _attach_route_cost(route, cost_inputs):
    miles = (route.get('distance_meters') or 0) / 1609.344
    duration_seconds = route.get('duration_seconds') or route.get('static_duration_seconds') or 0
    hours = duration_seconds / 3600.0
    mpg = cost_inputs.get('mpg') or 0
    fuel_cost = (miles / mpg) * cost_inputs['fuel_price_per_gallon'] if mpg else 0.0
    driver_cost = hours * cost_inputs['driver_hourly_cost']
    toll_analysis = _route_toll_analysis(route, cost_inputs)
    total_cost = fuel_cost + driver_cost + toll_analysis['toll_cost']
    route['cost_analysis'] = {
        'distance_miles': round(miles, 2),
        'duration_hours': round(hours, 2),
        'fuel_price_per_gallon': round(cost_inputs['fuel_price_per_gallon'], 2),
        'mpg': round(mpg, 2),
        'driver_hourly_cost': round(cost_inputs['driver_hourly_cost'], 2),
        'fuel_cost': round(fuel_cost, 2),
        'driver_cost': round(driver_cost, 2),
        'toll_cost': toll_analysis['toll_cost'],
        'total_cost': round(total_cost, 2),
        'tolls': toll_analysis['tolls'],
    }
    return route


def _attach_costs_to_routes(routes, cost_inputs):
    return [_attach_route_cost(route, cost_inputs) for route in routes]


def _normalize_ios_route_candidate(candidate, index):
    if not isinstance(candidate, dict):
        return None, f'Candidate {index + 1} is not an object.'

    candidate_id = _first_present(candidate, ['candidate_id', 'id']) or f'candidate_{index + 1}'
    try:
        distance_meters = float(candidate.get('distance_meters') or 0)
    except (TypeError, ValueError):
        return None, f'Candidate {candidate_id} has invalid distance_meters.'
    try:
        duration_seconds = float(candidate.get('expected_travel_seconds') or candidate.get('duration_seconds') or 0)
    except (TypeError, ValueError):
        return None, f'Candidate {candidate_id} has invalid expected_travel_seconds.'

    points = _route_coordinate_points(candidate.get('coordinates') or [])
    warnings = []
    if distance_meters <= 0:
        warnings.append('distance_meters is missing or zero')
    if duration_seconds <= 0:
        warnings.append('expected_travel_seconds is missing or zero')
    if len(points) < 2:
        warnings.append('coordinates are missing or insufficient for toll geofence analysis')

    route = {
        'candidate_id': candidate_id,
        'route_id': candidate_id,
        'route_set': candidate.get('source_preference') or '',
        'source_preference': candidate.get('source_preference') or '',
        'route_name': candidate.get('route_name') or '',
        'distance_meters': distance_meters,
        'distance_text': _format_route_distance(distance_meters),
        'duration_seconds': duration_seconds,
        'duration_text': _format_route_duration(duration_seconds),
        'apple_has_tolls': bool(candidate.get('apple_has_tolls')),
        'apple_has_highways': bool(candidate.get('apple_has_highways')),
        'coordinate_count': len(points),
        # Keep all MapKit polyline points server-side during evaluation. Do not
        # simplify before toll geofence detection, because small geofences can
        # be missed by aggressive geometry reduction.
        'coordinates': points,
        'warnings': warnings,
    }
    return route, ''


def _route_operating_cost(route):
    costs = route.get('cost_analysis') or {}
    return round((costs.get('fuel_cost') or 0) + (costs.get('driver_cost') or 0), 2)


def _route_evaluation_payload(route):
    costs = route.get('cost_analysis') or {}
    return {
        'candidate_id': route.get('candidate_id'),
        'truck_toll_cost': costs.get('toll_cost') or 0.0,
        'estimated_operating_cost': _route_operating_cost(route),
        'estimated_total_cost': costs.get('total_cost') or 0.0,
        'toll_facilities': [
            {
                'name': toll.get('code') or '',
                'cost': toll.get('amount') or 0.0,
            }
            for toll in costs.get('tolls') or []
        ],
    }


def _route_recommendation_payload(selected_route, evaluated_candidates):
    selected_costs = selected_route.get('cost_analysis') or {}
    standard_routes = [
        route for route in evaluated_candidates
        if (route.get('source_preference') or '').lower() == 'standard'
    ]
    comparison_route = standard_routes[0] if standard_routes else None
    if comparison_route is None:
        comparison_route = next(
            (route for route in evaluated_candidates if route.get('candidate_id') != selected_route.get('candidate_id')),
            selected_route,
        )
    comparison_costs = comparison_route.get('cost_analysis') or {}

    toll_savings = round((comparison_costs.get('toll_cost') or 0) - (selected_costs.get('toll_cost') or 0), 2)
    additional_distance = int(round((selected_route.get('distance_meters') or 0) - (comparison_route.get('distance_meters') or 0)))
    additional_seconds = int(round((selected_route.get('duration_seconds') or 0) - (comparison_route.get('duration_seconds') or 0)))
    additional_operating = round(_route_operating_cost(selected_route) - _route_operating_cost(comparison_route), 2)
    net_savings = round((comparison_costs.get('total_cost') or 0) - (selected_costs.get('total_cost') or 0), 2)

    if selected_route.get('candidate_id') == comparison_route.get('candidate_id'):
        reason = f"Lowest calculated total cost is ${selected_costs.get('total_cost', 0):.2f}."
    elif toll_savings > 0 and additional_seconds > 0:
        reason = f"Avoids ${toll_savings:.2f} in truck tolls for {round(additional_seconds / 60)} additional minutes."
    elif toll_savings > 0:
        reason = f"Avoids ${toll_savings:.2f} in truck tolls."
    else:
        reason = f"Lowest calculated total cost is ${selected_costs.get('total_cost', 0):.2f}."

    return {
        'route_name': selected_route.get('route_name') or '',
        'reason': reason,
        'truck_toll_cost': selected_costs.get('toll_cost') or 0.0,
        'toll_savings': toll_savings,
        'additional_distance_meters': additional_distance,
        'additional_travel_seconds': additional_seconds,
        'estimated_additional_operating_cost': additional_operating,
        'estimated_net_savings': net_savings,
    }


@api_bp.route('/api/driver/route/evaluate', methods=['POST'])
@jwt_required()
def driver_route_evaluate():
    _current_user = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    candidates = data.get('candidates') or []
    if not isinstance(candidates, list) or not candidates:
        return jsonify({
            'success': False,
            'error': 'At least one route candidate is required.',
        }), 400

    cost_inputs = _route_cost_inputs()
    if cost_inputs is None:
        return jsonify({
            'success': False,
            'error': 'No Quoteinput pricing row found for route cost analysis.',
        }), 500

    evaluated_candidates = []
    rejected_candidates = []
    for index, candidate in enumerate(candidates):
        route, error = _normalize_ios_route_candidate(candidate, index)
        if error:
            rejected_candidates.append({
                'candidate_index': index,
                'error': error,
            })
            continue
        evaluated_candidates.append(_attach_route_cost(route, cost_inputs))

    favored_route, selection_reason = _choose_favored_route(evaluated_candidates, [])
    if favored_route is None:
        return jsonify({
            'success': False,
            'request_id': data.get('request_id'),
            'error': 'No route candidates could be evaluated.',
            'rejected_candidates': rejected_candidates,
        }), 400

    # Avoid sending the entire polyline back unless the client already has it.
    for route in evaluated_candidates:
        route.pop('coordinates', None)

    favored_payload = dict(favored_route)
    favored_payload.pop('coordinates', None)
    return jsonify({
        'request_id': data.get('request_id'),
        'selected_candidate_id': favored_payload.get('candidate_id'),
        'recommendation': _route_recommendation_payload(favored_payload, evaluated_candidates),
        'evaluations': [_route_evaluation_payload(route) for route in evaluated_candidates],
        'metadata': {
            'success': True,
            'provider': 'apple_mapkit_candidates',
            'selection_reason': selection_reason,
            'departure_at': data.get('departure_at'),
            'truck': data.get('truck'),
            'origin': data.get('origin'),
            'destination': data.get('destination'),
            'cost_inputs': cost_inputs,
            'rejected_candidates': rejected_candidates,
        },
    }), 200


def _fetch_google_routes(origin, destination, route_set, avoid_tolls=False, departure_time=None):
    api_key = _route_api_key()
    if not api_key:
        return [], 'Google route API key is not configured.'

    field_mask = (
        'routes.duration,routes.staticDuration,routes.distanceMeters,routes.description,'
        'routes.polyline.encodedPolyline,routes.travelAdvisory.tollInfo,'
        'routes.legs.steps.distanceMeters,routes.legs.steps.staticDuration,'
        'routes.legs.steps.navigationInstruction,routes.legs.steps.polyline.encodedPolyline'
    )
    try:
        response = requests.post(
            'https://routes.googleapis.com/directions/v2:computeRoutes',
            headers={
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': api_key,
                'X-Goog-FieldMask': field_mask,
            },
            json=_google_routes_payload(origin, destination, avoid_tolls=avoid_tolls, departure_time=departure_time),
            timeout=10,
        )
        if response.status_code >= 400:
            return [], f'Google Routes API returned HTTP {response.status_code}.'
        payload = response.json()
    except Exception as exc:
        return [], f'Google Routes API request failed: {exc}'

    routes = payload.get('routes') or []
    if not routes:
        return [], 'Google Routes API returned no routes.'
    return [_normalize_google_route(route, route_set, index) for index, route in enumerate(routes)], ''


def _choose_favored_route(normal_routes, toll_avoidance_routes):
    candidates = normal_routes + toll_avoidance_routes
    if not candidates:
        return None, 'No candidate route was available.'
    favored = min(
        candidates,
        key=lambda route: (route.get('cost_analysis') or {}).get('total_cost', 999999999),
    )
    cost = (favored.get('cost_analysis') or {}).get('total_cost')
    return favored, f'Lowest calculated route cost: ${cost:.2f}.'


@api_bp.route('/api/driver/truck-route', methods=['POST'])
@api_bp.route('/api/truck/route', methods=['POST'])
@jwt_required()
def driver_truck_route():
    data = request.get_json(silent=True) or {}
    origin, origin_label = _route_point_from_request(
        data,
        ['origin', 'start', 'starting_point', 'from'],
        ['origin_lat', 'start_lat', 'latitude'],
        ['origin_lng', 'origin_lon', 'start_lng', 'start_lon', 'longitude'],
    )
    destination, destination_label = _route_point_from_request(
        data,
        ['destination', 'dest', 'to'],
        ['destination_lat', 'dest_lat'],
        ['destination_lng', 'destination_lon', 'dest_lng', 'dest_lon'],
    )
    if not origin or not destination:
        return jsonify({
            'success': False,
            'error': 'Origin and destination are required. Send either address text or lat/lng coordinates.',
        }), 400

    departure_time = _first_present(data, ['departure_time', 'departureTime'])
    cost_inputs = _route_cost_inputs()
    if cost_inputs is None:
        return jsonify({
            'success': False,
            'error': 'No Quoteinput pricing row found for route cost analysis.',
        }), 500
    normal_routes, normal_error = _fetch_google_routes(origin, destination, 'normal', avoid_tolls=False, departure_time=departure_time)
    toll_avoidance_routes, toll_error = _fetch_google_routes(origin, destination, 'toll_avoidance', avoid_tolls=True, departure_time=departure_time)
    normal_routes = _attach_costs_to_routes(normal_routes, cost_inputs)
    toll_avoidance_routes = _attach_costs_to_routes(toll_avoidance_routes, cost_inputs)
    favored_route, selection_reason = _choose_favored_route(normal_routes, toll_avoidance_routes)

    if favored_route is None:
        return jsonify({
            'success': False,
            'error': 'No truck route candidates could be calculated.',
            'provider_errors': {
                'normal': normal_error,
                'toll_avoidance': toll_error,
            },
        }), 502

    return jsonify({
        'success': True,
        'provider': 'google_routes',
        'travel_mode': 'DRIVE',
        'truck_note': 'Google Routes API does not apply truck-specific restrictions; returned routes are driving routes for local toll analysis.',
        'origin': origin_label,
        'destination': destination_label,
        'cost_inputs': cost_inputs,
        'favored_route': favored_route,
        'selection_reason': selection_reason,
        'candidate_routes': {
            'normal': normal_routes,
            'toll_avoidance': toll_avoidance_routes,
        },
        'provider_errors': {
            'normal': normal_error,
            'toll_avoidance': toll_error,
        },
    }), 200


def _dispatch_route_payload(order, driver_name, data):
    if order is None:
        return None

    origin_log = Driverlog.query.filter(
        Driverlog.Driver == driver_name,
        Driverlog.Clockin.isnot(None),
        Driverlog.Clockout.is_(None)
    ).order_by(Driverlog.Clockin.desc()).first()
    if origin_log is None:
        origin_log = Driverlog.query.filter(
            Driverlog.Driver == driver_name,
            Driverlog.Clockin.isnot(None)
        ).order_by(Driverlog.Clockin.desc()).first()

    origin_coordinates = _first_present(data, ['origin_coordinates', 'gps', 'coordinates'])
    origin_location = _first_present(data, ['origin_location', 'location'])
    if origin_log is not None:
        origin_coordinates = origin_coordinates or origin_log.GPSin
        origin_location = origin_location or origin_log.Locationstart

    destination_address = _clean_route_text(order.Dropblock2 or order.Company2)
    destination_name = _clean_route_text(order.Company2)
    destination_coordinates = _first_present(data, ['destination_coordinates', 'destination_gps'])
    dest_lat = _first_present(data, ['destination_lat', 'dest_lat'])
    dest_lon = _first_present(data, ['destination_lon', 'destination_lng', 'dest_lon', 'dest_lng'])
    if not destination_coordinates and dest_lat not in (None, '') and dest_lon not in (None, ''):
        destination_coordinates = f'{dest_lat},{dest_lon}'

    origin_for_route = origin_coordinates or origin_location
    destination_for_route = destination_coordinates or destination_address
    maps_url = None
    if origin_for_route and destination_for_route:
        maps_url = (
            'https://www.google.com/maps/dir/?api=1'
            f'&origin={quote_plus(origin_for_route)}'
            f'&destination={quote_plus(destination_for_route)}'
        )

    route = {
        'order_id': order.id,
        'jo': order.Jo,
        'container': order.Container,
        'driver': driver_name,
        'truck': order.Truck,
        'origin_location': origin_location,
        'origin_coordinates': origin_coordinates,
        'origin_clockin': origin_log.Clockin.isoformat() if origin_log and origin_log.Clockin else None,
        'destination_name': destination_name,
        'destination_address': destination_address,
        'destination_coordinates': destination_coordinates,
        'maps_url': maps_url,
        'distance_text': None,
        'duration_text': None,
        'provider': None,
        'route_status': 'route_ready' if maps_url else 'missing_origin_or_destination',
    }

    google_route = _google_distance(origin_for_route, destination_for_route)
    if google_route:
        route.update(google_route)
    elif maps_url:
        route['provider'] = 'google_maps_url'
        route['route_status'] = 'map_url_ready_distance_unavailable'

    return route

@api_bp.route('/api/test')
def api_test():
    return {"message": "API blueprint working"}


@api_bp.route('/api/driver/log', methods=['GET', 'POST'])
@jwt_required()
def driver_log_event():
    current_user = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    if request.method == 'GET':
        data = request.args.to_dict()

    udat, driver_name, display_name = _api_driver_identity(data, current_user)
    if not driver_name:
        return jsonify({'error': 'Driver could not be determined from token or request.'}), 400
    driver_aliases = _api_driver_aliases(driver_name, udat)

    if request.method == 'GET':
        log_dt = datetime.datetime.now()
        try:
            if _first_present(data, ['datetime', 'timestamp', 'gps_time', 'log_datetime', 'date', 'Date']):
                log_dt = _parse_driver_log_datetime(data)
        except (TypeError, ValueError):
            return jsonify({
                'error': 'Invalid datetime. Use an ISO value like 2026-08-08T07:30:00.'
            }), 400

        log_date = log_dt.date()
        open_log = Driverlog.query.filter(
            Driverlog.Driver.in_(driver_aliases),
            Driverlog.Clockin.isnot(None),
            Driverlog.Clockout.is_(None)
        ).order_by(Driverlog.Clockin.desc()).first()

        last_log = Driverlog.query.filter(
            Driverlog.Driver.in_(driver_aliases),
            Driverlog.Date == log_date
        ).order_by(Driverlog.Clockin.desc()).first()

        return jsonify({
            'driver': driver_name,
            'display_name': display_name,
            'date': log_date.isoformat(),
            'is_clocked_in': open_log is not None,
            'next_action': 'clock-out' if open_log is not None else 'clock-in',
            'open_log': _driver_log_payload(open_log) if open_log is not None else None,
            'last_log': _driver_log_payload(last_log) if last_log is not None else None,
            'pending_dispatch_assignments': _pending_dispatch_assignments(driver_name),
        }), 200

    log_action = _driver_log_action(data)
    if log_action is None:
        return jsonify({
            'error': 'Missing or invalid clock action. Use action=clock-in or action=clock-out.'
        }), 400

    try:
        log_dt = _parse_driver_log_datetime(data)
    except (TypeError, ValueError):
        return jsonify({
            'error': 'Invalid datetime. Use an ISO value like 2026-08-08T07:30:00.'
        }), 400
    log_date = log_dt.date()
    truck = str(_first_present(data, ['truck', 'Truck', 'unit', 'Unit']))[:45]
    location = _driver_log_location(data, log_action)
    gps_coordinates = _driver_log_coordinates(data)

    if log_action == 'in':
        open_log = Driverlog.query.filter(
            Driverlog.Driver.in_(driver_aliases),
            Driverlog.Clockout.is_(None)
        ).order_by(Driverlog.Clockin.desc()).first()
        if open_log is not None:
            return jsonify({
                'error': 'Driver is already clocked in.',
                'display_name': display_name,
                'log': _driver_log_payload(open_log),
            }), 409

        same_day_logs = Driverlog.query.filter(
            Driverlog.Driver == driver_name,
            Driverlog.Date == log_date
        ).all()
        shift_num = 1
        for row in same_day_logs:
            try:
                shift_num = max(shift_num, int(row.Shift or 0) + 1)
            except (TypeError, ValueError):
                shift_num = max(shift_num, 2)

        row = Driverlog(
            Date=log_date,
            Driver=driver_name,
            GPSin=gps_coordinates,
            GPSout=None,
            Clockin=log_dt,
            Clockout=None,
            Truck=truck,
            Locationstart=location,
            Locationstop=None,
            Shift=str(shift_num),
            Status='1',
        )
        db.session.add(row)
        db.session.commit()
        return jsonify({
            'message': 'Driver clocked in.',
            'display_name': display_name,
            'log': _driver_log_payload(row),
            'pending_dispatch_assignments': _pending_dispatch_assignments(driver_name),
        }), 201

    open_log = Driverlog.query.filter(
        Driverlog.Driver.in_(driver_aliases),
        Driverlog.Clockin.isnot(None),
        Driverlog.Clockout.is_(None)
    ).order_by(Driverlog.Clockin.desc()).first()
    if open_log is None:
        return jsonify({
            'success': False,
            'failure_note': 'Open clock-in information not found for this driver.',
            'driver': driver_name,
            'display_name': display_name,
            'date': log_date.isoformat(),
        }), 404

    open_log.Driver = driver_name
    open_log.Clockout = log_dt
    open_log.GPSout = gps_coordinates
    open_log.Locationstop = location
    if truck and not open_log.Truck:
        open_log.Truck = truck
    open_log.Status = '2'
    db.session.commit()
    return jsonify({
        'message': 'Driver clocked out.',
        'display_name': display_name,
        'log': _driver_log_payload(open_log),
        'pending_dispatch_assignments': _pending_dispatch_assignments(driver_name),
    }), 200


@api_bp.route('/api/driver/dispatch/messages', methods=['GET', 'POST'])
@api_bp.route('/api/driver/dispatch-communications', methods=['GET', 'POST'])
@jwt_required()
def driver_dispatch_messages():
    _ensure_dispatch_driver_message_table()
    current_user = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    if request.method == 'GET':
        data = request.args.to_dict()

    udat, driver_name, display_name = _api_driver_identity(data, current_user)
    if not driver_name:
        return jsonify({'error': 'Driver could not be determined from token or request.'}), 400

    order = _dispatch_order_from_request(data)
    now_dt = datetime.datetime.now()

    if request.method == 'POST':
        message_text = _first_present(data, ['message', 'text', 'body', 'MessageText'])
        if not message_text:
            return jsonify({'error': 'Message text is required.'}), 400

        sender_type = _first_present(data, ['sender_type', 'SenderType'])
        if not sender_type:
            sender_type = 'driver' if (udat is not None and udat.authority == 'driver') else 'dispatch'
        sender_name = _first_present(data, ['sender_name', 'SenderName']) or display_name
        route_payload = data.get('route')
        route_json = json.dumps(route_payload) if isinstance(route_payload, dict) else None

        row = DispatchDriverMessage(
            Co=scac,
            OrderId=order.id if order else None,
            Jo=order.Jo if order else _first_present(data, ['jo', 'Jo']),
            Container=order.Container if order else _first_present(data, ['container', 'Container']),
            Driver=driver_name,
            SenderName=sender_name,
            SenderType=sender_type,
            MessageText=str(message_text),
            CreatedAt=now_dt,
            ReadAt=None,
            Active=1,
            RouteJson=route_json,
        )
        db.session.add(row)
        db.session.commit()
        return jsonify({
            'message': 'Dispatch message saved.',
            'display_name': display_name,
            'dispatch_message': _message_payload(row, display_name),
            'route': route_payload if isinstance(route_payload, dict) else _dispatch_route_payload(order, driver_name, data),
        }), 201

    query = DispatchDriverMessage.query.filter(
        DispatchDriverMessage.Active == 1,
        DispatchDriverMessage.Driver == driver_name,
    )
    if order is not None:
        query = query.filter(DispatchDriverMessage.OrderId == order.id)
    else:
        jo = _first_present(data, ['jo', 'Jo'])
        container = _first_present(data, ['container', 'Container'])
        if jo:
            query = query.filter(DispatchDriverMessage.Jo == jo)
        if container:
            query = query.filter(DispatchDriverMessage.Container == container)

    since_id = _first_present(data, ['since_id', 'since'])
    if since_id:
        try:
            query = query.filter(DispatchDriverMessage.id > int(since_id))
        except (TypeError, ValueError):
            return jsonify({'error': 'since_id must be an integer.'}), 400

    rows = query.order_by(DispatchDriverMessage.CreatedAt, DispatchDriverMessage.id).all()
    message_payloads = [_message_payload(row, display_name) for row in rows]
    pending_assignments = _pending_dispatch_assignments(driver_name)
    route_payload = _dispatch_route_payload(order, driver_name, data)
    if route_payload is None:
        for message in reversed(message_payloads):
            if message.get('route'):
                route_payload = message.get('route')
                break
    if route_payload is None:
        for assignment in reversed(pending_assignments):
            if assignment.get('route'):
                route_payload = assignment.get('route')
                break
    return jsonify({
        'driver': driver_name,
        'display_name': display_name,
        'order': {
            'id': order.id,
            'jo': order.Jo,
            'container': order.Container,
            'customer': order.Shipper,
            'destination_name': order.Company2,
            'destination_address': _clean_route_text(order.Dropblock2),
        } if order else None,
        'route': route_payload,
        'pending_dispatch_assignments': pending_assignments,
        'messages': message_payloads,
    }), 200


@api_bp.route("/api/financial/bill-payment/import", methods=["POST"])
@api_bp.route("/api/financial/import/bill-payment", methods=["POST"])
@jwt_required()
def import_bill_payment():
    current_user = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    response, status_code = import_paid_bill_payload(data, username=current_user)
    return jsonify(response), status_code


@api_bp.route("/api/financial/import/accounts", methods=["GET"])
@jwt_required()
def financial_import_accounts():
    company_code = request.args.get('co') or request.args.get('company_code')
    return jsonify(financial_import_account_options(company_code)), 200


@api_bp.route("/api/financial/import/rules/lookup", methods=["POST"])
@jwt_required()
def financial_import_rule_lookup():
    data = request.get_json(silent=True) or {}
    response, status_code = lookup_financial_import_rule(data)
    return jsonify(response), status_code


@api_bp.route("/upload_pdf", methods=["POST"])
#@jwt_required()
def pdf_upload():
    username = request.form.get("username")
    container_number = request.form.get("container_number")
    file = request.files.get("file")

    print(f'The user uploading this file is: {username} for container {container_number} and file is {file}')


    if not username or not container_number or not file:
        return jsonify({"error": "Missing username, container number, or file"}), 400

    udat = users.query.filter(users.username == username).first()
    if udat is not None:
        utype = udat.authority
    else:
        utype = ''
    odat = Orders.query.filter(Orders.Container == container_number).order_by(Orders.id.desc()).first()
    if odat is not None:
        pcache = odat.D1cache
        if not hasinput(pcache): pcache = 1
        jo = odat.Jo
        filename = f'Proof_{jo}_{container_number}_c{str(pcache)}.pdf'
        outputpath = addpath(tpath('Orders-DrvProof', filename))
        odat.D1cache = pcache + 1
        odat.DrvProof = filename
        if utype == 'driver':
            odat.Driver = udat.name
        db.session.commit()
        file.save(outputpath)
        print(f'Saving file: {file} as {outputpath}')
        return jsonify({
            "message": "Uploaded successfully",
            "file": filename
        })

    else:
        return jsonify({"error": "Container not found in database"}), 400

@api_bp.route("/get_pins_now", methods=["GET"])
#@jwt_required(refresh=True)
def getpinsnow():
    pinid = request.args.get("pinid")
    #scac = request.args.get("scac")

    if not pinid or not scac:
        return {"error": "Missing scac or pinid"}, 400

    queue_dir = "/home/nixonai/tasks"
    queue_file = f"{queue_dir}/task_queue.txt"
    os.makedirs(queue_dir, exist_ok=True)

    job_line = f"{scac}|{pinid}\n"

    with open(queue_file, "a") as f:
        f.write(job_line)

    return {
        "status": "queued",
        "scac": scac,
        "pinid": pinid
    }


@api_bp.route("/pin_task_status", methods=["GET", "POST"])
def pin_task_status():
    pinid = request.args.get("pinid")
    print(f'Reviewing Status for pinid {pinid}')
    pinid = int(pinid)
    pin = db.session.get(Pins, pinid)

    if pin is not None:
        return_note = pin.Notes
        intext = pin.Intext
        outtext = pin.Outtext
        if 'Error' in return_note or 'Pin made' in return_note:
            return jsonify({"pinid": pinid, "message": "Completed", "note": return_note, "intext": intext, "outtext": outtext}), 200
        else:
            return jsonify({"pinid": pinid, "message": "NeedPin", "note": return_note, "intext": intext, "outtext": outtext}), 200
    else:
        return jsonify({"pinid": pinid, "message": "Missing task_id", "note": "Pin Not in Database", "intext": "Unknown", "outtext": "Unknown"}), 400



@api_bp.route("/get_pdf_for_container", methods=["GET"])
#@jwt_required()
def pdf_download():
    container_number = request.args.get("container_number")
    #file = request.files.get("file")
    print(f'Getting pdf files for container {container_number}')

    if not container_number:
        return jsonify({"error": "Missing container number or file"}), 400


    odat = Orders.query.filter(Orders.Container == container_number).order_by(Orders.id.desc()).first()
    if odat is not None:
        fileM = odat.Manifest
        if not fileM:
            print('There is no Manifest')
            filename = odat.Source
            outputpath = addpath(tpath('Orders-Source', filename))
        else:
            print('Using the Manifest')
            filename = odat.Manifest
            outputpath = addpath(tpath('Orders-Manifest', filename))

        return send_file(outputpath, mimetype="application/pdf")


    else:
        return jsonify({"error": "Container not found in database"}), 400


@api_bp.route('/get_existing_pins', methods=['GET', 'PUT', 'POST'])
@jwt_required()
def get_existing_pins():
    current_user = get_jwt_identity()
    print(f'user: {current_user}')
    maker = f'API-{current_user}'

    if request.method == 'GET':
        print(f'This is a GET of the existing pins for maker {maker}')
        #data_needed = request.args.get('data_needed')
        #print(f'data_needed: {data_needed}')
        #data = request.get_json()
        #print(f'data: {data}')

        lb_days = 60
        today = now.date()
        lbdate = today - timedelta(days=lb_days)
        active_date = today + timedelta(days=10)
        fd = '1900-01-01'
        print(f'Looking back to this date: {lbdate}')
        pdata = Pins.query.filter(Pins.Maker == maker).all()
        ret_data = []
        for pdat in pdata:
            havepin = pdat.OutPin
            if havepin == '0':
                mess = 'NeedPin'
            else:
                mess = 'HavePin'
            ret_data.append({'message': mess,'pinid': pdat.id, 'intext': pdat.Intext, 'outtext' : pdat.Outtext, 'note': pdat.Notes})
        print(f'return data is: {ret_data}')
        return ret_data


@api_bp.route('/delete_pin', methods=['GET', 'PUT', 'POST'])
@jwt_required()
def delete_pin():
    current_user = get_jwt_identity()
    print(f'user: {current_user}')

    if request.method == 'POST':
        print('This is a POST')
        pinid = request.args.get('pinid')
        print(f'pinid: {pinid}')
        pinid = int(pinid)
        pin = db.session.get(Pins, pinid)
        if pin:
            db.session.delete(pin)
            db.session.commit()
            return 'Success', 200
        else:
            return 'Already Deleted', 200

    return 'Failed', 400


@api_bp.route('/get_api_data', methods=['GET', 'PUT', 'POST'])
@jwt_required()
def handle_data():
    current_user = get_jwt_identity()
    print(f'user: {current_user}')

    if request.method == 'PUT':
        print('This is a put')
        data_needed = request.args.get('data_needed')
        print(f'data_needed: {data_needed}')

        if 'test1' in data_needed:
            print('made it to test1')
            data = request.get_json()
            print("Data received successfully:", data)
            old_data = [{'id':1,'container':'CAAU8649700','shipper':'one'},
                        {'id':2,'container':'XXXX8649700','shipper':'two'}]
            # Update the changes
            print(data['id'])
            if data:
                changeid = data['id']
                old_match = [item for item in old_data if item['id'] == changeid]
                con1 = old_match[0]['container']
                con2 = data['container']
                ship1 = old_match[0]['shipper']
                ship2 = data['shipper']
                print(con1, con2, ship1, ship2)
                if con1 == con2:
                    print('no update for containers')
                if ship1 == ship2:
                    print('no update for shipper')
                else:
                    print(f'Updating database for shipper from {ship1} to {ship2}')


            if not data:
                return jsonify({'error':'No data received'}), 400

            return jsonify({'message': 'Data received', 'data':data}), 200


    elif request.method == 'GET':
        data_needed = request.args.get('data_needed')
        #data_needed = 'api_test_two'
        print(f'This is a get request for data_needed:{data_needed}:')

        arglist = request.args.get('arglist')
        print(f'Was able to get the payload data for arglist:{arglist}:')

        data_return = api_call(scac, now, data_needed, arglist)
        return jsonify(data_return)

    else:
        return []

@api_bp.route('/make_pin_data', methods=['GET', 'PUT', 'POST'])
@jwt_required()
def make_pin_data():
    current_user = get_jwt_identity()
    print(f'user: {current_user}')


    if request.method == 'POST':
        print('This is a POST')
        data_needed = request.args.get('data_needed')
        print(f'data_needed: {data_needed}')
        data = request.get_json()
        print(f'data: {data}')

        lb_days = 60
        today = now.date()
        lbdate = today - timedelta(days=lb_days)
        active_date = today + timedelta(days=10)

        driver = data['driver']
        unit = data['truck']
        ingate = data['ingate']
        outgate = data['outgate']
        pintime = data['pintime']
        pindate = data['pindate']
        pintime = pintime.replace('6:00-7:00','06:00-07:00').replace('7:00-8:00','07:00-08:00').replace('8:00-9:00','08:00-09:00').replace('9:00-10:00','09:00-10:00')

        print(f' The pin date requested is {pindate} and timeslot {pintime}')
        pindate_obj = datetime.datetime.strptime(pindate, "%Y-%m-%d").date()
        print(f' The pin date object requested is {pindate_obj}')

        try:
            chassis = data['chassis']
        except:
            chassis = ''

        vdat = Vehicles.query.filter(Vehicles.Unit == unit).first()
        if vdat is not None:
            tag = vdat.Plate
        ddat = Drivers.query.filter(Drivers.Name == driver).first()
        if ddat is not None:
            phone = ddat.Phone
        indat = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Container == ingate)).first()
        if indat is not None:
            incon = indat.Container
            inchas = indat.Chassis
            contype = indat.Type

            ht = indat.HaulType
            ctext = ''
            if '45' in contype and '9' in contype: ctext = '45HC'
            if '40' in contype and '9' in contype: ctext = '40HC'
            if '40' in contype and '8' in contype: ctext = '40STD'
            if '45' in contype and '8' in contype: ctext = '45STD'
            if '20' in contype: ctext = '20'
            if 'R' in contype: ctext = ctext + ' Reefer'
            if 'U' in contype: ctext = ctext + ' OpenTop'

            address = indat.Dropblock2
            adata, backup = get_address_details(address)
            try:
                city = adata['city']
            except:
                city = backup

            if city == 'Baltimore':
                citiline = indat.Shipper
                citiline = citiline.split()
                city = citiline[0]

            if not hasinput(city):
                citiline = indat.Shipper
                citiline = citiline.split()
                city = citiline[0]

            if 'Export' in ht:
                if hasinput(indat.BOL):
                    inbook = indat.BOL
                else:
                    inbook = indat.Booking
                inbook = inbook.split('-', 1)[0]
                intext = f'Load In: *{inbook}  {incon}* ({ctext} {city})'

            if 'Import' in ht:
                intext = f'Empty In: *{incon}* ({ctext} {city})'
                inbook = None

        else:
            incon = None
            inbook = None
            inchas = chassis
            intext = 'Bare Chassis In'

        outdat = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Container == outgate)).first()
        if outdat is not None:
            outcon = outdat.Container
            outbook = outdat.Booking
        else:
            #Try matching on booking, cust be an empty out
            outdat = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Booking == outgate)).first()
            if outdat is not None:
                outcon = outdat.Container
                outbook = outdat.Booking
            else:
                outcon = None
                outbook = None
        if outdat is not None:
            outchas = inchas
            contype = outdat.Type

            ht = outdat.HaulType
            ctext = ''
            if '45' in contype and '9' in contype: ctext = '45HC'
            if '40' in contype and '9' in contype: ctext = '40HC'
            if '40' in contype and '8' in contype: ctext = '40STD'
            if '45' in contype and '8' in contype: ctext = '45STD'
            if '20' in contype: ctext = '20'
            if 'R' in contype: ctext = ctext + ' Reefer'
            if 'U' in contype: ctext = ctext + ' OpenTop'

            address = outdat.Dropblock2
            adata, backup = get_address_details(address)
            try:
                city = adata['city']
            except:
                city = backup

            if city == 'Baltimore':
                citiline = outdat.Shipper
                citiline = citiline.split()
                city = citiline[0]

            if not hasinput(city):
                citiline = outdat.Shipper
                citiline = citiline.split()
                city = citiline[0]

            if 'Export' in ht:
                outbook = outdat.Booking
                outbook = outbook.split('-', 1)[0]
                outtext = f'Empty Out: *{outbook}* ({ctext} {city})'

            if 'Import' in ht:
                try:
                    rel4 = outdat.Booking[-4:]
                except:
                    rel4 = outdat.Booking
                outtext = f'Load Out: *{rel4}  {outcon}* ({ctext} {city})'

        else:
            outcon = None
            outbook = None
            outchas = inchas
            outtext = 'Nothing Out'
        #Add this data to the pin database for today:
        #today = now.date()
        inpin = '0'
        outpin = '0'
        if inchas == None: inchas = 'OSLM007'
        # Now get the intext and outtext:
        #add_day = 2 # Need to make this an api argument
        #thisdate = today + timedelta(days=add_day)
        if driver is not None and unit is not None and inchas is not None:
            note = f'Will get pin for {driver} in unit {unit} using chassis {inchas} for {pindate_obj} {pintime}'

        input = Pins(Date=pindate_obj, Driver=driver, InBook=inbook, InCon=incon, InChas=inchas, InPin=inpin,
                     OutBook=outbook, OutCon=outcon, OutChas=outchas, OutPin=outpin, Unit=unit, Tag=tag, Phone=phone,
                     Timeslot=pintime, Intext=intext, Outtext=outtext, Notes=note, Active=0, Maker=f'API-{current_user}')
        db.session.add(input)
        db.session.commit()
        print(f'The new row has id {input.id}')

        #pdat = Pins.query.get(input.id)

        #pdat = Pins.query.filter(Pins.InCon == incon).first()
        #pinid = pdat.id

        return jsonify({'message': 'NeedPin', 'pinid': input.id, 'intext': intext, 'outtext' : outtext, 'note': note}), 200

    else:
        return jsonify({'error': 'No data received'}), 400
