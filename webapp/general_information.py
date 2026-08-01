import datetime
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from sqlalchemy import text

from webapp.extensions import db


GENERAL_INFORMATION_CATEGORIES = [
    'Company IDs',
    'Contacts',
    'Bank References',
    'Payment Methods',
    'Port / Terminal Access',
    'Load Boards / Brokers',
    'Insurance',
    'Government / Compliance',
    'Fuel / Toll / Cards',
    'Assets',
    'Drivers',
    'Software / Email / Web',
    'General Notes',
]

PAYMENT_METHOD_CATEGORY = 'Payment Methods'


def parse_date(value):
    value = (value or '').strip()
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def form_date(value):
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    return ''


def ensure_general_information_tables():
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS general_company_profile (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Co VARCHAR(12) NOT NULL UNIQUE,
            SCACCode VARCHAR(20) NULL,
            MCNumber VARCHAR(45) NULL,
            DOTNumber VARCHAR(45) NULL,
            FEIN VARCHAR(60) NULL,
            AuthorityGrantDate DATE NULL,
            NAICSCode VARCHAR(120) NULL,
            FormationDate DATE NULL,
            MainDOTTEL VARCHAR(80) NULL,
            PhysicalAddress TEXT NULL,
            MailingAddress TEXT NULL,
            DOTAddress TEXT NULL,
            CreatedAt DATETIME NOT NULL,
            UpdatedAt DATETIME NOT NULL,
            INDEX idx_general_company_profile_co (Co)
        )
    """))
    existing_profile_columns = db.session.execute(text("""
        SHOW COLUMNS FROM general_company_profile
    """)).mappings().all()
    profile_column_names = {row.get('Field') for row in existing_profile_columns}
    if 'PhysicalAddress' not in profile_column_names:
        db.session.execute(text("""
            ALTER TABLE general_company_profile ADD COLUMN PhysicalAddress TEXT NULL AFTER MainDOTTEL
        """))
    if 'MailingAddress' not in profile_column_names:
        db.session.execute(text("""
            ALTER TABLE general_company_profile ADD COLUMN MailingAddress TEXT NULL AFTER PhysicalAddress
        """))
    if 'DOTAddress' not in profile_column_names:
        db.session.execute(text("""
            ALTER TABLE general_company_profile ADD COLUMN DOTAddress TEXT NULL AFTER MailingAddress
        """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS general_information_categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Co VARCHAR(12) NOT NULL,
            CategoryName VARCHAR(100) NOT NULL,
            Active TINYINT NOT NULL DEFAULT 1,
            SortOrder INT NOT NULL DEFAULT 100,
            CreatedAt DATETIME NOT NULL,
            UpdatedAt DATETIME NOT NULL,
            UNIQUE KEY uq_general_info_category_co_name (Co, CategoryName),
            INDEX idx_general_info_category_co_sort (Co, SortOrder, CategoryName)
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS general_information_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Co VARCHAR(12) NOT NULL,
            Category VARCHAR(100) NOT NULL,
            Title VARCHAR(160) NOT NULL,
            DetailText TEXT NULL,
            WebsiteUrl VARCHAR(255) NULL,
            Username VARCHAR(160) NULL,
            PasswordValue VARCHAR(160) NULL,
            Email VARCHAR(200) NULL,
            Phone VARCHAR(80) NULL,
            Notes TEXT NULL,
            IsSensitive TINYINT NOT NULL DEFAULT 1,
            Active TINYINT NOT NULL DEFAULT 1,
            SortOrder INT NOT NULL DEFAULT 100,
            CreatedAt DATETIME NOT NULL,
            UpdatedAt DATETIME NOT NULL,
            INDEX idx_general_info_items_co_category (Co, Category),
            INDEX idx_general_info_items_active (Active),
            INDEX idx_general_info_items_title (Title)
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS secure_payment_methods (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Co VARCHAR(12) NOT NULL,
            MethodName VARCHAR(160) NOT NULL,
            ProviderName VARCHAR(160) NULL,
            WebsiteUrl VARCHAR(255) NULL,
            Username VARCHAR(160) NULL,
            Phone VARCHAR(80) NULL,
            AccountHint VARCHAR(120) NULL,
            EncryptedPassword TEXT NULL,
            EncryptedPin TEXT NULL,
            EncryptedSecurityNotes TEXT NULL,
            Notes TEXT NULL,
            Active TINYINT NOT NULL DEFAULT 1,
            CreatedAt DATETIME NOT NULL,
            UpdatedAt DATETIME NOT NULL,
            INDEX idx_secure_payment_methods_co_active (Co, Active),
            INDEX idx_secure_payment_methods_name (MethodName)
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS secure_payment_method_audit (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Co VARCHAR(12) NOT NULL,
            PaymentMethodId INT NOT NULL,
            Username VARCHAR(80) NULL,
            Action VARCHAR(45) NOT NULL,
            CreatedAt DATETIME NOT NULL,
            INDEX idx_secure_payment_audit_co_method (Co, PaymentMethodId),
            INDEX idx_secure_payment_audit_created (CreatedAt)
        )
    """))
    existing_payment_columns = db.session.execute(text("""
        SHOW COLUMNS FROM secure_payment_methods
    """)).mappings().all()
    payment_column_names = {row.get('Field') for row in existing_payment_columns}
    if 'Phone' not in payment_column_names:
        db.session.execute(text("""
            ALTER TABLE secure_payment_methods ADD COLUMN Phone VARCHAR(80) NULL AFTER Username
        """))
    db.session.commit()


def default_general_profile(company_code, scac_code, company_phone=None):
    fela_address = (
        'First Eagle Logistics\n'
        '8411 Old Marlboro Pike Ste 12\n'
        'Upper Marlboro, MD  20772-2622'
    )
    profile = {
        'Co': company_code,
        'SCACCode': scac_code or company_code,
        'MCNumber': '',
        'DOTNumber': '',
        'FEIN': '',
        'AuthorityGrantDate': None,
        'AuthorityGrantDateValue': '',
        'NAICSCode': '',
        'FormationDate': None,
        'FormationDateValue': '',
        'MainDOTTEL': company_phone or '',
        'PhysicalAddress': '',
        'MailingAddress': '',
        'DOTAddress': '',
    }
    if (scac_code or '').upper() == 'FELA':
        profile.update({
            'SCACCode': 'FELA',
            'MCNumber': '044326',
            'DOTNumber': '3040432',
            'FEIN': '47-2363625  472363625',
            'AuthorityGrantDate': datetime.date(2017, 9, 11),
            'AuthorityGrantDateValue': '2017-09-11',
            'NAICSCode': 'Local Trucking 484110',
            'FormationDate': datetime.date(2014, 11, 19),
            'FormationDateValue': '2014-11-19',
            'MainDOTTEL': '301-516-3000',
            'PhysicalAddress': fela_address,
            'MailingAddress': fela_address,
            'DOTAddress': fela_address,
        })
    return profile


def ensure_general_company_profile(company_code, scac_code, company_phone=None):
    now = datetime.datetime.utcnow()
    default_profile = default_general_profile(company_code, scac_code, company_phone)
    row = db.session.execute(text("""
        SELECT id
        FROM general_company_profile
        WHERE Co = :company_code
        LIMIT 1
    """), {'company_code': company_code}).first()
    if row:
        return
    db.session.execute(text("""
        INSERT INTO general_company_profile
            (Co, SCACCode, MCNumber, DOTNumber, FEIN, AuthorityGrantDate,
             NAICSCode, FormationDate, MainDOTTEL, PhysicalAddress, MailingAddress,
             DOTAddress, CreatedAt, UpdatedAt)
        VALUES
            (:company_code, :scac_code, :mc_number, :dot_number, :fein, :authority_grant_date,
             :naics_code, :formation_date, :main_dot_tel, :physical_address, :mailing_address,
             :dot_address, :created_at, :updated_at)
    """), {
        'company_code': company_code,
        'scac_code': default_profile['SCACCode'],
        'mc_number': default_profile['MCNumber'],
        'dot_number': default_profile['DOTNumber'],
        'fein': default_profile['FEIN'],
        'authority_grant_date': default_profile['AuthorityGrantDate'],
        'naics_code': default_profile['NAICSCode'],
        'formation_date': default_profile['FormationDate'],
        'main_dot_tel': default_profile['MainDOTTEL'],
        'physical_address': default_profile['PhysicalAddress'],
        'mailing_address': default_profile['MailingAddress'],
        'dot_address': default_profile['DOTAddress'],
        'created_at': now,
        'updated_at': now,
    })
    db.session.commit()


def general_company_profile(company_code, scac_code, company_phone=None):
    ensure_general_company_profile(company_code, scac_code, company_phone)
    row = db.session.execute(text("""
        SELECT Co, SCACCode, MCNumber, DOTNumber, FEIN, AuthorityGrantDate,
               NAICSCode, FormationDate, MainDOTTEL, PhysicalAddress,
               MailingAddress, DOTAddress
        FROM general_company_profile
        WHERE Co = :company_code
        LIMIT 1
    """), {'company_code': company_code}).mappings().first()
    profile = dict(row) if row else default_general_profile(company_code, scac_code, company_phone)
    default_profile = default_general_profile(company_code, scac_code, company_phone)
    for key in ['PhysicalAddress', 'MailingAddress', 'DOTAddress']:
        if not profile.get(key):
            profile[key] = default_profile.get(key, '')
    profile['AuthorityGrantDateValue'] = form_date(profile.get('AuthorityGrantDate'))
    profile['FormationDateValue'] = form_date(profile.get('FormationDate'))
    return profile


def update_general_company_profile(company_code, form):
    now = datetime.datetime.utcnow()
    db.session.execute(text("""
        INSERT INTO general_company_profile
            (Co, SCACCode, MCNumber, DOTNumber, FEIN, AuthorityGrantDate,
             NAICSCode, FormationDate, MainDOTTEL, PhysicalAddress, MailingAddress,
             DOTAddress, CreatedAt, UpdatedAt)
        VALUES
            (:company_code, :scac_code, :mc_number, :dot_number, :fein, :authority_grant_date,
             :naics_code, :formation_date, :main_dot_tel, :physical_address, :mailing_address,
             :dot_address, :created_at, :updated_at)
        ON DUPLICATE KEY UPDATE
            SCACCode = VALUES(SCACCode),
            MCNumber = VALUES(MCNumber),
            DOTNumber = VALUES(DOTNumber),
            FEIN = VALUES(FEIN),
            AuthorityGrantDate = VALUES(AuthorityGrantDate),
            NAICSCode = VALUES(NAICSCode),
            FormationDate = VALUES(FormationDate),
            MainDOTTEL = VALUES(MainDOTTEL),
            PhysicalAddress = VALUES(PhysicalAddress),
            MailingAddress = VALUES(MailingAddress),
            DOTAddress = VALUES(DOTAddress),
            UpdatedAt = VALUES(UpdatedAt)
    """), {
        'company_code': company_code,
        'scac_code': (form.get('scac_code') or '').strip(),
        'mc_number': (form.get('mc_number') or '').strip(),
        'dot_number': (form.get('dot_number') or '').strip(),
        'fein': (form.get('fein') or '').strip(),
        'authority_grant_date': parse_date(form.get('authority_grant_date')),
        'naics_code': (form.get('naics_code') or '').strip(),
        'formation_date': parse_date(form.get('formation_date')),
        'main_dot_tel': (form.get('main_dot_tel') or '').strip(),
        'physical_address': (form.get('physical_address') or '').strip(),
        'mailing_address': (form.get('mailing_address') or '').strip(),
        'dot_address': (form.get('dot_address') or '').strip(),
        'created_at': now,
        'updated_at': now,
    })
    db.session.commit()


def ensure_default_general_categories(company_code):
    now = datetime.datetime.utcnow()
    for index, category in enumerate(GENERAL_INFORMATION_CATEGORIES, start=1):
        db.session.execute(text("""
            INSERT INTO general_information_categories
                (Co, CategoryName, Active, SortOrder, CreatedAt, UpdatedAt)
        VALUES
            (:company_code, :category, 1, :sort_order, :created_at, :updated_at)
        ON DUPLICATE KEY UPDATE
            UpdatedAt = VALUES(UpdatedAt)
    """), {
            'company_code': company_code,
            'category': category,
            'sort_order': index * 10,
            'created_at': now,
            'updated_at': now,
        })
    db.session.commit()


def general_information_categories(company_code):
    ensure_default_general_categories(company_code)
    rows = db.session.execute(text("""
        SELECT CategoryName
        FROM general_information_categories
        WHERE Co = :company_code AND Active = 1
        ORDER BY SortOrder, CategoryName
    """), {'company_code': company_code}).mappings().all()
    return [row['CategoryName'] for row in rows]


def add_general_information_category(company_code, category):
    category = (category or '').strip()
    if not category:
        return 'Category name is required.'
    now = datetime.datetime.utcnow()
    db.session.execute(text("""
        INSERT INTO general_information_categories
            (Co, CategoryName, Active, SortOrder, CreatedAt, UpdatedAt)
        VALUES
            (:company_code, :category, 1, 100, :created_at, :updated_at)
        ON DUPLICATE KEY UPDATE
            Active = 1,
            UpdatedAt = VALUES(UpdatedAt)
    """), {
        'company_code': company_code,
        'category': category,
        'created_at': now,
        'updated_at': now,
    })
    db.session.commit()
    return ''


def delete_general_information_category(company_code, category):
    db.session.execute(text("""
        UPDATE general_information_categories
        SET Active = 0, UpdatedAt = :updated_at
        WHERE Co = :company_code AND CategoryName = :category
    """), {
        'company_code': company_code,
        'category': (category or '').strip(),
        'updated_at': datetime.datetime.utcnow(),
    })
    db.session.commit()


def general_information_items(company_code):
    rows = db.session.execute(text("""
        SELECT id, Co, Category, Title, DetailText, WebsiteUrl, Username, PasswordValue,
               Email, Phone, Notes, IsSensitive, Active, SortOrder,
               CreatedAt, UpdatedAt
        FROM general_information_items
        WHERE Co = :company_code AND Active = 1
        ORDER BY Category, SortOrder, Title, id
    """), {'company_code': company_code}).mappings().all()
    items = []
    for row in rows:
        item = dict(row)
        item['Sensitive'] = item.get('IsSensitive')
        items.append(item)
    return items


def payment_method_item(method):
    return {
        'id': f"payment-{method.get('id')}",
        'SourceId': method.get('id'),
        'ItemKind': 'payment_method',
        'Co': method.get('Co'),
        'Category': PAYMENT_METHOD_CATEGORY,
        'Title': method.get('MethodName') or '',
        'DetailText': method.get('ProviderName') or '',
        'WebsiteUrl': method.get('WebsiteUrl') or '',
        'Username': method.get('Username') or '',
        'PasswordValue': 'Protected',
        'Email': '',
        'Phone': method.get('Phone') or '',
        'Notes': method.get('Notes') or '',
        'AccountHint': method.get('AccountHint') or '',
        'Sensitive': 1,
        'IsSecurePayment': True,
    }


def combined_general_information_items(company_code):
    items = general_information_items(company_code)
    for item in items:
        item['ItemKind'] = 'general'
        item['SourceId'] = item.get('id')
        item['IsSecurePayment'] = False
        item['AccountHint'] = ''
    items.extend(payment_method_item(method) for method in secure_payment_methods(company_code))
    return sorted(items, key=lambda item: (
        item.get('Category') or '',
        item.get('Title') or '',
        str(item.get('id') or ''),
    ))


def upsert_general_information_item(company_code, form):
    item_id = form.get('item_id')
    now = datetime.datetime.utcnow()
    payload = {
        'company_code': company_code,
        'category': (form.get('category') or 'General Notes').strip(),
        'title': (form.get('title') or '').strip(),
        'detail_text': (form.get('detail_text') or '').strip(),
        'website_url': (form.get('website_url') or '').strip(),
        'username': (form.get('username') or '').strip(),
        'password_value': (form.get('password_value') or '').strip(),
        'email': (form.get('email') or '').strip(),
        'phone': (form.get('phone') or '').strip(),
        'notes': (form.get('notes') or '').strip(),
        'sensitive': 1 if form.get('sensitive') else 0,
        'updated_at': now,
    }
    if not payload['title']:
        return 'Title is required.'

    if item_id:
        payload['item_id'] = item_id
        db.session.execute(text("""
            UPDATE general_information_items
            SET Category = :category,
                Title = :title,
                DetailText = :detail_text,
                WebsiteUrl = :website_url,
                Username = :username,
                PasswordValue = :password_value,
                Email = :email,
                Phone = :phone,
                Notes = :notes,
                IsSensitive = :sensitive,
                UpdatedAt = :updated_at
            WHERE id = :item_id AND Co = :company_code
        """), payload)
    else:
        payload['created_at'] = now
        db.session.execute(text("""
            INSERT INTO general_information_items
                (Co, Category, Title, DetailText, WebsiteUrl, Username, PasswordValue,
                 Email, Phone, Notes, IsSensitive, Active, SortOrder, CreatedAt, UpdatedAt)
            VALUES
                (:company_code, :category, :title, :detail_text, :website_url, :username, :password_value,
                 :email, :phone, :notes, :sensitive, 1, 100, :created_at, :updated_at)
        """), payload)
    db.session.commit()
    return ''


def delete_general_information_item(company_code, item_id):
    db.session.execute(text("""
        UPDATE general_information_items
        SET Active = 0, UpdatedAt = :updated_at
        WHERE id = :item_id AND Co = :company_code
    """), {
        'company_code': company_code,
        'item_id': item_id,
        'updated_at': datetime.datetime.utcnow(),
    })
    db.session.commit()


def _secure_info_fernet():
    raw_key = os.environ.get('CLASS8_PAYMENT_METHOD_KEY') or os.environ.get('GENERAL_INFO_FERNET_KEY')
    if raw_key:
        try:
            return Fernet(raw_key.encode())
        except (ValueError, TypeError):
            pass
    secret = str(current_app.config.get('SECRET_KEY') or 'class8-local-development-key')
    derived_key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(derived_key)


def encrypt_secret(value):
    value = (value or '').strip()
    if not value:
        return ''
    return _secure_info_fernet().encrypt(value.encode()).decode()


def decrypt_secret(value):
    value = (value or '').strip()
    if not value:
        return ''
    try:
        return _secure_info_fernet().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        return '[Unable to decrypt with current key]'


def secure_payment_methods(company_code):
    rows = db.session.execute(text("""
        SELECT id, Co, MethodName, ProviderName, WebsiteUrl, Username, Phone, AccountHint,
               Notes, Active, CreatedAt, UpdatedAt
        FROM secure_payment_methods
        WHERE Co = :company_code AND Active = 1
        ORDER BY MethodName, ProviderName, id
    """), {'company_code': company_code}).mappings().all()
    return [dict(row) for row in rows]


def upsert_secure_payment_method(company_code, form):
    method_id = form.get('payment_method_id')
    now = datetime.datetime.utcnow()
    method_name = (form.get('method_name') or '').strip()
    if not method_name:
        return 'Payment method name is required.'
    payload = {
        'company_code': company_code,
        'method_name': method_name,
        'provider_name': (form.get('provider_name') or '').strip(),
        'website_url': (form.get('payment_website_url') or '').strip(),
        'username': (form.get('payment_username') or '').strip(),
        'phone': (form.get('phone') or '').strip(),
        'account_hint': (form.get('account_hint') or '').strip(),
        'notes': (form.get('payment_notes') or '').strip(),
        'updated_at': now,
    }
    password_value = (form.get('secure_password') or '').strip()
    pin_value = (form.get('secure_pin') or '').strip()
    security_notes_value = (form.get('secure_security_notes') or '').strip()

    if method_id:
        payload['method_id'] = method_id
        assignments = """
            MethodName = :method_name,
            ProviderName = :provider_name,
            WebsiteUrl = :website_url,
            Username = :username,
            Phone = :phone,
            AccountHint = :account_hint,
            Notes = :notes,
            UpdatedAt = :updated_at
        """
        if password_value:
            payload['encrypted_password'] = encrypt_secret(password_value)
            assignments += ", EncryptedPassword = :encrypted_password"
        if pin_value:
            payload['encrypted_pin'] = encrypt_secret(pin_value)
            assignments += ", EncryptedPin = :encrypted_pin"
        if security_notes_value:
            payload['encrypted_security_notes'] = encrypt_secret(security_notes_value)
            assignments += ", EncryptedSecurityNotes = :encrypted_security_notes"
        db.session.execute(text(f"""
            UPDATE secure_payment_methods
            SET {assignments}
            WHERE id = :method_id AND Co = :company_code
        """), payload)
    else:
        payload.update({
            'encrypted_password': encrypt_secret(password_value),
            'encrypted_pin': encrypt_secret(pin_value),
            'encrypted_security_notes': encrypt_secret(security_notes_value),
            'created_at': now,
        })
        db.session.execute(text("""
            INSERT INTO secure_payment_methods
                (Co, MethodName, ProviderName, WebsiteUrl, Username, Phone, AccountHint,
                 EncryptedPassword, EncryptedPin, EncryptedSecurityNotes,
                 Notes, Active, CreatedAt, UpdatedAt)
            VALUES
                (:company_code, :method_name, :provider_name, :website_url, :username, :phone, :account_hint,
                 :encrypted_password, :encrypted_pin, :encrypted_security_notes,
                 :notes, 1, :created_at, :updated_at)
        """), payload)
    db.session.commit()
    return ''


def upsert_secure_payment_method_from_general_form(company_code, form):
    class PaymentFormAdapter:
        def __init__(self, source_form):
            self.source_form = source_form

        def get(self, key, default=None):
            mapping = {
                'payment_method_id': 'payment_method_id',
                'method_name': 'title',
                'provider_name': 'detail_text',
                'payment_website_url': 'website_url',
                'payment_username': 'username',
                'account_hint': 'account_hint',
                'secure_password': 'password_value',
                'secure_pin': 'secure_pin',
                'secure_security_notes': 'secure_security_notes',
                'payment_notes': 'notes',
            }
            return self.source_form.get(mapping.get(key, key), default)

    return upsert_secure_payment_method(company_code, PaymentFormAdapter(form))


def delete_secure_payment_method(company_code, method_id):
    db.session.execute(text("""
        UPDATE secure_payment_methods
        SET Active = 0, UpdatedAt = :updated_at
        WHERE id = :method_id AND Co = :company_code
    """), {
        'company_code': company_code,
        'method_id': method_id,
        'updated_at': datetime.datetime.utcnow(),
    })
    db.session.commit()


def reveal_secure_payment_method(company_code, method_id, username):
    row = db.session.execute(text("""
        SELECT id, MethodName, ProviderName, WebsiteUrl, Username, AccountHint,
               Phone, EncryptedPassword, EncryptedPin, EncryptedSecurityNotes, Notes
        FROM secure_payment_methods
        WHERE id = :method_id AND Co = :company_code AND Active = 1
        LIMIT 1
    """), {
        'company_code': company_code,
        'method_id': method_id,
    }).mappings().first()
    if not row:
        return None
    db.session.execute(text("""
        INSERT INTO secure_payment_method_audit
            (Co, PaymentMethodId, Username, Action, CreatedAt)
        VALUES
            (:company_code, :method_id, :username, 'reveal', :created_at)
    """), {
        'company_code': company_code,
        'method_id': method_id,
        'username': username,
        'created_at': datetime.datetime.utcnow(),
    })
    db.session.commit()
    item = dict(row)
    item['PasswordValue'] = decrypt_secret(item.pop('EncryptedPassword', ''))
    item['PinValue'] = decrypt_secret(item.pop('EncryptedPin', ''))
    item['SecurityNotesValue'] = decrypt_secret(item.pop('EncryptedSecurityNotes', ''))
    return item
