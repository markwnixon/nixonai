from webapp import create_app
import webapp.routes as routes


def test_dispatch_calendar_events_endpoint(monkeypatch):
    app = create_app()
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True

    def fake_events(start=None, end=None, filters=None):
        assert filters['driver'] == 'Driver A'
        return [{
            'id': '1',
            'title': 'CONT123 | Customer',
            'start': '2026-06-22T08:00:00',
            'extendedProps': {'container': 'CONT123'},
        }]

    monkeypatch.setattr(routes, 'calendar_events', fake_events)
    with app.test_client() as client:
        response = client.get('/api/dispatch/calendar/events?driver=Driver%20A')

    assert response.status_code == 200
    assert response.get_json()[0]['extendedProps']['container'] == 'CONT123'


def test_dispatch_calendar_capacity_endpoint(monkeypatch):
    app = create_app()
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True

    monkeypatch.setattr(routes, 'capacity_summary', lambda start=None, end=None, filters=None: [{
        'date': '2026-06-22',
        'scheduled': 4,
        'capacity': 3,
        'over_capacity': True,
    }])
    with app.test_client() as client:
        response = client.get('/api/dispatch/calendar/capacity')

    assert response.status_code == 200
    assert response.get_json()[0]['over_capacity'] is True
