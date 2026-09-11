import datetime

from webapp.bot.routes import scheduler_order_payload


def test_scheduler_order_payload_includes_appointment_and_port_constraints():
    class Order:
        id = 42
        Jo = 'E4200'
        HaulType = 'Dray Import'
        Status = 'Active'
        DisStatus = 'upcoming_deliveries'
        Company = 'Seagirt'
        Container = 'ABCD1234567'
        Type = "20' GP"
        Booking = '123456'
        BOL = 'BOL123'
        Shipper = 'Example Customer'
        Company2 = 'Example Warehouse'
        Dropblock2 = 'Baltimore, MD'
        Date3 = datetime.datetime(2026, 9, 15)
        Time3 = '08:30'
        Date = None
        Date2 = None
        Date4 = datetime.datetime(2026, 9, 14)
        Date5 = datetime.datetime(2026, 9, 16)
        Date6 = datetime.datetime(2026, 9, 13)
        Date7 = datetime.datetime(2026, 9, 18)
        Date8 = None
        HoldType = None
        Hstat = 0
        Driver = ''
        Truck = ''
        Description = 'Call before delivery'

    payload = scheduler_order_payload(Order())

    assert payload['delivery_date'] == '2026-09-15T00:00:00'
    assert payload['delivery_time'] == '08:30'
    assert payload['port_window_start'] == '2026-09-14T00:00:00'
    assert payload['port_window_end'] == '2026-09-16T00:00:00'
    assert payload['container_type'] == "20' GP"
