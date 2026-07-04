import datetime

from sqlalchemy import text

from webapp import db
from webapp.models import Orders
from webapp.viewfuncs import hasinput


def ensure_email_log_table():
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS email_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            OrderId INT NULL,
            Jo VARCHAR(50),
            EmailType VARCHAR(50),
            Direction VARCHAR(20),
            FromEmail VARCHAR(255),
            ToEmails TEXT,
            CcEmails TEXT,
            Subject TEXT,
            BodyText MEDIUMTEXT,
            AttachmentName VARCHAR(255),
            AttachmentSendName VARCHAR(255),
            MessageId VARCHAR(255),
            SentAt DATETIME,
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_email_log_order (OrderId),
            INDEX idx_email_log_jo (Jo),
            INDEX idx_email_log_type (EmailType)
        )
    """))
    db.session.commit()


def clean_text(value):
    return str(value).strip() if value is not None else ''


def compact_email_list(values):
    return ', '.join([clean_text(value) for value in values or [] if hasinput(clean_text(value))])


def email_type_from_subject(subject):
    subject_text = clean_text(subject).lower()
    if 'rate con request' in subject_text or 'rate confirmation' in subject_text:
        return 'rate_con_request'
    if 'invoice' in subject_text:
        return 'invoice_sent'
    if 'proof' in subject_text or 'pod' in subject_text:
        return 'proof_sent'
    return 'outgoing'


def log_outgoing_order_email(
    order,
    subject,
    body,
    to_emails,
    cc_emails,
    from_email,
    attachment_name='',
    attachment_send_name='',
    message_id='',
    email_type=None,
):
    if order is None:
        return
    ensure_email_log_table()
    db.session.execute(
        text("""
            INSERT INTO email_log
                (OrderId, Jo, EmailType, Direction, FromEmail, ToEmails, CcEmails,
                 Subject, BodyText, AttachmentName, AttachmentSendName, MessageId,
                 SentAt, CreatedAt)
            VALUES
                (:order_id, :jo, :email_type, 'outgoing', :from_email, :to_emails,
                 :cc_emails, :subject, :body_text, :attachment_name,
                 :attachment_send_name, :message_id, :sent_at, :created_at)
        """),
        {
            'order_id': order.id,
            'jo': clean_text(order.Jo),
            'email_type': email_type or email_type_from_subject(subject),
            'from_email': clean_text(from_email),
            'to_emails': compact_email_list(to_emails),
            'cc_emails': compact_email_list(cc_emails),
            'subject': clean_text(subject),
            'body_text': clean_text(body),
            'attachment_name': clean_text(attachment_name),
            'attachment_send_name': clean_text(attachment_send_name),
            'message_id': clean_text(message_id),
            'sent_at': datetime.datetime.utcnow(),
            'created_at': datetime.datetime.utcnow(),
        },
    )
    db.session.commit()


def log_phone_call(order_id, contact, notes, username=''):
    order = Orders.query.get(order_id)
    if order is None:
        return {'ok': False, 'error': 'Order not found.'}, 404
    ensure_email_log_table()
    now = datetime.datetime.utcnow()
    db.session.execute(
        text("""
            INSERT INTO email_log
                (OrderId, Jo, EmailType, Direction, FromEmail, ToEmails, CcEmails,
                 Subject, BodyText, SentAt, CreatedAt)
            VALUES
                (:order_id, :jo, 'phone_call', 'phone', :username, :contact, '',
                 :subject, :body_text, :sent_at, :created_at)
        """),
        {
            'order_id': order.id,
            'jo': clean_text(order.Jo),
            'username': clean_text(username),
            'contact': clean_text(contact),
            'subject': f'Phone call: {clean_text(contact) or clean_text(order.Shipper) or clean_text(order.Jo)}',
            'body_text': clean_text(notes),
            'sent_at': now,
            'created_at': now,
        },
    )
    db.session.commit()
    return {'ok': True}, 200


def log_outgoing_email_for_orders(
    sids,
    subject,
    body,
    to_emails,
    cc_emails,
    from_email,
    attachment_name='',
    attachment_send_name='',
    message_id='',
):
    for sid in sids or []:
        order = Orders.query.get(sid)
        log_outgoing_order_email(
            order,
            subject,
            body,
            to_emails,
            cc_emails,
            from_email,
            attachment_name=attachment_name,
            attachment_send_name=attachment_send_name,
            message_id=message_id,
        )


def email_logs_for_order(order_id, limit=8):
    ensure_email_log_table()
    rows = db.session.execute(
        text("""
            SELECT id, Jo, EmailType, Direction, FromEmail, ToEmails, CcEmails,
                   Subject, BodyText, AttachmentName, AttachmentSendName, MessageId, SentAt
            FROM email_log
            WHERE OrderId = :order_id
            ORDER BY COALESCE(SentAt, CreatedAt) DESC, id DESC
            LIMIT :limit
        """),
        {'order_id': order_id, 'limit': limit},
    ).mappings().all()
    output = []
    for row in rows:
        sent_at = row.get('SentAt')
        output.append({
            'id': row.get('id'),
            'jo': row.get('Jo') or '',
            'email_type': row.get('EmailType') or '',
            'direction': row.get('Direction') or '',
            'from_email': row.get('FromEmail') or '',
            'to_emails': row.get('ToEmails') or '',
            'cc_emails': row.get('CcEmails') or '',
            'subject': row.get('Subject') or '',
            'body_text': row.get('BodyText') or '',
            'attachment_name': row.get('AttachmentName') or '',
            'attachment_send_name': row.get('AttachmentSendName') or '',
            'message_id': row.get('MessageId') or '',
            'sent_at': sent_at.strftime('%Y-%m-%d %H:%M') if sent_at else '',
        })
    return output
