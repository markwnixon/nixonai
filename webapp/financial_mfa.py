import base64
import datetime
import hashlib
import hmac
import secrets
import struct
import time
from functools import wraps
from urllib.parse import quote

from flask import flash, redirect, request, session, url_for
from flask_login import current_user
from sqlalchemy import text

from webapp import db
from webapp.CCC_system_setup import scac
from webapp.models import ScacMfaSettings, UserMfa


FINANCIAL_GENRES = {
    'Billing',
    'Accounts',
    'IncomeMaint',
    'InvoiceMaint',
}

FINANCIAL_MFA_SESSION_KEY = 'financial_mfa_verified_until'
FINANCIAL_MFA_USER_KEY = 'financial_mfa_user_id'
FINANCIAL_MFA_SCAC_KEY = 'financial_mfa_scac'
FINANCIAL_MFA_CODE_HASH_KEY = 'financial_mfa_code_hash'
FINANCIAL_MFA_CODE_EXPIRES_KEY = 'financial_mfa_code_expires'
FINANCIAL_MFA_CODE_SENT_KEY = 'financial_mfa_code_sent_at'


def ensure_mfa_tables():
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS scac_mfa_settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            scac_code VARCHAR(20) NOT NULL UNIQUE,
            financial_mfa_required BOOLEAN NOT NULL DEFAULT FALSE,
            timeout_minutes INT NOT NULL DEFAULT 720,
            updated_by VARCHAR(30),
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS user_mfa (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            scac_code VARCHAR(20) NOT NULL,
            totp_secret VARCHAR(64) NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT FALSE,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            confirmed_at DATETIME,
            INDEX idx_user_mfa_user (user_id),
            INDEX idx_user_mfa_scac (scac_code),
            UNIQUE KEY uq_user_mfa_user_scac (user_id, scac_code)
        )
    """))
    db.session.commit()


def clear_financial_mfa_session():
    session.pop(FINANCIAL_MFA_SESSION_KEY, None)
    session.pop(FINANCIAL_MFA_USER_KEY, None)
    session.pop(FINANCIAL_MFA_SCAC_KEY, None)
    session.pop(FINANCIAL_MFA_CODE_HASH_KEY, None)
    session.pop(FINANCIAL_MFA_CODE_EXPIRES_KEY, None)
    session.pop(FINANCIAL_MFA_CODE_SENT_KEY, None)


def get_mfa_settings(scac_code=None):
    ensure_mfa_tables()
    code = scac_code or scac
    settings = ScacMfaSettings.query.filter_by(scac_code=code).first()
    if settings is None:
        settings = ScacMfaSettings(
            scac_code=code,
            financial_mfa_required=False,
            timeout_minutes=720,
            updated_by=None,
            updated_at=datetime.datetime.utcnow(),
        )
        db.session.add(settings)
        db.session.commit()
    return settings


def get_user_mfa(user_id=None, scac_code=None):
    ensure_mfa_tables()
    uid = user_id or current_user.id
    code = scac_code or scac
    return UserMfa.query.filter_by(user_id=uid, scac_code=code).first()


def generate_totp_secret():
    raw = secrets.token_bytes(20)
    return base64.b32encode(raw).decode('ascii').replace('=', '')


def get_or_create_user_mfa(user_id=None, scac_code=None):
    uid = user_id or current_user.id
    code = scac_code or scac
    row = get_user_mfa(uid, code)
    if row is None:
        row = UserMfa(
            user_id=uid,
            scac_code=code,
            totp_secret=generate_totp_secret(),
            enabled=False,
            created_at=datetime.datetime.utcnow(),
            confirmed_at=None,
        )
        db.session.add(row)
        db.session.commit()
    return row


def reset_user_mfa_secret(user_id=None, scac_code=None):
    row = get_or_create_user_mfa(user_id, scac_code)
    row.totp_secret = generate_totp_secret()
    row.enabled = False
    row.confirmed_at = None
    row.created_at = datetime.datetime.utcnow()
    db.session.commit()
    clear_financial_mfa_session()
    return row


def _secret_bytes(secret):
    padded = secret + ('=' * ((8 - len(secret) % 8) % 8))
    return base64.b32decode(padded, casefold=True)


def totp_code(secret, for_time=None, interval=30, digits=6):
    if for_time is None:
        for_time = int(time.time())
    counter = int(for_time // interval)
    msg = struct.pack('>Q', counter)
    digest = hmac.new(_secret_bytes(secret), msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10 ** digits)).zfill(digits)


def verify_totp(secret, code, window=1):
    clean = ''.join(ch for ch in str(code or '') if ch.isdigit())
    if len(clean) != 6:
        return False
    now = int(time.time())
    for step in range(-window, window + 1):
        if hmac.compare_digest(totp_code(secret, now + (step * 30)), clean):
            return True
    return False


def _email_code_hash(code, user_id=None, scac_code=None):
    uid = user_id or current_user.id
    code_scac = scac_code or scac
    raw = f'{uid}:{code_scac}:{code}'.encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def send_financial_mfa_email(force=False):
    if current_user.email is None or '@' not in current_user.email:
        return False, 'No valid email address is associated with this user.'

    now = int(time.time())
    last_sent = int(session.get(FINANCIAL_MFA_CODE_SENT_KEY) or 0)
    if not force and last_sent and now - last_sent < 60:
        return True, 'A financial MFA code was already sent recently.'

    code = str(secrets.randbelow(1000000)).zfill(6)
    session[FINANCIAL_MFA_CODE_HASH_KEY] = _email_code_hash(code)
    session[FINANCIAL_MFA_CODE_EXPIRES_KEY] = now + 600
    session[FINANCIAL_MFA_CODE_SENT_KEY] = now

    subject = f'{scac} financial access code'
    body = (
        f'<p>Your financial access code is:</p>'
        f'<p style="font-size: 24px; font-weight: bold; letter-spacing: 3px;">{code}</p>'
        f'<p>This code expires in 10 minutes.</p>'
    )

    from webapp.class8_utils_email import accounting_sender_key
    from webapp.send_mimemail import send_mimemail

    try:
        send_mimemail([subject, body, current_user.email, None, None, None], accounting_sender_key(), raise_errors=True)
    except Exception as exc:
        print(f'Financial MFA email send failed for user {current_user.id}: {exc}')
        return False, 'Unable to send the financial MFA code. Please contact an administrator.'

    return True, 'Financial MFA code sent to the email associated with this account.'


def verify_financial_email_code(code):
    clean = ''.join(ch for ch in str(code or '') if ch.isdigit())
    if len(clean) != 6:
        return False
    expires = int(session.get(FINANCIAL_MFA_CODE_EXPIRES_KEY) or 0)
    if expires < int(time.time()):
        return False
    expected = session.get(FINANCIAL_MFA_CODE_HASH_KEY)
    if not expected:
        return False
    return hmac.compare_digest(expected, _email_code_hash(clean))


def otpauth_uri(user_mfa, username=None):
    label = quote(f"{user_mfa.scac_code}:{username or current_user.username}")
    issuer = quote('Class8 Financials')
    return f"otpauth://totp/{label}?secret={user_mfa.totp_secret}&issuer={issuer}&digits=6&period=30"


def mark_financial_mfa_verified(settings=None):
    settings = settings or get_mfa_settings()
    timeout = settings.timeout_minutes or 720
    session[FINANCIAL_MFA_SESSION_KEY] = int(time.time()) + (timeout * 60)
    session[FINANCIAL_MFA_USER_KEY] = current_user.id
    session[FINANCIAL_MFA_SCAC_KEY] = settings.scac_code


def financial_mfa_is_verified(scac_code=None):
    code = scac_code or scac
    return (
        session.get(FINANCIAL_MFA_USER_KEY) == current_user.id and
        session.get(FINANCIAL_MFA_SCAC_KEY) == code and
        int(session.get(FINANCIAL_MFA_SESSION_KEY) or 0) > int(time.time())
    )


def financial_mfa_redirect():
    settings = get_mfa_settings()
    if not settings.financial_mfa_required:
        return None
    if financial_mfa_is_verified(settings.scac_code):
        return None

    next_url = request.full_path if request.query_string else request.path
    sent, message = send_financial_mfa_email()
    flash(message, 'warning' if sent else 'danger')
    return redirect(url_for('authenticate.mfa_verify', next=next_url))


def financial_mfa_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        redirect_response = financial_mfa_redirect()
        if redirect_response is not None:
            return redirect_response
        return func(*args, **kwargs)
    return wrapper
