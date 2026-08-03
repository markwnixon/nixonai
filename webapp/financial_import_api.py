import datetime
import hashlib
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text

from webapp import db
from webapp.CCC_system_setup import scac
from webapp.class8_tasks_gledger import gledger_write
from webapp.models import Accounts, Bills, People
from webapp.viewfuncs import newjo


EXPENSE_TYPES = ['Expense', 'Cost of Goods Sold', 'Other Expense']
PAYMENT_TYPES = ['Bank', 'Credit Card', 'Exch']
GENERIC_VENDOR_WORDS = {
    'inc', 'llc', 'co', 'corp', 'corporation', 'company', 'logistics',
    'transport', 'transportation', 'services', 'service', 'the', 'and',
}


def clean_text(value, limit=None):
    text_value = ' '.join(str(value or '').strip().split())
    if limit:
        return text_value[:limit]
    return text_value


def money_string(value):
    clean = str(value or '').replace('$', '').replace(',', '').strip()
    if clean in ['', 'None', 'none']:
        clean = '0'
    amount = Decimal(clean).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f'{amount:.2f}'


def money_decimal(value):
    try:
        return Decimal(str(value or '').replace('$', '').replace(',', '').strip()).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP,
        )
    except:
        return Decimal('0.00')


def parse_date(value, field_name, errors, default=None):
    if value in [None, '']:
        return default
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min)
    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y']:
        try:
            return datetime.datetime.strptime(str(value).strip(), fmt)
        except:
            pass
    errors.append(f'{field_name} must be YYYY-MM-DD or MM/DD/YYYY.')
    return default


def ensure_financial_import_tables():
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS financial_import_rules (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Scac VARCHAR(20) NOT NULL,
            RuleType VARCHAR(30) NOT NULL DEFAULT 'bill',
            SourceType VARCHAR(30) NOT NULL DEFAULT '',
            VendorKey VARCHAR(200) NOT NULL DEFAULT '',
            DescriptionKey VARCHAR(250) NOT NULL DEFAULT '',
            VendorId INT,
            VendorName VARCHAR(100),
            ExpenseAccountId INT,
            ExpenseAccountName VARCHAR(50),
            PayAccountId INT,
            PayAccountName VARCHAR(50),
            IncomeAccountId INT,
            IncomeAccountName VARCHAR(50),
            Co VARCHAR(9),
            AccountType VARCHAR(45),
            AccountCategory VARCHAR(45),
            AccountSubcategory VARCHAR(45),
            Confidence DECIMAL(5,2) NOT NULL DEFAULT 1.00,
            MatchCount INT NOT NULL DEFAULT 0,
            LastUsedAt DATETIME,
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_financial_import_rule (
                Scac,
                RuleType,
                SourceType,
                VendorKey,
                DescriptionKey,
                Co
            ),
            INDEX idx_financial_import_rules_scac (Scac),
            INDEX idx_financial_import_rules_vendor (Scac, VendorKey),
            INDEX idx_financial_import_rules_expense (ExpenseAccountId)
        )
    """))
    existing_rule_columns = {
        row[0] for row in db.session.execute(text('SHOW COLUMNS FROM financial_import_rules'))
    }
    if 'VendorId' not in existing_rule_columns:
        db.session.execute(text('ALTER TABLE financial_import_rules ADD COLUMN VendorId INT AFTER DescriptionKey'))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS financial_import_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Scac VARCHAR(20) NOT NULL,
            ImportKey VARCHAR(128) NOT NULL,
            SourceFile VARCHAR(255),
            SourceType VARCHAR(30),
            LineNumber INT,
            RecordType VARCHAR(30),
            VendorName VARCHAR(100),
            Description VARCHAR(600),
            Amount VARCHAR(20),
            TransactionDate DATE,
            Ref VARCHAR(50),
            Status VARCHAR(30) NOT NULL DEFAULT 'new',
            BillId INT,
            PaymentId INT,
            LedgerJournalId VARCHAR(100),
            RuleId INT,
            ErrorText VARCHAR(1000),
            RawText TEXT,
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_financial_import_record (Scac, ImportKey),
            INDEX idx_financial_import_records_scac_status (Scac, Status),
            INDEX idx_financial_import_records_bill (BillId),
            INDEX idx_financial_import_records_rule (RuleId)
        )
    """))
    db.session.commit()


def vendor_options():
    return People.query.filter(People.Ptype == 'Vendor').order_by(People.Company).all()


def vendor_row(vendor):
    return {
        'id': vendor.id,
        'company': vendor.Company,
        'email': vendor.Email,
    }


def normalize_match_text(value):
    text_value = ''.join(ch.lower() if ch.isalnum() else ' ' for ch in (value or ''))
    return ' '.join(text_value.split())


def likely_payee_text(payload):
    text_value = clean_text(payload.get('description') or payload.get('vendor_name') or payload.get('company') or '')
    upper_value = text_value.upper()
    for marker in [' DES:', ' ID:', ' INDN:', ' CO ID:', ' DEBIT CARD', ' PURCHASE ']:
        pos = upper_value.find(marker)
        if pos > 0:
            return text_value[:pos]
    return text_value


def suggested_vendor_for_payload(payload):
    payee_text = normalize_match_text(likely_payee_text(payload))
    tx_text = normalize_match_text(' '.join([
        payload.get('vendor_name') or payload.get('company') or '',
        payload.get('description') or '',
        payload.get('raw_text') or '',
    ]))
    best_vendor = None
    best_score = 0
    for vendor in vendor_options():
        vendor_text = normalize_match_text(vendor.Company)
        if not vendor_text:
            continue
        vendor_words = [
            word for word in vendor_text.split()
            if len(word) >= 4 and word not in GENERIC_VENDOR_WORDS
        ]
        matched_words = [word for word in vendor_words if word in payee_text]
        if vendor_text in payee_text:
            score = len(vendor_text)
        elif len(vendor_words) == 1 and matched_words:
            score = len(matched_words[0])
        elif len(matched_words) >= 2:
            score = sum(len(word) for word in matched_words)
        else:
            score = 0
        if score > best_score:
            best_vendor = vendor
            best_score = score
    return best_vendor if best_score >= 5 else None


def selected_vendor(payload):
    vendor_id = payload.get('vendor_id')
    if vendor_id not in [None, '']:
        try:
            vendor = People.query.get(int(vendor_id))
            if vendor is not None and vendor.Ptype == 'Vendor':
                return vendor
        except:
            pass
    vendor_name = clean_text(payload.get('vendor_name') or payload.get('company'), 50)
    if not vendor_name:
        return None
    vendor = People.query.filter(
        (People.Ptype == 'Vendor') &
        (People.Company == vendor_name)
    ).first()
    return vendor


def find_account(payload, id_key, name_key, account_types, company_code=None):
    account_id = payload.get(id_key)
    if account_id not in [None, '']:
        try:
            account = Accounts.query.get(int(account_id))
            if account is not None:
                return account
        except:
            pass

    account_name = clean_text(payload.get(name_key), 50)
    if not account_name:
        return None
    query = Accounts.query.filter(Accounts.Name == account_name)
    if company_code:
        query = query.filter(Accounts.Co == company_code)
    if account_types:
        query = query.filter(Accounts.Type.in_(account_types))
    return query.first()


def rule_keys(payload):
    vendor_key = clean_text(payload.get('vendor_key') or payload.get('vendor_name'), 200).lower()
    description_key = clean_text(payload.get('description_key') or payload.get('description'), 250).lower()
    return vendor_key, description_key


def build_import_key(payload):
    import_key = clean_text(payload.get('import_key'), 128)
    if import_key:
        return import_key
    parts = [
        scac,
        clean_text(payload.get('source_file')),
        str(payload.get('line_number') or ''),
        clean_text(payload.get('vendor_name')),
        clean_text(payload.get('description')),
        clean_text(payload.get('amount')),
        clean_text(payload.get('bill_date') or payload.get('date')),
        clean_text(payload.get('ref')),
    ]
    return hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()


def existing_import_record(import_key):
    return db.session.execute(
        text("""
            SELECT id, Status, BillId, LedgerJournalId, ErrorText
            FROM financial_import_records
            WHERE Scac = :scac AND ImportKey = :import_key
            LIMIT 1
        """),
        {'scac': scac, 'import_key': import_key},
    ).mappings().first()


def create_import_record(import_key, payload, status, error_text=None):
    transaction_date = parse_date(
        payload.get('payment_date') or payload.get('bill_date') or payload.get('date'),
        'date',
        [],
    )
    db.session.execute(
        text("""
            INSERT INTO financial_import_records
                (Scac, ImportKey, SourceFile, SourceType, LineNumber, RecordType,
                 VendorName, Description, Amount, TransactionDate, Ref, Status,
                 ErrorText, RawText, CreatedAt, UpdatedAt)
            VALUES
                (:scac, :import_key, :source_file, :source_type, :line_number,
                 :record_type, :vendor_name, :description, :amount,
                 :transaction_date, :ref, :status, :error_text, :raw_text,
                 :created_at, :updated_at)
        """),
        {
            'scac': scac,
            'import_key': import_key,
            'source_file': clean_text(payload.get('source_file'), 255),
            'source_type': clean_text(payload.get('source_type'), 30),
            'line_number': payload.get('line_number'),
            'record_type': clean_text(payload.get('record_type') or 'bill_payment', 30),
            'vendor_name': clean_text(payload.get('vendor_name'), 100),
            'description': clean_text(payload.get('description'), 600),
            'amount': clean_text(payload.get('amount'), 20),
            'transaction_date': transaction_date.date() if transaction_date is not None else None,
            'ref': clean_text(payload.get('ref'), 50),
            'status': status,
            'error_text': clean_text(error_text, 1000),
            'raw_text': payload.get('raw_text'),
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now(),
        },
    )
    db.session.flush()
    return db.session.execute(text('SELECT LAST_INSERT_ID()')).scalar()


def update_import_record(record_id, status, bill=None, rule_id=None, error_text=None):
    db.session.execute(
        text("""
            UPDATE financial_import_records
            SET Status = :status,
                BillId = :bill_id,
                PaymentId = :payment_id,
                LedgerJournalId = :ledger_journal_id,
                RuleId = :rule_id,
                ErrorText = :error_text,
                UpdatedAt = :updated_at
            WHERE id = :record_id
        """),
        {
            'status': status,
            'bill_id': bill.id if bill is not None else None,
            'payment_id': bill.id if bill is not None and status == 'imported' else None,
            'ledger_journal_id': f'PAYBILL-{bill.Jo}' if bill is not None and status == 'imported' else None,
            'rule_id': rule_id,
            'error_text': clean_text(error_text, 1000),
            'updated_at': datetime.datetime.now(),
            'record_id': record_id,
        },
    )
    db.session.flush()


def upsert_rule(payload, vendor, expense_account, pay_account, company_code):
    vendor_key, description_key = rule_keys(payload)
    if not vendor_key and not description_key:
        return None
    now = datetime.datetime.now()
    source_type = clean_text(payload.get('source_type'), 30)
    params = {
        'scac': scac,
        'rule_type': 'bill',
        'source_type': source_type,
        'vendor_key': vendor_key,
        'description_key': description_key,
        'vendor_id': vendor.id,
        'vendor_name': clean_text(vendor.Company, 100),
        'expense_account_id': expense_account.id,
        'expense_account_name': expense_account.Name,
        'pay_account_id': pay_account.id,
        'pay_account_name': pay_account.Name,
        'co': company_code,
        'account_type': expense_account.Type,
        'account_category': expense_account.Category,
        'account_subcategory': expense_account.Subcategory,
        'now': now,
    }
    db.session.execute(
        text("""
            INSERT INTO financial_import_rules
                (Scac, RuleType, SourceType, VendorKey, DescriptionKey,
                 VendorId, VendorName, ExpenseAccountId, ExpenseAccountName,
                 PayAccountId, PayAccountName, Co, AccountType,
                 AccountCategory, AccountSubcategory, MatchCount,
                 LastUsedAt, CreatedAt, UpdatedAt)
            VALUES
                (:scac, :rule_type, :source_type, :vendor_key, :description_key,
                 :vendor_id, :vendor_name, :expense_account_id, :expense_account_name,
                 :pay_account_id, :pay_account_name, :co, :account_type,
                 :account_category, :account_subcategory, 1, :now, :now, :now)
            ON DUPLICATE KEY UPDATE
                VendorId = VALUES(VendorId),
                VendorName = VALUES(VendorName),
                ExpenseAccountId = VALUES(ExpenseAccountId),
                ExpenseAccountName = VALUES(ExpenseAccountName),
                PayAccountId = VALUES(PayAccountId),
                PayAccountName = VALUES(PayAccountName),
                AccountType = VALUES(AccountType),
                AccountCategory = VALUES(AccountCategory),
                AccountSubcategory = VALUES(AccountSubcategory),
                MatchCount = MatchCount + 1,
                LastUsedAt = VALUES(LastUsedAt),
                UpdatedAt = VALUES(UpdatedAt)
        """),
        params,
    )
    row = db.session.execute(
        text("""
            SELECT id FROM financial_import_rules
            WHERE Scac = :scac
              AND RuleType = :rule_type
              AND SourceType = :source_type
              AND VendorKey = :vendor_key
              AND DescriptionKey = :description_key
              AND Co = :co
            LIMIT 1
        """),
        params,
    ).first()
    return row[0] if row else None


def validate_bill_payment_payload(payload):
    errors = []
    bill_date = parse_date(payload.get('bill_date') or payload.get('date'), 'bill_date', errors)
    payment_date = parse_date(payload.get('payment_date') or payload.get('paid_date') or bill_date, 'payment_date', errors, bill_date)
    due_date = parse_date(payload.get('due_date') or bill_date, 'due_date', errors, bill_date)
    vendor_name = clean_text(payload.get('vendor_name') or payload.get('company'), 50)
    vendor = selected_vendor(payload)
    if vendor is None:
        errors.append('Choose a vendor from the vendor list.')
    try:
        amount = money_string(payload.get('amount') or payload.get('bAmount'))
        if Decimal(amount) == Decimal('0.00'):
            errors.append('amount must not be zero.')
    except:
        amount = '0.00'
        errors.append('amount is invalid.')

    company_code = clean_text(payload.get('co') or payload.get('company_code'), 9)
    pay_account = find_account(payload, 'pay_account_id', 'pay_account_name', PAYMENT_TYPES, company_code or None)
    if pay_account is not None and not company_code:
        company_code = pay_account.Co
    expense_account = find_account(payload, 'expense_account_id', 'expense_account_name', EXPENSE_TYPES, company_code or None)
    if expense_account is not None and not company_code:
        company_code = expense_account.Co
    if not company_code:
        errors.append('co or company_code is required when account names are ambiguous.')
    if pay_account is None:
        errors.append('pay_account_name or pay_account_id must match a payment account.')
    if expense_account is None:
        errors.append('expense_account_name or expense_account_id must match an expense account.')
    if pay_account is not None and expense_account is not None and pay_account.Co != expense_account.Co:
        errors.append(f'Payment account company {pay_account.Co} does not match expense account company {expense_account.Co}.')
    if pay_account is not None and company_code and pay_account.Co != company_code:
        errors.append(f'Payment account company {pay_account.Co} does not match {company_code}.')
    if expense_account is not None and company_code and expense_account.Co != company_code:
        errors.append(f'Expense account company {expense_account.Co} does not match {company_code}.')
    return errors, vendor, amount, bill_date, payment_date, due_date, company_code, pay_account, expense_account


def create_paid_bill_from_import(payload, username=None):
    ensure_financial_import_tables()
    import_key = build_import_key(payload)
    existing = existing_import_record(import_key)
    if existing and existing['Status'] == 'imported':
        return {
            'status': 'duplicate',
            'import_key': import_key,
            'record_id': existing['id'],
            'bill_id': existing['BillId'],
            'ledger_journal_id': existing['LedgerJournalId'],
        }, 200

    errors, vendor, amount, bill_date, payment_date, due_date, company_code, pay_account, expense_account = validate_bill_payment_payload(payload)
    if errors:
        if not existing:
            try:
                record_id = create_import_record(import_key, payload, 'error', '; '.join(errors))
                db.session.commit()
            except:
                db.session.rollback()
                record_id = None
        else:
            record_id = existing['id']
            update_import_record(record_id, 'error', error_text='; '.join(errors))
            db.session.commit()
        return {'status': 'error', 'import_key': import_key, 'record_id': record_id, 'errors': errors}, 400

    record_id = existing['id'] if existing else create_import_record(import_key, payload, 'processing')
    try:
        ref = clean_text(payload.get('ref') or payload.get('reference'), 50)
        memo = clean_text(payload.get('memo') or expense_account.Name, 50)
        description = clean_text(payload.get('description') or memo, 600)
        payment_method = clean_text(payload.get('payment_method') or payload.get('pMeth') or 'Imported', 45)
        jo = newjo(f'{company_code}B', bill_date.strftime('%Y-%m-%d'))
        bill = Bills(
            Jo=jo,
            Pid=vendor.id,
            Company=vendor.Company,
            Memo=memo,
            Description=description,
            bAmount=amount,
            Status='Unpaid',
            Scache=0,
            Source=clean_text(payload.get('source') or 'FinancialImport', 75),
            Ref=ref,
            Date=bill_date,
            pDate=payment_date,
            pAmount=amount,
            pMulti=None,
            pAccount=pay_account.Name,
            bAccount=expense_account.Name,
            bType=expense_account.Type,
            bCat=expense_account.Category,
            bSubcat=expense_account.Subcategory,
            Link=None,
            User=clean_text(username or payload.get('user') or 'api_import', 25),
            Co=company_code,
            Temp1='FinancialImport',
            Temp2=import_key,
            Recurring=0,
            dDate=due_date,
            pAmount2='0.00',
            pDate2=None,
            Proof=clean_text(payload.get('proof'), 45) or None,
            Check=clean_text(payload.get('check'), 45) or None,
            Ccache=0,
            QBi=0,
            iflag=0,
            PmtList=amount,
            PacctList=pay_account.Name,
            RefList=ref,
            MemoList=memo,
            PdateList=payment_date.strftime('%Y-%m-%d'),
            CheckList=clean_text(payload.get('check'), 200) or None,
            MethList=payment_method,
            Pcache=0,
            pMeth=payment_method,
        )
        db.session.add(bill)
        db.session.commit()

        ledger_errors = gledger_write(['newbill'], bill.Jo, bill.bAccount, bill.pAccount, 0)
        if ledger_errors:
            update_import_record(record_id, 'error', bill=bill, error_text='; '.join(ledger_errors))
            db.session.commit()
            return {'status': 'error', 'import_key': import_key, 'record_id': record_id, 'bill_id': bill.id, 'errors': ledger_errors}, 400

        ledger_errors = gledger_write(['paybill'], bill.Jo, bill.bAccount, bill.pAccount, 0)
        if ledger_errors:
            bill.Status = 'Unpaid'
            update_import_record(record_id, 'error', bill=bill, error_text='; '.join(ledger_errors))
            db.session.commit()
            return {'status': 'error', 'import_key': import_key, 'record_id': record_id, 'bill_id': bill.id, 'errors': ledger_errors}, 400

        bill.Status = 'Paid'
        rule_id = upsert_rule(payload, vendor, expense_account, pay_account, company_code)
        update_import_record(record_id, 'imported', bill=bill, rule_id=rule_id)
        db.session.commit()
        return {
            'status': 'imported',
            'import_key': import_key,
            'record_id': record_id,
            'bill_id': bill.id,
            'jo': bill.Jo,
            'ledger_journal_id': f'PAYBILL-{bill.Jo}',
            'rule_id': rule_id,
        }, 201
    except Exception as exc:
        db.session.rollback()
        try:
            if existing:
                update_import_record(record_id, 'error', error_text=str(exc))
            else:
                record_id = create_import_record(import_key, payload, 'error', str(exc))
            db.session.commit()
        except:
            db.session.rollback()
        return {'status': 'error', 'import_key': import_key, 'record_id': record_id, 'errors': [str(exc)]}, 500


def import_paid_bill_payload(data, username=None):
    if not isinstance(data, dict):
        return {'status': 'error', 'errors': ['JSON object is required.']}, 400
    items = data.get('items')
    if items is None:
        items = [data]
    if not isinstance(items, list) or not items:
        return {'status': 'error', 'errors': ['items must be a non-empty list.']}, 400

    results = []
    status_code = 201
    for item in items:
        result, item_status = create_paid_bill_from_import(item, username=username)
        results.append(result)
        if item_status >= 500:
            status_code = 500
        elif item_status >= 400 and status_code < 500:
            status_code = 207 if len(items) > 1 else item_status
        elif item_status == 200 and status_code == 201:
            status_code = 200
    return {'status': 'completed', 'results': results}, status_code


def financial_import_account_options(company_code=None):
    ensure_financial_import_tables()
    company_code = clean_text(company_code, 9)
    expense_query = Accounts.query.filter(Accounts.Type.in_(EXPENSE_TYPES))
    payment_query = Accounts.query.filter(Accounts.Type.in_(PAYMENT_TYPES))
    if company_code:
        expense_query = expense_query.filter(Accounts.Co == company_code)
        payment_query = payment_query.filter(Accounts.Co == company_code)

    def account_row(account):
        return {
            'id': account.id,
            'name': account.Name,
            'type': account.Type,
            'category': account.Category,
            'subcategory': account.Subcategory,
            'co': account.Co,
        }

    return {
        'expense_accounts': [
            account_row(account)
            for account in expense_query.order_by(Accounts.Co, Accounts.Category, Accounts.Name).all()
        ],
        'payment_accounts': [
            account_row(account)
            for account in payment_query.order_by(Accounts.Co, Accounts.Name).all()
        ],
        'vendors': [vendor_row(vendor) for vendor in vendor_options()],
    }


def bill_payment_candidates(payload):
    errors = []
    company_code = clean_text(payload.get('co') or payload.get('company_code'), 9)
    payment_date = parse_date(payload.get('payment_date') or payload.get('paid_date') or payload.get('date'), 'date', errors)
    if payment_date is None:
        return []
    try:
        amount = money_decimal(payload.get('amount') or payload.get('pAmount'))
    except:
        return []
    pay_account = find_account(payload, 'pay_account_id', 'pay_account_name', PAYMENT_TYPES, company_code or None)
    start = payment_date - datetime.timedelta(days=10)
    end = payment_date + datetime.timedelta(days=10)
    query = Bills.query.filter(Bills.pDate >= start).filter(Bills.pDate <= end)
    if company_code:
        query = query.filter(Bills.Co == company_code)
    if pay_account is not None:
        query = query.filter(Bills.pAccount == pay_account.Name)
    rows = query.order_by(Bills.pDate.desc(), Bills.id.desc()).limit(200).all()
    rows = [
        bill for bill in rows
        if bill.Status == 'Paid' and money_decimal(bill.pAmount) == amount
    ][:20]
    payment_day = payment_date.date()
    rows = sorted(
        rows,
        key=lambda bill: (
            abs(((bill.pDate.date() if isinstance(bill.pDate, datetime.datetime) else bill.pDate) - payment_day).days)
            if bill.pDate else 9999,
            -(bill.id or 0),
        )
    )
    return [
        {
            'id': bill.id,
            'jo': bill.Jo,
            'vendor_id': bill.Pid,
            'vendor_name': bill.Company,
            'payment_account': bill.pAccount,
            'expense_account': bill.bAccount,
            'amount': bill.pAmount,
            'payment_date': bill.pDate.strftime('%Y-%m-%d') if bill.pDate else '',
        }
        for bill in rows
    ]


def lookup_financial_import_rule(payload):
    ensure_financial_import_tables()
    if not isinstance(payload, dict):
        return {'status': 'error', 'errors': ['JSON object is required.']}, 400
    vendor_key, description_key = rule_keys(payload)
    source_type = clean_text(payload.get('source_type'), 30)
    company_code = clean_text(payload.get('co') or payload.get('company_code'), 9)
    params = {
        'scac': scac,
        'rule_type': clean_text(payload.get('rule_type') or 'bill', 30),
        'source_type': source_type,
        'vendor_key': vendor_key,
        'description_key': description_key,
        'co': company_code,
    }
    rows = db.session.execute(
        text("""
            SELECT *
            FROM financial_import_rules
            WHERE Scac = :scac
              AND RuleType = :rule_type
              AND (:source_type = '' OR SourceType = :source_type)
              AND (:co = '' OR Co = :co)
              AND (
                    (VendorKey = :vendor_key AND DescriptionKey = :description_key)
                 OR (VendorKey = :vendor_key AND DescriptionKey = '')
                 OR (VendorKey = :vendor_key)
              )
            ORDER BY
                CASE
                    WHEN VendorKey = :vendor_key AND DescriptionKey = :description_key THEN 1
                    WHEN VendorKey = :vendor_key AND DescriptionKey = '' THEN 2
                    ELSE 3
                END,
                MatchCount DESC,
                LastUsedAt DESC
            LIMIT 1
        """),
        params,
    ).mappings().first()
    vendor_suggestion = suggested_vendor_for_payload(payload)
    bill_matches = bill_payment_candidates(payload)
    if rows is None:
        return {
            'status': 'not_found',
            'vendor_suggestion': vendor_row(vendor_suggestion) if vendor_suggestion else None,
            'bill_payment_matches': bill_matches,
        }, 404
    return {
        'status': 'matched',
        'rule': {
            'id': rows['id'],
            'vendor_id': rows['VendorId'],
            'vendor_name': rows['VendorName'],
            'expense_account_id': rows['ExpenseAccountId'],
            'expense_account_name': rows['ExpenseAccountName'],
            'pay_account_id': rows['PayAccountId'],
            'pay_account_name': rows['PayAccountName'],
            'income_account_id': rows['IncomeAccountId'],
            'income_account_name': rows['IncomeAccountName'],
            'co': rows['Co'],
            'account_type': rows['AccountType'],
            'account_category': rows['AccountCategory'],
            'account_subcategory': rows['AccountSubcategory'],
            'confidence': float(rows['Confidence'] or 0),
            'match_count': rows['MatchCount'],
        },
        'vendor_suggestion': vendor_row(vendor_suggestion) if vendor_suggestion else None,
        'bill_payment_matches': bill_matches,
    }, 200
