import datetime
import os
import re

from sqlalchemy import text
from werkzeug.utils import secure_filename

from webapp.extensions import db
from webapp.models import Drivers, Trucklog, Vehicles
from webapp.CCC_system_setup import addpath, scac
from webapp.class8_utils_email import info_mimemail


COMPLIANCE_ITEM_TYPES = [
    ('maryland_annual_report', 'Maryland Annual Business Report'),
    ('ifta_quarterly', 'IFTA Quarterly'),
    ('truck_registration', 'Truck Registration'),
    ('vehicle_registration_renewal', 'Vehicle Tag / Registration Renewal'),
    ('truck_2290', 'Truck 2290 Fuel Tax'),
    ('truck_insurance', 'Truck Insurance Expiration'),
    ('fmcsa_biennial', 'FMCSA Biennial Filing'),
    ('clearinghouse_driver', 'Clearinghouse Annual Driver Check'),
    ('random_drug_test', 'Random Drug Test Selection'),
    ('atcc_renewal', 'ATCC Renewal'),
    ('scac_renewal', 'SCAC Renewal'),
    ('ucr_registration', 'UCR Registration'),
    ('workers_comp', 'Workers Comp'),
    ('uiia_access', 'UIIA Access'),
    ('website_access', 'Website Access'),
    ('other', 'Other Compliance Item'),
]

COMPLIANCE_ITEM_LABELS = dict(COMPLIANCE_ITEM_TYPES)


def slugify(value):
    safe = secure_filename(str(value or '').strip().lower().replace(' ', '_'))
    return safe or 'other'


def parse_date(value):
    value = (value or '').strip()
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def date_value(row, key):
    value = row.get(key) if row else None
    if isinstance(value, datetime.datetime):
        return value.date()
    return value


def display_date(value):
    if isinstance(value, datetime.datetime):
        return value.date()
    return value or ''


def form_date(value):
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    return ''


def days_until(value, today=None):
    if value is None:
        return None
    today = today or datetime.date.today()
    return (value - today).days


def compliance_status(row, today=None):
    today = today or datetime.date.today()
    status = (row.get('Status') or '').strip()
    due_date = date_value(row, 'DueDate') or date_value(row, 'ExpireDate')
    if status.lower() in ['complete', 'filed', 'inactive']:
        return 'complete'
    if due_date is None:
        return 'open'
    if due_date < today:
        return 'overdue'
    if due_date <= today + datetime.timedelta(days=30):
        return 'due-soon'
    return 'open'


def ensure_compliance_check_tables():
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS compliance_company_profile (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Co VARCHAR(12) NOT NULL UNIQUE,
            CompanyName VARCHAR(120) NULL,
            DOTNumber VARCHAR(45) NULL,
            MCNumber VARCHAR(45) NULL,
            FEIN VARCHAR(45) NULL,
            AlertEmail VARCHAR(200) NULL,
            AlertLeadDays INT NOT NULL DEFAULT 30,
            Notes TEXT NULL,
            CreatedAt DATETIME NOT NULL,
            UpdatedAt DATETIME NOT NULL,
            INDEX idx_compliance_company_profile_co (Co)
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS compliance_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Co VARCHAR(12) NOT NULL,
            ItemType VARCHAR(45) NOT NULL,
            Subject VARCHAR(120) NULL,
            Identifier VARCHAR(120) NULL,
            PeriodLabel VARCHAR(45) NULL,
            PeriodCadence VARCHAR(20) NOT NULL DEFAULT 'annual',
            PeriodFrom DATE NULL,
            PeriodTo DATE NULL,
            DueDate DATE NULL,
            FiledDate DATE NULL,
            ExpireDate DATE NULL,
            Status VARCHAR(45) NULL,
            WebsiteUrl VARCHAR(255) NULL,
            Username VARCHAR(120) NULL,
            PasswordValue VARCHAR(120) NULL,
            File1 VARCHAR(255) NULL,
            Notes TEXT NULL,
            AlertEnabled TINYINT NOT NULL DEFAULT 1,
            LastAlertSentAt DATETIME NULL,
            CreatedAt DATETIME NOT NULL,
            UpdatedAt DATETIME NOT NULL,
            INDEX idx_compliance_items_co_type (Co, ItemType),
            INDEX idx_compliance_items_due (DueDate),
            INDEX idx_compliance_items_expire (ExpireDate)
        )
    """))
    existing_columns = db.session.execute(text("""
        SHOW COLUMNS FROM compliance_items
    """)).mappings().all()
    column_names = {row.get('Field') for row in existing_columns}
    if 'PeriodFrom' not in column_names:
        db.session.execute(text("""
            ALTER TABLE compliance_items ADD COLUMN PeriodFrom DATE NULL AFTER PeriodLabel
        """))
    if 'PeriodTo' not in column_names:
        db.session.execute(text("""
            ALTER TABLE compliance_items ADD COLUMN PeriodTo DATE NULL AFTER PeriodFrom
        """))
    if 'PeriodCadence' not in column_names:
        db.session.execute(text("""
            ALTER TABLE compliance_items ADD COLUMN PeriodCadence VARCHAR(20) NOT NULL DEFAULT 'annual' AFTER PeriodLabel
        """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS compliance_item_type_options (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Co VARCHAR(12) NOT NULL,
            TypeValue VARCHAR(45) NOT NULL,
            TypeLabel VARCHAR(120) NOT NULL,
            Active TINYINT NOT NULL DEFAULT 1,
            SortOrder INT NOT NULL DEFAULT 100,
            CreatedAt DATETIME NOT NULL,
            UpdatedAt DATETIME NOT NULL,
            UNIQUE KEY uq_compliance_item_type_options_co_value (Co, TypeValue),
            INDEX idx_compliance_item_type_options_co_sort (Co, SortOrder, TypeLabel)
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS compliance_item_files (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Co VARCHAR(12) NOT NULL,
            ItemId INT NOT NULL,
            FileLabel VARCHAR(120) NULL,
            StoredFile VARCHAR(255) NOT NULL,
            OriginalFile VARCHAR(255) NULL,
            UploadedAt DATETIME NOT NULL,
            INDEX idx_compliance_item_files_item (ItemId),
            INDEX idx_compliance_item_files_co (Co)
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS compliance_vehicle_repairs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Co VARCHAR(12) NOT NULL,
            VehicleId INT NULL,
            Unit VARCHAR(45) NOT NULL,
            RepairDate DATE NULL,
            Notes TEXT NULL,
            File1 VARCHAR(255) NULL,
            CreatedAt DATETIME NOT NULL,
            UpdatedAt DATETIME NOT NULL,
            INDEX idx_compliance_vehicle_repairs_co_unit (Co, Unit),
            INDEX idx_compliance_vehicle_repairs_date (RepairDate)
        )
    """))
    db.session.commit()


def ensure_default_item_types(company_code):
    now = datetime.datetime.utcnow()
    for index, (type_value, type_label) in enumerate(COMPLIANCE_ITEM_TYPES, start=1):
        db.session.execute(text("""
            INSERT IGNORE INTO compliance_item_type_options
                (Co, TypeValue, TypeLabel, Active, SortOrder, CreatedAt, UpdatedAt)
            VALUES
                (:company_code, :type_value, :type_label, 1, :sort_order, :created_at, :updated_at)
        """), {
            'company_code': company_code,
            'type_value': type_value,
            'type_label': type_label,
            'sort_order': index * 10,
            'created_at': now,
            'updated_at': now,
        })
    db.session.commit()


def compliance_item_type_options(company_code):
    ensure_default_item_types(company_code)
    rows = db.session.execute(text("""
        SELECT TypeValue, TypeLabel
        FROM compliance_item_type_options
        WHERE Co = :company_code AND Active = 1
        ORDER BY SortOrder, TypeLabel
    """), {'company_code': company_code}).mappings().all()
    return [(row.get('TypeValue'), row.get('TypeLabel')) for row in rows]


def compliance_item_type_labels(company_code):
    return dict(compliance_item_type_options(company_code))


def add_compliance_item_type(company_code, label):
    label = (label or '').strip()
    if not label:
        return 'Compliance item type name is required.'
    type_value = slugify(label)
    now = datetime.datetime.utcnow()
    db.session.execute(text("""
        INSERT INTO compliance_item_type_options
            (Co, TypeValue, TypeLabel, Active, SortOrder, CreatedAt, UpdatedAt)
        VALUES
            (:company_code, :type_value, :type_label, 1, 100, :created_at, :updated_at)
        ON DUPLICATE KEY UPDATE
            TypeLabel = VALUES(TypeLabel),
            Active = 1,
            UpdatedAt = VALUES(UpdatedAt)
    """), {
        'company_code': company_code,
        'type_value': type_value,
        'type_label': label,
        'created_at': now,
        'updated_at': now,
    })
    db.session.commit()
    return ''


def delete_compliance_item_type(company_code, type_value):
    db.session.execute(text("""
        UPDATE compliance_item_type_options
        SET Active = 0, UpdatedAt = :updated_at
        WHERE Co = :company_code AND TypeValue = :type_value
    """), {
        'company_code': company_code,
        'type_value': type_value,
        'updated_at': datetime.datetime.utcnow(),
    })
    db.session.commit()


def compliance_profile(company_code, company_name='', default_email=''):
    row = db.session.execute(text("""
        SELECT * FROM compliance_company_profile WHERE Co = :company_code
    """), {'company_code': company_code}).mappings().first()
    if row:
        return dict(row)
    now = datetime.datetime.utcnow()
    db.session.execute(text("""
        INSERT INTO compliance_company_profile
            (Co, CompanyName, AlertEmail, AlertLeadDays, CreatedAt, UpdatedAt)
        VALUES
            (:company_code, :company_name, :alert_email, 30, :created_at, :updated_at)
    """), {
        'company_code': company_code,
        'company_name': company_name,
        'alert_email': default_email,
        'created_at': now,
        'updated_at': now,
    })
    db.session.commit()
    row = db.session.execute(text("""
        SELECT * FROM compliance_company_profile WHERE Co = :company_code
    """), {'company_code': company_code}).mappings().first()
    return dict(row)


def update_compliance_profile(company_code, form):
    try:
        alert_lead_days = int(form.get('alert_lead_days') or 30)
    except ValueError:
        alert_lead_days = 30
    db.session.execute(text("""
        UPDATE compliance_company_profile
        SET CompanyName = :company_name,
            DOTNumber = :dot_number,
            MCNumber = :mc_number,
            FEIN = :fein,
            AlertEmail = :alert_email,
            AlertLeadDays = :alert_lead_days,
            Notes = :notes,
            UpdatedAt = :updated_at
        WHERE Co = :company_code
    """), {
        'company_code': company_code,
        'company_name': (form.get('company_name') or '').strip(),
        'dot_number': (form.get('dot_number') or '').strip(),
        'mc_number': (form.get('mc_number') or '').strip(),
        'fein': (form.get('fein') or '').strip(),
        'alert_email': (form.get('alert_email') or '').strip(),
        'alert_lead_days': alert_lead_days,
        'notes': (form.get('profile_notes') or '').strip(),
        'updated_at': datetime.datetime.utcnow(),
    })
    db.session.commit()


def compliance_items(company_code):
    type_labels = compliance_item_type_labels(company_code)
    rows = db.session.execute(text("""
        SELECT * FROM compliance_items
        WHERE Co = :company_code
        ORDER BY
            CASE WHEN COALESCE(DueDate, ExpireDate) IS NULL THEN 1 ELSE 0 END,
            COALESCE(DueDate, ExpireDate),
            ItemType,
            Subject
    """), {'company_code': company_code}).mappings().all()
    today = datetime.date.today()
    output = []
    for row in rows:
        item = dict(row)
        item['TypeLabel'] = type_labels.get(item.get('ItemType'), COMPLIANCE_ITEM_LABELS.get(item.get('ItemType'), item.get('ItemType') or 'Compliance Item'))
        item['PeriodCadence'] = normalize_period_cadence(item.get('PeriodCadence'), item.get('ItemType'))
        item['ComputedStatus'] = compliance_status(item, today)
        item['DaysUntil'] = days_until(date_value(item, 'DueDate') or date_value(item, 'ExpireDate'), today)
        item['PeriodDisplay'] = period_display(item)
        item['DueExpireDisplay'] = date_value(item, 'DueDate') or date_value(item, 'ExpireDate') or ''
        item['PeriodFromForm'] = form_date(item.get('PeriodFrom'))
        item['PeriodToForm'] = form_date(item.get('PeriodTo'))
        item['DueExpireForm'] = form_date(date_value(item, 'DueDate') or date_value(item, 'ExpireDate'))
        item['FiledDateForm'] = form_date(item.get('FiledDate'))
        item['Files'] = compliance_item_files(company_code, item.get('id'))
        output.append(item)
    return output


def due_compliance_items(company_code, lead_days=30):
    type_labels = compliance_item_type_labels(company_code)
    today = datetime.date.today()
    limit = today + datetime.timedelta(days=int(lead_days or 30))
    rows = db.session.execute(text("""
        SELECT * FROM compliance_items
        WHERE Co = :company_code
          AND AlertEnabled = 1
          AND COALESCE(Status, '') NOT IN ('Complete', 'Filed', 'Inactive')
          AND COALESCE(DueDate, ExpireDate) IS NOT NULL
          AND COALESCE(DueDate, ExpireDate) <= :limit_date
        ORDER BY COALESCE(DueDate, ExpireDate), ItemType, Subject
    """), {'company_code': company_code, 'limit_date': limit}).mappings().all()
    output = []
    for row in rows:
        item = dict(row)
        item['TypeLabel'] = type_labels.get(item.get('ItemType'), COMPLIANCE_ITEM_LABELS.get(item.get('ItemType'), item.get('ItemType') or 'Compliance Item'))
        item['ComputedStatus'] = compliance_status(item, today)
        item['DaysUntil'] = days_until(date_value(item, 'DueDate') or date_value(item, 'ExpireDate'), today)
        output.append(item)
    return output


def compliance_due_alert_payload(company_code, lead_days=30):
    items = due_compliance_items(company_code, lead_days)
    alerts = []
    for item in items:
        due_expire = date_value(item, 'DueDate') or date_value(item, 'ExpireDate')
        files = compliance_item_files(company_code, item.get('id'))
        alerts.append({
            'id': item.get('id'),
            'type': item.get('ItemType') or '',
            'type_label': item.get('TypeLabel') or '',
            'subject': item.get('Subject') or '',
            'identifier': item.get('Identifier') or '',
            'period': period_display(item),
            'period_from': form_date(item.get('PeriodFrom')),
            'period_to': form_date(item.get('PeriodTo')),
            'period_cadence': normalize_period_cadence(item.get('PeriodCadence'), item.get('ItemType')),
            'due_date_expires': form_date(due_expire),
            'filed_date': form_date(item.get('FiledDate')),
            'status': item.get('Status') or '',
            'computed_status': item.get('ComputedStatus') or '',
            'days_until': item.get('DaysUntil'),
            'alert_enabled': bool(item.get('AlertEnabled')),
            'website_url': item.get('WebsiteUrl') or '',
            'notes': item.get('Notes') or '',
            'documents': [
                {
                    'id': file_row.get('id'),
                    'display_name': file_row.get('DisplayName') or '',
                    'label': file_row.get('FileLabel') or '',
                    'original_file': file_row.get('OriginalFile') or '',
                    'url': file_link(file_row.get('StoredFile')),
                    'uploaded_at': file_row.get('UploadedAt').isoformat() if isinstance(file_row.get('UploadedAt'), datetime.datetime) else str(file_row.get('UploadedAt') or ''),
                }
                for file_row in files
            ],
        })
    return {
        'company': company_code,
        'lead_days': int(lead_days or 30),
        'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'count': len(alerts),
        'alerts': alerts,
    }


def filing_history(items):
    return [
        item for item in items
        if item.get('FiledDate') or item.get('File1') or item.get('Files') or item.get('Status') in ['Complete', 'Filed']
    ]


def period_display(item):
    period_from = date_value(item, 'PeriodFrom')
    period_to = date_value(item, 'PeriodTo')
    if period_from and period_to:
        return f'{period_from} to {period_to}'
    if period_from:
        return str(period_from)
    if period_to:
        return str(period_to)
    return ''


def period_label_from_dates(period_from, period_to):
    if period_from and period_to:
        return f'{period_from} to {period_to}'
    if period_from:
        return str(period_from)
    if period_to:
        return str(period_to)
    return ''


def normalize_period_cadence(value, item_type=''):
    value = (value or '').strip().lower()
    if value in ['quarterly', 'qtr']:
        return 'quarterly'
    if value in ['annual', 'yearly', 'year']:
        return 'annual'
    if value in ['biannual', 'bi-annual', 'biennial', 'two_year']:
        return 'biannual'
    if value in ['none', 'one_time', 'one-time']:
        return 'none'
    if item_type == 'ifta_quarterly':
        return 'quarterly'
    return 'annual'


def period_increment_months(cadence):
    if cadence == 'quarterly':
        return 3
    if cadence == 'annual':
        return 12
    if cadence == 'biannual':
        return 24
    return 0


def next_identifier_text(value, cadence):
    if cadence == 'quarterly':
        return next_quarter_text(value)
    if cadence == 'annual':
        return next_year_text(value)
    if cadence == 'biannual':
        next_value = next_year_text(value)
        return next_year_text(next_value)
    return value or ''


def credential_items(items):
    return [
        item for item in items
        if item.get('ItemType') in ['website_access', 'uiia_access']
        or item.get('WebsiteUrl')
        or item.get('Username')
        or item.get('PasswordValue')
    ]


def upsert_compliance_item(company_code, form):
    item_id = form.get('item_id')
    payload = {
        'company_code': company_code,
        'item_type': (form.get('item_type') or 'other').strip(),
        'subject': (form.get('subject') or '').strip(),
        'identifier': (form.get('identifier') or '').strip(),
        'period_cadence': normalize_period_cadence(form.get('period_cadence'), form.get('item_type')),
        'period_from': parse_date(form.get('period_from')),
        'period_to': parse_date(form.get('period_to')),
        'due_date': parse_date(form.get('due_date_expire')) or parse_date(form.get('due_date')) or parse_date(form.get('expire_date')),
        'filed_date': parse_date(form.get('filed_date')),
        'status': (form.get('status') or 'Open').strip(),
        'website_url': (form.get('website_url') or '').strip(),
        'username': (form.get('username') or '').strip(),
        'password_value': (form.get('password_value') or '').strip(),
        'file1': (form.get('file1') or '').strip(),
        'notes': (form.get('notes') or '').strip(),
        'alert_enabled': 1 if form.get('alert_enabled') else 0,
        'updated_at': datetime.datetime.utcnow(),
    }
    payload['expire_date'] = payload['due_date']
    payload['period_label'] = period_label_from_dates(
        payload['period_from'],
        payload['period_to']
    )
    if item_id:
        payload['item_id'] = item_id
        db.session.execute(text("""
            UPDATE compliance_items
            SET ItemType = :item_type,
                Subject = :subject,
                Identifier = :identifier,
                PeriodLabel = :period_label,
                PeriodCadence = :period_cadence,
                PeriodFrom = :period_from,
                PeriodTo = :period_to,
                DueDate = :due_date,
                FiledDate = :filed_date,
                ExpireDate = :expire_date,
                Status = :status,
                WebsiteUrl = :website_url,
                Username = :username,
                PasswordValue = :password_value,
                File1 = :file1,
                Notes = :notes,
                AlertEnabled = :alert_enabled,
                UpdatedAt = :updated_at
            WHERE id = :item_id AND Co = :company_code
        """), payload)
    else:
        payload['created_at'] = payload['updated_at']
        db.session.execute(text("""
            INSERT INTO compliance_items
                (Co, ItemType, Subject, Identifier, PeriodLabel, PeriodCadence, PeriodFrom, PeriodTo, DueDate, FiledDate, ExpireDate,
                 Status, WebsiteUrl, Username, PasswordValue, File1, Notes, AlertEnabled, CreatedAt, UpdatedAt)
            VALUES
                (:company_code, :item_type, :subject, :identifier, :period_label, :period_cadence, :period_from, :period_to, :due_date, :filed_date, :expire_date,
                 :status, :website_url, :username, :password_value, :file1, :notes, :alert_enabled, :created_at, :updated_at)
        """), payload)
    db.session.commit()


def last_day_of_month(year, month):
    return [
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31, 30, 31, 30, 31, 31, 30, 31, 30, 31
    ][month - 1]


def add_months(value, months):
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        value = value.date()
    source_last_day = last_day_of_month(value.year, value.month)
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    target_last_day = last_day_of_month(year, month)
    if value.day == source_last_day:
        return datetime.date(year, month, target_last_day)
    return datetime.date(year, month, min(value.day, target_last_day))


def next_quarter_text(value):
    value = (value or '').strip()
    if not value:
        return value
    match = re.search(r'(?i)\bQ(?:TR)?\s*([1-4])\b', value)
    if not match:
        year_match = re.search(r'\b(20\d{2}|19\d{2})\b', value)
        if not year_match:
            return value
        year = int(year_match.group(1)) + 1
        return value[:year_match.start()] + str(year) + value[year_match.end():]

    quarter = int(match.group(1))
    next_quarter = 1 if quarter == 4 else quarter + 1
    output = value[:match.start(1)] + str(next_quarter) + value[match.end(1):]
    if quarter == 4:
        year_match = re.search(r'\b(20\d{2}|19\d{2})\b', output)
        if year_match:
            year = int(year_match.group(1)) + 1
            output = output[:year_match.start()] + str(year) + output[year_match.end():]
    return output


def next_year_text(value):
    value = (value or '').strip()
    if not value:
        return value
    year_match = re.search(r'\b(20\d{2}|19\d{2})\b', value)
    if not year_match:
        return value
    year = int(year_match.group(1)) + 1
    return value[:year_match.start()] + str(year) + value[year_match.end():]


def create_next_compliance_item(company_code, item_id):
    item = db.session.execute(text("""
        SELECT * FROM compliance_items
        WHERE id = :item_id AND Co = :company_code
    """), {'item_id': item_id, 'company_code': company_code}).mappings().first()
    if not item:
        return 'Compliance item was not found.'

    item_type = (item.get('ItemType') or '').strip()
    cadence = normalize_period_cadence(item.get('PeriodCadence'), item_type)
    identifier = item.get('Identifier') or ''
    period_from = date_value(item, 'PeriodFrom')
    period_to = date_value(item, 'PeriodTo')
    quarterly = cadence == 'quarterly'
    date_increment_months = period_increment_months(cadence)
    now = datetime.datetime.utcnow()
    next_period_from = add_months(period_from, date_increment_months)
    next_period_to = add_months(period_to, date_increment_months)
    next_due_expire = add_months(item.get('DueDate') or item.get('ExpireDate'), date_increment_months)
    next_period_label = period_label_from_dates(
        next_period_from,
        next_period_to
    )

    db.session.execute(text("""
        INSERT INTO compliance_items
            (Co, ItemType, Subject, Identifier, PeriodLabel, PeriodCadence, PeriodFrom, PeriodTo, DueDate, FiledDate, ExpireDate,
             Status, WebsiteUrl, Username, PasswordValue, File1, Notes, AlertEnabled, CreatedAt, UpdatedAt)
        VALUES
            (:company_code, :item_type, :subject, :identifier, :period_label, :period_cadence, :period_from, :period_to, :due_date, NULL, :expire_date,
             'Open', :website_url, :username, :password_value, '', :notes, :alert_enabled, :created_at, :updated_at)
    """), {
        'company_code': company_code,
        'item_type': item_type,
        'subject': item.get('Subject') or '',
        'identifier': next_identifier_text(identifier, cadence),
        'period_label': next_period_label,
        'period_cadence': cadence,
        'period_from': next_period_from,
        'period_to': next_period_to,
        'due_date': next_due_expire,
        'expire_date': next_due_expire,
        'website_url': item.get('WebsiteUrl') or '',
        'username': item.get('Username') or '',
        'password_value': item.get('PasswordValue') or '',
        'notes': item.get('Notes') or '',
        'alert_enabled': 1 if item.get('AlertEnabled') else 0,
        'created_at': now,
        'updated_at': now,
    })
    db.session.commit()
    return ''


def delete_compliance_item(company_code, item_id):
    rows = db.session.execute(text("""
        SELECT StoredFile FROM compliance_item_files
        WHERE ItemId = :item_id AND Co = :company_code
    """), {'item_id': item_id, 'company_code': company_code}).mappings().all()
    stored_paths = [
        compliance_upload_path(row.get('StoredFile'))
        for row in rows
    ]

    db.session.execute(text("""
        DELETE FROM compliance_item_files WHERE ItemId = :item_id AND Co = :company_code
    """), {'item_id': item_id, 'company_code': company_code})
    db.session.execute(text("""
        DELETE FROM compliance_items WHERE id = :item_id AND Co = :company_code
    """), {'item_id': item_id, 'company_code': company_code})
    db.session.commit()

    for stored_path in stored_paths:
        if stored_path and os.path.exists(stored_path):
            os.remove(stored_path)


def compliance_item_files(company_code, item_id):
    if not item_id:
        return []
    rows = db.session.execute(text("""
        SELECT * FROM compliance_item_files
        WHERE Co = :company_code AND ItemId = :item_id
        ORDER BY UploadedAt DESC, id DESC
    """), {'company_code': company_code, 'item_id': item_id}).mappings().all()
    files = []
    for row in rows:
        file_row = dict(row)
        file_row['DisplayName'] = os.path.basename(file_row.get('StoredFile') or '') or file_row.get('OriginalFile') or 'Open Document'
        files.append(file_row)
    return files


def save_compliance_item_file(company_code, item_id, uploaded_file, label=''):
    if not item_id:
        return 'Choose a compliance item before uploading a file.'
    item = db.session.execute(text("""
        SELECT * FROM compliance_items WHERE id = :item_id AND Co = :company_code
    """), {'item_id': item_id, 'company_code': company_code}).mappings().first()
    if not item:
        return 'Compliance item was not found.'
    current_count = db.session.execute(text("""
        SELECT COUNT(*) FROM compliance_item_files
        WHERE Co = :company_code AND ItemId = :item_id
    """), {'company_code': company_code, 'item_id': item_id}).scalar() or 0
    if int(current_count) >= 3:
        return 'Each compliance item can store up to 3 documents. Delete an existing document before uploading another.'
    if not uploaded_file or not uploaded_file.filename:
        return 'Choose a file to upload.'
    safe_original = secure_filename(uploaded_file.filename)
    if not safe_original:
        return 'The uploaded file name is not valid.'

    root, ext = os.path.splitext(safe_original)
    document_label = (label or root or safe_original).strip()
    filename_base = slugify(document_label)
    directory = addpath(f'static/{scac}/data/vCompliance')
    os.makedirs(directory, exist_ok=True)

    extension = ext.lower() or '.pdf'
    filename = f'{filename_base}{extension}'
    output_path = os.path.join(directory, filename)
    suffix = 2
    while os.path.exists(output_path):
        filename = f'{filename_base}_{suffix}{extension}'
        output_path = os.path.join(directory, filename)
        suffix += 1

    uploaded_file.save(output_path)
    now = datetime.datetime.utcnow()
    db.session.execute(text("""
        INSERT INTO compliance_item_files
            (Co, ItemId, FileLabel, StoredFile, OriginalFile, UploadedAt)
        VALUES
            (:company_code, :item_id, :file_label, :stored_file, :original_file, :uploaded_at)
    """), {
        'company_code': company_code,
        'item_id': item_id,
        'file_label': document_label,
        'stored_file': f'/static/{scac}/data/vCompliance/{filename}',
        'original_file': safe_original,
        'uploaded_at': now,
    })
    db.session.commit()
    return ''


def compliance_upload_path(stored_file):
    stored_file = (stored_file or '').strip()
    if not stored_file:
        return ''
    prefix = f'/static/{scac}/data/vCompliance/'
    if stored_file.startswith(prefix):
        filename = os.path.basename(stored_file)
    elif stored_file.startswith(f'static/{scac}/data/vCompliance/'):
        filename = os.path.basename(stored_file)
    else:
        return ''

    directory = os.path.abspath(addpath(f'static/{scac}/data/vCompliance'))
    candidate = os.path.abspath(os.path.join(directory, filename))
    if os.path.commonpath([directory, candidate]) != directory:
        return ''
    return candidate


def delete_compliance_item_file(company_code, file_id):
    row = db.session.execute(text("""
        SELECT StoredFile FROM compliance_item_files
        WHERE id = :file_id AND Co = :company_code
    """), {'file_id': file_id, 'company_code': company_code}).mappings().first()
    stored_path = compliance_upload_path(row.get('StoredFile') if row else '')

    db.session.execute(text("""
        DELETE FROM compliance_item_files WHERE id = :file_id AND Co = :company_code
    """), {'file_id': file_id, 'company_code': company_code})
    db.session.commit()

    if stored_path and os.path.exists(stored_path):
        os.remove(stored_path)


def compliance_asset_summary(company_code):
    drivers = Drivers.query.filter(Drivers.Active == 1).order_by(Drivers.Name).all()
    vehicles = Vehicles.query.filter(Vehicles.Active == 1).order_by(Vehicles.Unit).all()
    units = [vehicle.Unit for vehicle in vehicles if vehicle.Unit]
    repair_rows = []
    if units:
        repair_rows = Trucklog.query.filter(
            Trucklog.Unit.in_(units),
            Trucklog.Maintrecord != None,
            Trucklog.Maintrecord != '',
        ).order_by(Trucklog.Date.desc()).limit(100).all()
    repairs_by_unit = {}
    for repair in repair_rows:
        repairs_by_unit.setdefault(repair.Unit, []).append(repair)

    manual_rows = db.session.execute(text("""
        SELECT * FROM compliance_vehicle_repairs
        WHERE Co = :company_code
        ORDER BY RepairDate DESC, id DESC
    """), {'company_code': company_code}).mappings().all()
    manual_repairs_by_unit = {}
    for row in manual_rows:
        manual_repairs_by_unit.setdefault(row.get('Unit'), []).append(dict(row))

    today = datetime.date.today()
    for truck in vehicles:
        exp_date = truck.ExpDate
        truck.ComplianceStatus = 'open'
        if exp_date:
            if exp_date < today:
                truck.ComplianceStatus = 'overdue'
            elif exp_date <= today + datetime.timedelta(days=30):
                truck.ComplianceStatus = 'due-soon'
        truck.RecentRepairs = repairs_by_unit.get(truck.Unit, [])[:3]
        truck.ManualRepairs = manual_repairs_by_unit.get(truck.Unit, [])[:5]

    for driver in drivers:
        driver.ComplianceAlerts = []
        for label, value in [
            ('CDL', driver.CDLexpire),
            ('Med', driver.MedExpire),
            ('TWIC', driver.TwicExpire),
        ]:
            expire_date = value.date() if isinstance(value, datetime.datetime) else value
            if expire_date and expire_date < today:
                driver.ComplianceAlerts.append(f'{label} overdue')
            elif expire_date and expire_date <= today + datetime.timedelta(days=30):
                driver.ComplianceAlerts.append(f'{label} due soon')

    return drivers, vehicles


def save_vehicle_repair(company_code, form, uploaded_file=None):
    vehicle_id = form.get('vehicle_id')
    vehicle = Vehicles.query.get(vehicle_id) if vehicle_id else None
    unit = vehicle.Unit if vehicle is not None else (form.get('unit') or '').strip()
    if not unit:
        return 'Choose a vehicle before adding a repair note.'

    file_path = ''
    if uploaded_file and uploaded_file.filename:
        safe_name = secure_filename(uploaded_file.filename)
        if safe_name:
            stamp = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
            unit_safe = secure_filename(unit) or 'Vehicle'
            filename = f'VehicleRepair_{unit_safe}_{stamp}_{safe_name}'
            output_path = addpath(f'static/{scac}/data/vCompliance/{filename}')
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            uploaded_file.save(output_path)
            file_path = f'/static/{scac}/data/vCompliance/{filename}'

    now = datetime.datetime.utcnow()
    db.session.execute(text("""
        INSERT INTO compliance_vehicle_repairs
            (Co, VehicleId, Unit, RepairDate, Notes, File1, CreatedAt, UpdatedAt)
        VALUES
            (:company_code, :vehicle_id, :unit, :repair_date, :notes, :file1, :created_at, :updated_at)
    """), {
        'company_code': company_code,
        'vehicle_id': vehicle.id if vehicle is not None else None,
        'unit': unit,
        'repair_date': parse_date(form.get('repair_date')) or datetime.date.today(),
        'notes': (form.get('repair_notes') or '').strip(),
        'file1': file_path,
        'created_at': now,
        'updated_at': now,
    })
    db.session.commit()
    return ''


def delete_vehicle_repair(company_code, repair_id):
    db.session.execute(text("""
        DELETE FROM compliance_vehicle_repairs
        WHERE id = :repair_id AND Co = :company_code
    """), {'repair_id': repair_id, 'company_code': company_code})
    db.session.commit()


def file_link(value):
    value = (value or '').strip()
    if not value:
        return ''
    if value.startswith('http://') or value.startswith('https://') or value.startswith('/static/'):
        return value
    if value.startswith('static/'):
        return '/' + value
    return value


def send_compliance_alert_digest(company_code, profile, due_items):
    alert_email = (profile.get('AlertEmail') or '').strip()
    if not alert_email:
        return ['No alert email is set for this company.']
    if not due_items:
        return ['No due compliance alerts to send.']

    lines = []
    for item in due_items:
        due_date = date_value(item, 'DueDate') or date_value(item, 'ExpireDate')
        days = item.get('DaysUntil')
        timing = 'overdue' if days is not None and days < 0 else f'due in {days} days'
        lines.append(
            f"{item.get('TypeLabel')}: {item.get('Subject') or item.get('Identifier') or 'Compliance item'} "
            f"({due_date}, {timing})"
        )
    body = 'The following compliance items need attention:<br><br>' + '<br>'.join(lines)
    emaildata = [
        f"Compliance Alerts - {profile.get('CompanyName') or company_code}",
        body,
        alert_email,
        '',
        '',
        '',
        'No Attachment',
        '',
        'temp',
    ]
    err = info_mimemail(emaildata, [], sender_key=None)
    now = datetime.datetime.utcnow()
    for item in due_items:
        db.session.execute(text("""
            UPDATE compliance_items
            SET LastAlertSentAt = :sent_at
            WHERE id = :item_id AND Co = :company_code
        """), {'sent_at': now, 'item_id': item.get('id'), 'company_code': company_code})
    db.session.commit()
    return err
