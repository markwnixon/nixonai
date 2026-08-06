from webapp import create_app
import webapp.routes as routes
import webapp.dispatch_kanban as dispatch_kanban
from webapp.dispatch_kanban import apply_delivery_date_to_order, derived_workflow_status
import datetime


def test_dispatch_kanban_jobs_endpoint(monkeypatch):
    app = create_app()
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True

    def fake_jobs(filters=None):
        assert filters['driver'] == 'Driver A'
        return {
            'columns': [{
                'key': 'assigned',
                'label': 'Assigned',
                'jobs': [{'id': 1, 'container': 'CONT123'}],
            }],
        }

    monkeypatch.setattr(routes, 'kanban_jobs', fake_jobs)
    with app.test_client() as client:
        response = client.get('/api/dispatch/kanban/jobs?driver=Driver%20A')

    assert response.status_code == 200
    assert response.get_json()['columns'][0]['jobs'][0]['container'] == 'CONT123'


def test_dispatch_kanban_options_endpoint(monkeypatch):
    app = create_app()
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True

    monkeypatch.setattr(routes, 'kanban_options', lambda: {
        'columns': [{'key': 'new_orders', 'label': 'New Orders'}],
        'drivers': [],
        'trucks': [],
    })
    with app.test_client() as client:
        response = client.get('/api/dispatch/kanban/options')

    assert response.status_code == 200
    assert response.get_json()['columns'][0]['key'] == 'new_orders'


def test_dispatch_kanban_move_endpoint(monkeypatch):
    app = create_app()
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True

    def fake_move(order_id, workflow_status, username=None, override_pin=False, reason=None):
        assert order_id == 42
        assert workflow_status == 'assigned'
        assert username == 'dispatch'
        assert override_pin is False
        return {'ok': True, 'job': {'id': order_id, 'workflow_status': workflow_status}}, 200

    monkeypatch.setattr(routes, 'kanban_move_job', fake_move)
    with app.test_client() as client:
        response = client.post('/api/dispatch/kanban/job/42/move', json={'workflow_status': 'assigned'})

    assert response.status_code == 200
    assert response.get_json()['job']['workflow_status'] == 'assigned'


def test_kanban_returned_without_proof_mapping_is_completed():
    class OrderStub:
        Status = ''
        HaulType = 'Import'
        Hstat = 2
        Istat = 0
        Driver = ''
        Container = 'CONT123'
        Booking = ''
        Delivery = ''
        Time3 = ''
        Date6 = None
        Proof = ''
        Proof2 = ''
        DrvProof = ''
        DelStat = 0
        Date = None
        Date2 = None
        Date3 = None

    assert derived_workflow_status(OrderStub(), state=None, pin=None) == 'completed'

    OrderStub.Istat = 1
    assert derived_workflow_status(OrderStub(), state=None, pin=None) == 'completed'


def test_kanban_returned_with_none_required_maps_to_invoice_ready():
    class OrderStub:
        Status = ''
        HaulType = 'Dray Import DP'
        Hstat = 2
        Istat = 0
        Driver = ''
        Container = 'CONT123'
        Booking = ''
        Delivery = ''
        HoldType = ''
        Time3 = ''
        Date6 = None
        Proof = 'None Required'
        Proof2 = ''
        DrvProof = ''
        DelStat = 0
        Date = None
        Date2 = None
        Date3 = None

    assert derived_workflow_status(OrderStub(), state=None, pin=None) == 'invoice_ready'


def test_kanban_future_container_maps_to_upcoming_delivery(monkeypatch):
    monkeypatch.setattr(dispatch_kanban, 'pin_row_for_order', lambda order: None)

    class OrderStub:
        Status = ''
        HaulType = 'Import'
        Hstat = 0
        Istat = 0
        Driver = ''
        Container = 'CONT123'
        Booking = ''
        Delivery = 'Hard Time'
        Time3 = '08:00'
        Date6 = None
        Proof = ''
        Proof2 = ''
        DrvProof = ''
        DelStat = 0
        Date = None
        Date2 = None
        Date3 = datetime.datetime.combine(
            datetime.date.today() + datetime.timedelta(days=3),
            datetime.time.min,
        )

    assert derived_workflow_status(OrderStub(), state=None, pin=None) == 'upcoming_deliveries'

    OrderStub.Date3 = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    assert derived_workflow_status(OrderStub(), state=None, pin=None) == 'port_today'
    assert derived_workflow_status(OrderStub(), state={'WorkflowStatus': 'needs_pin'}, pin=None) == 'port_today'


def test_kanban_driver_assigned_does_not_map_to_pin_assigned(monkeypatch):
    monkeypatch.setattr(dispatch_kanban, 'pin_row_for_order', lambda order: None)

    class OrderStub:
        Status = ''
        HaulType = 'Import'
        Hstat = 0
        Istat = 0
        Driver = 'Driver A'
        Container = 'CONT123'
        Booking = ''
        Delivery = ''
        Time3 = ''
        Date6 = None
        Proof = ''
        Proof2 = ''
        DrvProof = ''
        DelStat = 0
        Date = None
        Date2 = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        Date3 = None

    assert derived_workflow_status(OrderStub(), state=None, pin=None) == 'new_orders'
    assert derived_workflow_status(OrderStub(), state={'WorkflowStatus': 'assigned'}, pin=None) == 'new_orders'


def test_kanban_pin_row_maps_to_pin_assigned(monkeypatch):
    class PinStub:
        Date = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        InPin = '1234'
        OutPin = ''
        InBook = ''
        OutBook = ''

    class OrderStub:
        Status = ''
        HaulType = 'Import'
        Hstat = 0
        Istat = 0
        Driver = ''
        Container = 'CONT123'
        Booking = ''
        Delivery = 'Hard Time'
        Time3 = '08:00'
        Date6 = None
        Proof = ''
        Proof2 = ''
        DrvProof = ''
        DelStat = 0
        Date = None
        Date2 = None
        Date3 = datetime.datetime.combine(datetime.date.today(), datetime.time.min)

    assert derived_workflow_status(OrderStub(), state=None, pin=PinStub()) == 'pin_assigned'


def test_kanban_old_pin_row_does_not_map_to_pin_assigned(monkeypatch):
    class PinStub:
        Date = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=1), datetime.time.min)
        InPin = '1234'
        OutPin = ''
        InBook = ''
        OutBook = ''

    class OrderStub:
        Status = ''
        HaulType = 'Import'
        Hstat = 0
        Istat = 0
        Driver = ''
        Container = 'CONT123'
        Booking = ''
        Delivery = 'Hard Time'
        Time3 = '08:00'
        Date6 = None
        Proof = ''
        Proof2 = ''
        DrvProof = ''
        DelStat = 0
        Date = None
        Date2 = None
        Date3 = datetime.datetime.combine(datetime.date.today(), datetime.time.min)

    assert derived_workflow_status(OrderStub(), state=None, pin=PinStub()) == 'port_today'


def test_kanban_current_pin_does_not_override_physical_progress(monkeypatch):
    class PinStub:
        Date = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        InPin = '1234'
        OutPin = ''
        InBook = ''
        OutBook = ''

    class OrderStub:
        Status = ''
        HaulType = 'Import'
        Hstat = 1
        Istat = 0
        Driver = ''
        Container = 'CONT123'
        Booking = ''
        Delivery = 'Hard Time'
        Time3 = '08:00'
        Date6 = None
        Proof = ''
        Proof2 = ''
        DrvProof = ''
        DelStat = 0
        Date = None
        Date2 = None
        Date3 = datetime.datetime.combine(datetime.date.today(), datetime.time.min)

    assert derived_workflow_status(OrderStub(), state=None, pin=PinStub()) == 'in_progress'


def test_kanban_future_import_ship_arrival_maps_to_new_orders(monkeypatch):
    monkeypatch.setattr(dispatch_kanban, 'pin_row_for_order', lambda order: None)

    class OrderStub:
        Status = ''
        HaulType = 'Import'
        Hstat = 0
        Istat = 0
        Driver = ''
        Container = ''
        Booking = ''
        Delivery = ''
        Time3 = ''
        Date6 = datetime.datetime.combine(
            dispatch_kanban.next_week_start(),
            datetime.time.min,
        )
        Proof = ''
        Proof2 = ''
        DrvProof = ''
        DelStat = 0
        Date = None
        Date2 = None
        Date3 = None

    assert derived_workflow_status(OrderStub(), state=None, pin=None) == 'new_orders'


def test_kanban_text_hold_without_hold_type_does_not_map_to_on_call(monkeypatch):
    monkeypatch.setattr(dispatch_kanban, 'pin_row_for_order', lambda order: None)

    class OrderStub:
        Status = 'Exam hold'
        HaulType = 'Import'
        Hstat = 0
        Istat = 0
        Driver = ''
        Container = 'CONT123'
        Booking = ''
        HoldType = ''
        Delivery = 'Upon Notice'
        Time3 = ''
        Date6 = None
        Proof = ''
        Proof2 = ''
        DrvProof = ''
        DelStat = 0
        Date = None
        Date2 = None
        Date3 = datetime.datetime.combine(datetime.date.today(), datetime.time.min)

    assert derived_workflow_status(OrderStub(), state=None, pin=None) == 'port_today'


def test_kanban_structured_hold_type_maps_to_on_call(monkeypatch):
    monkeypatch.setattr(dispatch_kanban, 'pin_row_for_order', lambda order: None)

    class OrderStub:
        Status = ''
        HaulType = 'Import'
        Hstat = 0
        Istat = 0
        Driver = ''
        Container = 'CONT123'
        Booking = ''
        Delivery = 'Hard Time'
        HoldType = 'Line Hold'
        Time3 = '08:00'
        Date6 = None
        Proof = ''
        Proof2 = ''
        DrvProof = ''
        DelStat = 0
        Date = None
        Date2 = None
        Date3 = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=2), datetime.time.min)

    assert derived_workflow_status(OrderStub(), state=None, pin=None) == 'on_call'


def test_kanban_drop_pick_maps_to_drop_pick_before_in_progress(monkeypatch):
    monkeypatch.setattr(dispatch_kanban, 'pin_row_for_order', lambda order: None)

    class OrderStub:
        Status = ''
        HaulType = 'Dray Import DP'
        Hstat = 1
        Istat = 0
        Driver = ''
        Container = 'CONT123'
        Booking = ''
        Delivery = 'Hard Time'
        HoldType = ''
        Time3 = '08:00'
        Date6 = None
        Proof = ''
        Proof2 = ''
        DrvProof = ''
        DelStat = 0
        Date = None
        Date2 = None
        Date3 = datetime.datetime.combine(datetime.date.today(), datetime.time.min)

    assert derived_workflow_status(OrderStub(), state=None, pin=None) == 'drop_pick'


def test_kanban_delivery_proof_maps_to_delivered(monkeypatch):
    monkeypatch.setattr(dispatch_kanban, 'pin_row_for_order', lambda order: None)

    class OrderStub:
        Status = ''
        HaulType = 'Import'
        Hstat = 0
        Istat = 0
        Driver = ''
        Container = 'CONT123'
        Booking = ''
        Delivery = ''
        Time3 = ''
        Date6 = None
        Proof = 'pod.pdf'
        Proof2 = ''
        DrvProof = ''
        DelStat = 0
        Date = None
        Date2 = None
        Date3 = None

    assert derived_workflow_status(OrderStub(), state=None, pin=None) == 'delivered'


def test_kanban_manual_delivered_state_is_honored(monkeypatch):
    monkeypatch.setattr(dispatch_kanban, 'pin_row_for_order', lambda order: None)

    class OrderStub:
        Status = ''
        HaulType = 'Import'
        Hstat = 0
        Istat = 0
        Driver = ''
        Container = 'CONT123'
        Booking = ''
        Delivery = 'Hard Time'
        HoldType = ''
        Time3 = '08:00'
        Date6 = None
        Proof = ''
        Proof2 = ''
        DrvProof = ''
        DelStat = 0
        Date = None
        Date2 = None
        Date3 = datetime.datetime.combine(datetime.date.today(), datetime.time.min)

    assert derived_workflow_status(
        OrderStub(),
        state={'WorkflowStatus': 'delivered'},
        pin=None,
    ) == 'delivered'


def test_apply_delivery_date_sets_pull_and_return_same_day():
    class OrderStub:
        Date = None
        Date2 = None
        Date3 = None
        Time3 = None

    order = OrderStub()
    delivery_date = datetime.date.today() + datetime.timedelta(days=2)
    apply_delivery_date_to_order(order, delivery_date, '08:00')

    expected = datetime.datetime.combine(delivery_date, datetime.time.min)
    assert order.Date == expected
    assert order.Date2 == expected
    assert order.Date3 == expected
    assert order.Time3 == '08:00'
