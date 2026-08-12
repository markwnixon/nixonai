from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from webapp.extensions import db
from webapp.models import Orders, users, Pins, Vehicles, Drivers, Driverlog, DispatchDriverMessage, DispatchDriverAssignment
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
