import datetime
import os
import smtplib
from decimal import Decimal, InvalidOperation
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from urllib.parse import quote

from sqlalchemy import and_, or_

from webapp.CCC_system_setup import addpath, passwords, scac, tpath, websites
from webapp.CCC_system_setup import usernames as em
from webapp import db
from webapp.class8_utils_email import (
    accounting_sender_key,
)
from webapp.email_log import email_logs_for_order, log_outgoing_order_email, log_phone_call
from webapp.models import Orders
from webapp.viewfuncs import hasinput


COLLECTION_COLUMNS = [
    ('completed_not_invoiced', 'Completed Not Invoiced'),
    ('needs_rate_con', 'Needs Rate Con Invoice Match'),
    ('rate_con_requested', 'Rate Con Requested'),
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


def unique_emails(values):
    output = []
    seen = set()
    for value in values:
        items = value if isinstance(value, (list, tuple, set)) else email_list(value)
        for email in items:
            email = clean_text(email)
            if '@' not in email:
                continue
            key = email.lower()
            if key not in seen:
                output.append(email)
                seen.add(key)
    return output


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
    return int_value(getattr(order, 'RCneeded', 0))


def rate_con_needed(order):
    return rate_con_stage(order) == 1


def rate_con_requested(order):
    return rate_con_stage(order) == 2


def rate_con_received(order):
    return rate_con_stage(order) == 3


def rate_con_amount(order):
    return money_value(getattr(order, 'RCAmount', None))


def invoice_ready_for_rate_con_match(order):
    return hasinput(getattr(order, 'Invoice', None)) and money_value(getattr(order, 'InvoTotal', None)) > Decimal('0.00')


def rate_con_amount_matches_invoice(order):
    if not hasinput(getattr(order, 'RCAmount', None)):
        return False
    invoice_total = money_value(getattr(order, 'InvoTotal', None))
    return abs(rate_con_amount(order) - invoice_total) <= Decimal('0.01')


def invalid_rate_con_received_status(order):
    if rate_con_stage(order) != 3:
        return False
    rc_amount = rate_con_amount(order)
    invoice_total = money_value(getattr(order, 'InvoTotal', None))
    if rc_amount <= Decimal('0.00'):
        return True
    if invoice_total > Decimal('0.00') and abs(rc_amount - invoice_total) > Decimal('0.01'):
        return True
    return False


def rate_con_ready_to_send(order):
    return rate_con_received(order) and invoice_ready_for_rate_con_match(order) and rate_con_amount_matches_invoice(order)


def rate_con_label(order):
    if rate_con_required(order) and not rate_con_received(order):
        return 'Needs Rate Con'
    if rate_con_received(order) and not invoice_ready_for_rate_con_match(order):
        return 'Needs Invoice'
    if rate_con_received(order) and not rate_con_amount_matches_invoice(order):
        return 'Unmatched Rate Con & Invoice'
    if rate_con_ready_to_send(order):
        return 'Received'
    return 'Not required'


def is_rate_con_followup(order):
    return rate_con_required(order) and not rate_con_ready_to_send(order)


def collection_email_defaults(order):
    broker_email = clean_text(order.Emailjp)
    support_broker_email = clean_text(order.Emailoa)
    ap_email = clean_text(order.Emailap)
    if is_rate_con_followup(order):
        return {
            'email_to': ', '.join(unique_emails([broker_email])),
            'email_cc': ', '.join(unique_emails([support_broker_email])),
            'email_mode': 'rate_con',
        }
    return {
        'email_to': ', '.join(unique_emails([ap_email, broker_email, support_broker_email])),
        'email_cc': '',
        'email_mode': 'collection',
    }


def update_order_broker_emails(order, data):
    emailjp = clean_text(data.get('emailjp'))
    emailoa = clean_text(data.get('emailoa'))
    if emailjp or 'emailjp' in data:
        order.Emailjp = emailjp or None
    if emailoa or 'emailoa' in data:
        order.Emailoa = emailoa or None


def balance_due(order):
    if hasinput(getattr(order, 'BalDue', None)):
        return money_value(getattr(order, 'BalDue', None))
    invoice_total = money_value(getattr(order, 'InvoTotal', None))
    paid = paid_amount(order)
    if invoice_total or paid:
        return invoice_total - paid
    return Decimal('0.00')


def paid_amount(order):
    return money_value(getattr(order, 'PaidAmt', None))


def payment_repair_needed(order):
    if not hasinput(getattr(order, 'BalDue', None)):
        return False
    invoice_total = money_value(getattr(order, 'InvoTotal', None))
    paid = money_value(getattr(order, 'PaidAmt', None))
    reported_due = money_value(getattr(order, 'BalDue', None))
    expected_due = invoice_total - paid
    return abs(reported_due - expected_due) > Decimal('0.01')


def expected_balance_due(order):
    return money_value(getattr(order, 'InvoTotal', None)) - money_value(getattr(order, 'PaidAmt', None))


def collection_status(order, today=None):
    istat = int_value(order.Istat, -1)
    hstat = int_value(order.Hstat, 0)
    bal_due = balance_due(order)
    paid = paid_amount(order)
    age = days_since(order.InvoDate, today)

    if istat in [5, 8, 9]:
        return 'paid'
    if istat == 4:
        return 'partial_paid'
    if hstat < 2 and istat < 1:
        return 'not_ready'
    if rate_con_requested(order):
        return 'rate_con_requested'
    if rate_con_required(order) and not rate_con_ready_to_send(order):
        return 'needs_rate_con'
    if istat < 1:
        if rate_con_ready_to_send(order):
            return 'ready_to_send'
        return 'completed_not_invoiced'
    if istat in [1, 2, 6]:
        if rate_con_required(order) and not rate_con_ready_to_send(order):
            return 'needs_rate_con'
        return 'ready_to_send'
    if age is not None and age >= 120:
        return 'bad_debts'
    if age is not None and age >= 60:
        return 'over_60'
    if age is not None and age >= 30:
        return 'over_30'
    return 'sent_current'


def normalize_presend_collection_status(order):
    changed = False
    if invalid_rate_con_received_status(order):
        order.RCneeded = 1
        changed = True
    status = collection_status(order)
    if status in ['completed_not_invoiced', 'needs_rate_con', 'rate_con_requested'] and int_value(order.Istat, -1) == 3:
        order.Istat = 2
        changed = True
    return changed


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


def is_export_order(order):
    haul_type = clean_text(getattr(order, 'HaulType', '')).lower()
    return 'export' in haul_type


def collection_reference(order):
    load_number = clean_text(getattr(order, 'Order', ''))
    if load_number:
        return load_number
    container = clean_text(order.Container)
    primary_ref = clean_text(order.Booking) if is_export_order(order) else clean_text(order.BOL)
    fallback_ref = clean_text(order.BOL) if is_export_order(order) else clean_text(order.Booking)
    reference = primary_ref or fallback_ref
    parts = [part for part in [reference, container] if part]
    return ' / '.join(parts) or clean_text(order.Jo)


def collection_subject_reference(order):
    order_number = clean_text(getattr(order, 'Order', ''))
    reference = collection_reference(order)
    if not reference:
        return ''
    first_word = order_number.lower().split(maxsplit=1)[0] if order_number else ''
    if first_word in ['load', 'pro']:
        return reference
    return f'Order {reference}'


def collection_subject(order):
    reference = collection_subject_reference(order) or clean_text(order.Jo)
    prefix = 'Rate con follow up for' if is_rate_con_followup(order) else 'Follow up on'
    return f'{prefix} {reference}'


def safe_filename_part(value, fallback='order'):
    text = clean_text(value) or fallback
    safe_text = ''.join(char if char.isalnum() or char in ['-', '_'] else '_' for char in text)
    return safe_text.strip('_') or fallback


def invoice_package_name(order):
    package = os.path.basename(clean_text(order.Package))
    return package


def invoice_package_path(order):
    package = invoice_package_name(order)
    if not package:
        return ''
    path = addpath(f'static/{scac}/data/vPackage/{package}')
    return path if os.path.isfile(path) else ''


def invoice_package_send_name(order):
    return f'{safe_filename_part(order.Container, clean_text(order.Jo) or "order")}_invoice_package.pdf'


def invoice_package_view_url(order):
    package = invoice_package_name(order)
    if not package or not invoice_package_path(order):
        return ''
    return f'/static/{scac}/data/vPackage/{quote(package)}'


def rate_con_view_url(order):
    rate_con = os.path.basename(clean_text(order.RateCon))
    if not rate_con:
        return ''
    path = addpath(tpath('Orders-RateCon', rate_con))
    if not os.path.isfile(path):
        return ''
    return f'/static/{scac}/data/vRateCon/{quote(rate_con)}'


def collection_card(order):
    status = collection_status(order)
    paid = paid_amount(order)
    due = balance_due(order)
    repair_needed = payment_repair_needed(order)
    invoice_age = days_since(order.InvoDate)
    email_defaults = collection_email_defaults(order)
    package_path = invoice_package_path(order)
    return {
        'id': order.id,
        'jo': clean_text(order.Jo),
        'order_number': clean_text(order.Order),
        'collection_reference': collection_reference(order),
        'default_email_subject': collection_subject(order),
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
        'expected_balance_due': money_text(expected_balance_due(order)),
        'payment_repair_needed': repair_needed,
        'rate_con_needed': rate_con_required(order),
        'rate_con_stage': rate_con_stage(order),
        'rate_con_status': rate_con_label(order),
        'rate_con_missing': rate_con_needed(order),
        'rate_con_requested': rate_con_requested(order),
        'rate_con_received': rate_con_received(order),
        'rate_con_file': clean_text(order.RateCon),
        'rate_con_amount': money_text(rate_con_amount(order)) if hasinput(getattr(order, 'RCAmount', None)) else '',
        'rate_con_amount_matches_invoice': rate_con_amount_matches_invoice(order),
        'rate_con_ready_to_send': rate_con_ready_to_send(order),
        'rate_con_invoice_required': not invoice_ready_for_rate_con_match(order) if rate_con_received(order) else False,
        'rate_con_view_url': rate_con_view_url(order),
        'delivery_date': format_date(order.Date3),
        'returned_date': format_date(order.Date2),
        'istat': int_value(order.Istat, -1),
        'pay_ref': clean_text(order.PayRef),
        'pay_method': clean_text(order.PayMeth),
        'paid_date': format_date(order.PaidDate),
        'email_to': email_defaults['email_to'],
        'email_cc': email_defaults['email_cc'],
        'email_mode': email_defaults['email_mode'],
        'emailjp': clean_text(order.Emailjp),
        'emailoa': clean_text(order.Emailoa),
        'emailap': clean_text(order.Emailap),
        'package_file': invoice_package_name(order),
        'package_available': bool(package_path),
        'package_view_url': invoice_package_view_url(order),
        'package_send_name': invoice_package_send_name(order) if package_path else '',
    }


def filtered_orders(filters=None):
    filters = filters or {}
    query = Orders.query
    query = query.filter(or_(Orders.Istat <= 4, Orders.Istat.is_(None)))
    query = query.filter(or_(
        Orders.Istat >= 1,
        and_(Orders.Hstat >= 2, Orders.RCneeded > 0),
        and_(Orders.Hstat >= 2, or_(Orders.Istat < 1, Orders.Istat.is_(None))),
    ))
    cutoff = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=730), datetime.time.min)
    query = query.filter(or_(
        Orders.InvoDate >= cutoff,
        Orders.Date3 >= cutoff,
        Orders.Date2 >= cutoff,
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

    order_by = (Orders.InvoDate.desc(), Orders.Date3.desc(), Orders.id.desc())
    orders = query.order_by(*order_by).limit(1500).all()
    if not search:
        # Rate-con jobs are often not invoiced yet, so invoice-date ordering can push them past
        # the general board cap. Always include them before the Python status grouping below.
        seen_ids = {order.id for order in orders}
        rate_con_orders = query.filter(Orders.Hstat >= 2, Orders.RCneeded > 0).order_by(*order_by).all()
        orders.extend(order for order in rate_con_orders if order.id not in seen_ids)
    if any(normalize_presend_collection_status(order) for order in orders):
        db.session.commit()
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
    if 'rate_con_amount' in data:
        amount = clean_text(data.get('rate_con_amount'))
        order.RCAmount = money_text(amount) if amount else None
    update_order_broker_emails(order, data)
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
    update_order_broker_emails(order, data)
    to_emails = email_list(data.get('to_emails'))
    cc_emails = email_list(data.get('cc_emails'))
    if is_rate_con_followup(order):
        if not hasinput(order.Emailjp) and to_emails:
            order.Emailjp = to_emails[0]
        if not hasinput(order.Emailoa) and cc_emails:
            order.Emailoa = cc_emails[0]
        broker_emails = unique_emails([order.Emailjp])
        support_broker_emails = unique_emails([order.Emailoa])
        ap_email_keys = {email.lower() for email in email_list(order.Emailap)}
        to_emails = [email for email in unique_emails([to_emails, broker_emails]) if email.lower() not in ap_email_keys]
        cc_emails = [email for email in unique_emails([cc_emails, support_broker_emails]) if email.lower() not in ap_email_keys]
    subject = clean_text(data.get('subject'))
    body = clean_text(data.get('body'))
    if not to_emails:
        return {'ok': False, 'error': 'At least one valid To email is required.'}, 400
    if not subject:
        return {'ok': False, 'error': 'Subject is required.'}, 400
    if not body:
        return {'ok': False, 'error': 'Email body is required.'}, 400

    include_package = bool(data.get('include_package'))
    attachment_path = ''
    attachment_source_name = ''
    attachment_send_name = ''
    if include_package:
        attachment_path = invoice_package_path(order)
        if not attachment_path:
            return {'ok': False, 'error': 'Invoice package is not available for this order.'}, 400
        attachment_source_name = invoice_package_name(order)
        attachment_send_name = invoice_package_send_name(order)

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
    if attachment_path:
        with open(attachment_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment', filename=attachment_send_name)
        msg.attach(part)

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
        attachment_name=attachment_source_name,
        attachment_send_name=attachment_send_name,
    )
    return {'ok': True, 'emails': email_logs_for_order(order_id)}, 200


def upload_collection_rate_con(order_id, uploaded_file, data=None):
    data = data or {}
    order = Orders.query.get(order_id)
    if order is None:
        return {'ok': False, 'error': 'Order not found.'}, 404
    if uploaded_file is None or not clean_text(getattr(uploaded_file, 'filename', '')):
        return {'ok': False, 'error': 'Choose a PDF rate con to upload.'}, 400

    _name, extension = os.path.splitext(uploaded_file.filename)
    if extension.lower() != '.pdf':
        return {'ok': False, 'error': 'Rate con upload must be a PDF file.'}, 400

    try:
        current_cache = int(order.Rcache or 0)
    except (TypeError, ValueError):
        current_cache = 0
    next_cache = current_cache + 1 if order.RateCon else current_cache
    jo_part = safe_filename_part(order.Jo, f'order_{order.id}')
    filename = f'RateCon_{jo_part}_c{next_cache}.pdf'
    output_path = addpath(tpath('Orders-RateCon', filename))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    uploaded_file.save(output_path)

    if order.RateCon:
        old_path = addpath(tpath('Orders-RateCon', os.path.basename(clean_text(order.RateCon))))
        if old_path != output_path and os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    order.RateCon = filename
    order.Rcache = next_cache
    order.RCneeded = 3
    amount = clean_text(data.get('rate_con_amount'))
    if amount:
        order.RCAmount = money_text(amount)
    db.session.commit()
    return {'ok': True, 'job': collection_card(order)}, 200


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
