import datetime
import importlib.util
import json
import plistlib
import sys
from pathlib import Path

from flask import Flask
from flask_jwt_extended import create_access_token

from webapp.bot.routes import bot_bp
from webapp.chassis_locations import age_label, chassis_location_rows
from webapp.extensions import db, jwt
from webapp.models import ChassisLocationObservation, Vehicles


COLLECTOR_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'airtag_chassis_collector.py'
spec = importlib.util.spec_from_file_location('airtag_chassis_collector', COLLECTOR_PATH)
collector = importlib.util.module_from_spec(spec)
sys.modules['airtag_chassis_collector'] = collector
spec.loader.exec_module(collector)


def make_app():
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY='test-secret-key-that-is-at-least-32-bytes-long',
    )
    db.init_app(app)
    jwt.init_app(app)
    app.register_blueprint(bot_bp)
    return app


def seed_chassis():
    Vehicles.__table__.create(bind=db.engine, checkfirst=True)
    ChassisLocationObservation.__table__.create(bind=db.engine, checkfirst=True)
    db.session.execute(Vehicles.__table__.insert().values(
        Unit='OSLM001', Title='Chassis OSLM001', Type='Chassis', Active=1,
    ))
    db.session.commit()


def token_for(app, scopes):
    with app.app_context():
        return create_access_token(identity='collector', additional_claims={
            'token_type': 'bot', 'scopes': scopes,
        })


def test_collector_reads_plist_and_maps_chassis(tmp_path):
    cache_path = tmp_path / 'Items.data'
    cache_path.write_bytes(plistlib.dumps([{
        'name': 'Chassis OSLM001',
        'location': {
            'latitude': 39.2904,
            'longitude': -76.6122,
            'timeStamp': 1791634500000,
        },
    }]))

    items = collector.extract_items(collector.load_cache(cache_path))
    observations, missing = collector.build_observations(items, {'OSLM001': 'Chassis OSLM001'})

    assert missing == []
    assert observations[0]['chassis_id'] == 'OSLM001'
    assert observations[0]['latitude'] == 39.2904
    assert observations[0]['observed_at'].endswith('Z')


def test_collector_reads_find_my_json_cache(tmp_path):
    cache_path = tmp_path / 'Items.data'
    cache_path.write_text(json.dumps([{
        'name': 'Chassis OSLM001',
        'location': {
            'latitude': 39.2904,
            'longitude': -76.6122,
            'timeStamp': 1791634500000,
        },
    }]))

    items = collector.extract_items(collector.load_cache(cache_path))

    assert items['Chassis OSLM001']['longitude'] == -76.6122
    assert items['Chassis OSLM001']['observed_at'].endswith('Z')


def test_chassis_location_endpoint_authenticates_validates_and_deduplicates():
    app = make_app()
    with app.app_context():
        seed_chassis()
    token = token_for(app, ['write:orders'])
    payload = {'observations': [{
        'chassis_id': 'OSLM001',
        'airtag_name': 'Chassis OSLM001',
        'latitude': 39.2904,
        'longitude': -76.6122,
        'observed_at': '2026-10-10T12:15:00Z',
    }]}

    first = app.test_client().post('/bot/chassis/locations', json=payload, headers={
        'Authorization': f'Bearer {token}',
    })
    second = app.test_client().post('/bot/chassis/locations', json=payload, headers={
        'Authorization': f'Bearer {token}',
    })

    assert first.status_code == 200
    assert first.get_json()['inserted'] == 1
    assert second.get_json()['duplicates'] == 1


def test_chassis_location_endpoint_rejects_crossed_tag_mapping():
    app = make_app()
    with app.app_context():
        seed_chassis()
    token = token_for(app, ['write:orders'])
    response = app.test_client().post('/bot/chassis/locations', json={'observations': [{
        'chassis_id': 'OSLM001',
        'airtag_name': 'Wrong tag',
        'latitude': 39.29,
        'longitude': -76.61,
        'observed_at': '2026-10-10T12:15:00Z',
    }]}, headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 400
    assert 'not assigned' in response.get_json()['error']


def test_blank_title_disables_chassis_tracking_and_hides_it_from_page():
    app = make_app()
    with app.app_context():
        seed_chassis()
        db.session.execute(Vehicles.__table__.insert().values(
            Unit='OSLM002', Title='', Type='Chassis', Active=1,
        ))
        db.session.commit()
    token = token_for(app, ['write:orders'])
    response = app.test_client().post('/bot/chassis/locations', json={'observations': [{
        'chassis_id': 'OSLM002',
        'airtag_name': 'Unassigned AirTag',
        'latitude': 39.29,
        'longitude': -76.61,
        'observed_at': '2026-10-10T12:15:00Z',
    }]}, headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 400
    assert 'not configured' in response.get_json()['error']
    with app.app_context():
        assert [row['vehicle'].Unit for row in chassis_location_rows()] == ['OSLM001']


def test_age_labels_are_operationally_readable():
    assert age_label(None) == 'No location received'
    assert age_label(35) == 'Last seen 35 minutes ago'
    assert age_label(120) == 'Last seen 2 hours ago'
    assert age_label(2880) == 'Last seen 2 days ago'
