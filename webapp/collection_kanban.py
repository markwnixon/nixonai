import datetime
import smtplib
from decimal import Decimal, InvalidOperation
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

from sqlalchemy import and_, or_

from webapp.CCC_system_setup import passwords, websites
from webapp.CCC_system_setup import usernames as em
from webapp import db
from webapp.class8_utils_email import accounting_sender_key
from webapp.email_log import email_logs_for_order, log_outgoing_order_email, log_phone_call
from webapp.models import Orders
from webapp.viewfuncs import hasinput


COLLECTION_COLUMNS = [
    ('completed_not_invoiced', 'Completed Not Invoiced'),
    ('needs_rate_con', 'Needs Rate Con'),
    ('rate_con_requested', 'Rate Con Requested'),
    ('rate_con_received', 'Rate Con Received'),
    ('ready_to_send', 'Ready To Send'),
    ('sent_current', 'Sent Current'),
    ('over_30', 'Over 30'),
    ('over_60', 'Over 60'),
    ('partial_paid', 'Partial Paid'),
    ('bad_debts', 'Bad Debts'),
]

COLLECTION_STATUS_LABELS = dict(COLLECTION_COLUMNS)
COLLECTION_STATUS_KEYS = {key for key, _ in COLLECTION_COLUMNS}


def clean_text(value):
    return str(value).strip() if value is not None else ''


def email_list(value):
    if not hasinput(value):
        return []
    values = str(value).replace(';', ',').split(',')
    return [clean_text(item) for item in values if '@' in clean_text(item)]


def money_value(value):
    if value is None:
        return Decimal('0.00')
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(',', '').strip() or '0')
    except (InvalidOperation, ValueError):
        return Decimal('0.00')


def money_text(value):
    return f'{money_value(value):,.2f}'


def order_date(value):
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return None


def int_value(value, default=0):
    try:
        return int(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def format_date(value):
    date_value = order_date(value)
    return date_value.strftime('%Y-%m-%d') if date_value else ''


def days_since(value, today=None):
    date_value = order_date(value)
    if not date_value:
        return None
    return ((today or datetime.date.today()) - date_value).days


def rate_con_required(order):
    return int_value(getattr(order, 'RCneeded', 0)) > 0


def rate_con_stage(order):
    stage = int_value(getattr(order, 'RCneeded', 0))
    if stage > 0 and hasinput(getattr(order, 'RateCon', None)):
        return 3
    return stage


def rate_con_needed(order):
    return rate_con_stage(order) == 1


def rate_con_requested(order):
    return rate_con_stage(order) == 2


def rate_con_received(order):
    return rate_con_stage(order) == 3 or (rate_con_required(order) and hasinput(getattr(order, 'RateCon', None)))


def rate_con_label(order):
    stage = rate_con_stage(order)
    if stage == 1:
        return 'Needs rate con'
    if stage == 2:
        return 'Request sent'
    if stage == 3:
        return 'Received'
    return 'Not required'


def balance_due(order):
    bal_due = money_value(getattr(order, 'BalDue', None))
    if bal_due:
        return bal_due
    invoice_total = money_value(getattr(order, 'InvoTotal', None))
    paid = money_value(getattr(order, 'PaidAmt', None))
    if invoice_total or paid:
        return invoice_total - paid
    return Decimal('0.00')


def paid_amount(order):
    return money_value(getattr(order, 'PaidAmt', None))


def collection_status(order, today=None):
    istat = int_value(order.Istat, -1)
    bal_due = balance_due(order)
    paid = paid_amount(order)
    age = days_since(order.InvoDate, today)

    if istat in [4, 5, 8, 9] or (money_value(order.InvoTotal) and bal_due <= Decimal('0.00')):
        return 'paid'
    if paid > Decimal('0.00') and bal_due > Decimal('0.00'):
        return 'partial_paid'
    if rate_con_needed(order):
        return 'needs_rate_con'
    if rate_con_requested(order):
        return 'rate_con_requested'
    if rate_con_received(order) and istat < 1:
        return 'rate_con_received'
    if istat < 1:
        return 'completed_not_invoiced'
    if istat in [1, 2, 6]:
        return 'ready_to_send'
    if age is not None and age >= 120:
        return 'bad_debts'
    if age is not None and age >= 60:
        return 'over_60'
    if age is not None and age >= 30:
        return 'over_30'
    return 'sent_current'


def order_matches_range(order, range_filter):
    if not range_filter or range_filter in ['open', 'all_open']:
        return collection_status(order) != 'paid'
    if range_filter == 'all':
        return collection_status(order) != 'paid'
    if range_filter == 'paid':
        return collection_status(order) == 'paid'
    if range_filter == 'overdue':
        return collection_status(order) in ['over_30', 'over_60', 'bad_debts', 'partial_paid']
    if range_filter == 'rate_con':
        return rate_con_required(order)
    if range_filter == 'recent':
        cutoff = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=120), datetime.time.min)
        return bool(
            (order.InvoDate and order.InvoDate >= cutoff) or
            (order.Date3 and order.Date3 >= cutoff) or
            (order.Date2 and order.Date2 >= cutoff)
        )
    return True


def invoice_ref(order):
    return clean_text(order.Invoice) or clean_text(order.Package)


def collection_card(order):
    status = collection_status(order)
    paid = paid_amount(order)
    due = balance_due(order)
    invoice_age = days_since(order.InvoDate)
    return {
        'id': order.id,
        'jo': clean_text(order.Jo),
        'status': status,
        'status_label': COLLECTION_STATUS_LABELS.get(status, status),
        'customer': clean_text(order.Shipper) or clean_text(order.Company),
        'container': clean_text(order.Container),
        'booking': clean_text(order.Booking) or clean_text(order.BOL),
        'delivery_location': clean_text(order.Company2),
        'invoice': invoice_ref(order),
        'invoice_date': format_date(order.InvoDate),
        'invoice_age': invoice_age if invoice_age is not None else '',
        'invoice_total': money_text(order.InvoTotal),
        'paid_amount': money_text(paid),
        'balance_due': money_text(due),
        'rate_con_needed': rate_con_required(order),
        'rate_con_stage': rate_con_stage(order),
        'rate_con_status': rate_con_label(order),
        'rate_con_missing': rate_con_needed(order),
        'rate_con_requested': rate_con_requested(order),
        'rate_con_received': rate_con_received(order),
        'rate_con_file': clean_text(order.RateCon),
        'delivery_date': format_date(order.Date3),
        'returned_date': format_date(order.Date2),
        'istat': int_value(order.Istat, -1),
        'pay_ref': clean_text(order.PayRef),
        'pay_method': clean_text(order.PayMeth),
        'paid_date': format_date(order.PaidDate),
        'email_to': clean_text(order.Emailjp) or clean_text(order.Emailap) or clean_text(order.Emailoa),
        'email_cc': clean_text(order.Emailap) if clean_text(order.Emailap) != clean_text(order.Emailjp) else '',
    }


def filtered_orders(filters=None):
    filters = filters or {}
    query = Orders.query
    query = query.filter(or_(
        Orders.Istat >= 1,
        Orders.RCneeded > 0,
        and_(Orders.Hstat >= 2, or_(Orders.Istat < 1, Orders.Istat.is_(None))),
    ))

    customer = clean_text(filters.get('customer'))
    if customer:
        query = query.filter(or_(Orders.Shipper == customer, Orders.Company == customer))

    search = clean_text(filters.get('search'))
    if search:
        pattern = f'%{search}%'
        query = query.filter(or_(
            Orders.Jo.ilike(pattern),
            Orders.Container.ilike(pattern),
            Orders.Booking.ilike(pattern),
            Orders.BOL.ilike(pattern),
            Orders.Shipper.ilike(pattern),
            Orders.Company.ilike(pattern),
            Orders.Invoice.ilike(pattern),
            Orders.Package.ilike(pattern),
        ))

    orders = query.order_by(Orders.InvoDate.desc(), Orders.Date3.desc(), Orders.id.desc()).limit(1500).all()
    status_filter = clean_text(filters.get('status'))
    range_filter = clean_text(filters.get('range')) or 'open'
    output = []
    for order in orders:
        status = collection_status(order)
        if status_filter and status != status_filter:
            continue
        if not order_matches_range(order, range_filter):
            continue
        output.append(order)
    return output


def collection_jobs(filters=None):
    jobs_by_status = {key: [] for key, _ in COLLECTION_COLUMNS}
    totals_by_status = {key: Decimal('0.00') for key, _ in COLLECTION_COLUMNS}
    total_jobs = 0
    total_due = Decimal('0.00')
    for order in filtered_orders(filters):
        card = collection_card(order)
        status = card['status']
        jobs_by_status.setdefault(status, []).append(card)
        due = balance_due(order)
        totals_by_status[status] = totals_by_status.get(status, Decimal('0.00')) + due
        total_due += due
        total_jobs += 1
    return {
        'total_jobs': total_jobs,
        'total_due': money_text(total_due),
        'columns': [
            {
                'key': key,
                'label': label,
                'jobs': jobs_by_status.get(key, []),
                'total_due': money_text(totals_by_status.get(key, Decimal('0.00'))),
            }
            for key, label in COLLECTION_COLUMNS
        ],
    }


def update_collection_job(order_id, data):
    order = Orders.query.get(order_id)
    if order is None:
        return {'ok': False, 'error': 'Order not found.'}, 404
    try:
        rc_stage = int(data.get('rate_con_stage'))
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'Rate con stage must be 0, 1, 2, or 3.'}, 400
    if rc_stage not in [0, 1, 2, 3]:
        return {'ok': False, 'error': 'Rate con stage must be 0, 1, 2, or 3.'}, 400
    order.RCneeded = rc_stage
    db.session.commit()
    return {'ok': True, 'job': collection_card(order)}, 200


def collection_email_logs(order_id):
    order = Orders.query.get(order_id)
    if order is None:
        return {'ok': False, 'error': 'Order not found.'}, 404
    return {'ok': True, 'emails': email_logs_for_order(order_id)}, 200


def send_collection_email(order_id, data):
    order = Orders.query.get(order_id)
    if order is None:
        return {'ok': False, 'error': 'Order not found.'}, 404
    to_emails = email_list(data.get('to_emails'))
    cc_emails = email_list(data.get('cc_emails'))
    subject = clean_text(data.get('subject'))
    body = clean_text(data.get('body'))
    if not to_emails:
        return {'ok': False, 'error': 'At least one valid To email is required.'}, 400
    if not subject:
        return {'ok': False, 'error': 'Subject is required.'}, 400
    if not body:
        return {'ok': False, 'error': 'Email body is required.'}, 400

    sender_key = accounting_sender_key()
    emailfrom = em[sender_key]
    username = em[sender_key]
    password = passwords[sender_key]
    msg = MIMEMultipart()
    msg['From'] = emailfrom
    msg['To'] = ', '.join(to_emails)
    msg['CC'] = ', '.join(cc_emails)
    msg['Subject'] = subject
    msg['Date'] = formatdate()
    from_domain = emailfrom.split('@')[1]
    message_id = make_msgid(domain=from_domain)
    msg['Message-ID'] = message_id
    msg.attach(MIMEText(body.replace('\n', '<br>'), 'html'))

    host, port = websites['mailserver'].split(':')
    server = smtplib.SMTP(host, port)
    server.starttls()
    server.login(username, password)
    server.sendmail(emailfrom, to_emails + cc_emails, msg.as_string())
    server.quit()

    log_outgoing_order_email(
        order,
        subject,
        body,
        to_emails,
        cc_emails,
        emailfrom,
        message_id=message_id,
        email_type='manual_email',
    )
    return {'ok': True, 'emails': email_logs_for_order(order_id)}, 200


def log_collection_call(order_id, data, username=''):
    notes = clean_text(data.get('notes'))
    contact = clean_text(data.get('contact'))
    if not notes:
        return {'ok': False, 'error': 'Call notes are required.'}, 400
    result, status_code = log_phone_call(order_id, contact, notes, username=username)
    if not result.get('ok'):
        return result, status_code
    return {'ok': True, 'emails': email_logs_for_order(order_id)}, 200


def collection_options():
    customer_rows = (
        Orders.query.with_entities(Orders.Shipper, Orders.Company)
        .filter((Orders.Shipper.isnot(None)) | (Orders.Company.isnot(None)))
        .limit(2500)
        .all()
    )
    customers = set()
    for shipper, company in customer_rows:
        if clean_text(shipper):
            customers.add(clean_text(shipper))
        elif clean_text(company):
            customers.add(clean_text(company))
    return {
        'customers': sorted(customers),
        'columns': [{'key': key, 'label': label} for key, label in COLLECTION_COLUMNS],
        'ranges': [
            {'key': 'open', 'label': 'Open'},
            {'key': 'overdue', 'label': 'Overdue'},
            {'key': 'rate_con', 'label': 'Rate Con Workflow'},
            {'key': 'recent', 'label': 'Recent 120 Days'},
            {'key': 'all', 'label': 'All'},
        ],
    }
