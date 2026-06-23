import datetime
import json
from decimal import Decimal, ROUND_HALF_UP

import requests
from sqlalchemy import text

from webapp import db
from webapp.CCC_system_setup import apikeys, scac
from webapp.models import Accounts, Bills, People, PlaidAccount, PlaidItem, PlaidTransaction, PlaidVendorRule
from webapp.class8_tasks_gledger import gledger_write, post_balanced_journal
from webapp.viewfuncs import newjo


PLAID_ENV_URLS = {
    'sandbox': 'https://sandbox.plaid.com',
    'development': 'https://development.plaid.com',
    'production': 'https://production.plaid.com',
}


def cents(value):
    if value is None:
        return None
    return int((Decimal(str(value)) * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value, '%Y-%m-%d').date()
    except:
        return None


def parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    except:
        return None


def plaid_config():
    client_id = apikeys.get('plaid_client_id') or apikeys.get('PLAID_CLIENT_ID')
    secret = apikeys.get('plaid_secret') or apikeys.get('PLAID_SECRET')
    env = (apikeys.get('plaid_env') or apikeys.get('PLAID_ENV') or 'sandbox').lower()
    base_url = PLAID_ENV_URLS.get(env, PLAID_ENV_URLS['sandbox'])
    return client_id, secret, env, base_url


def plaid_ready():
    client_id, secret, env, base_url = plaid_config()
    return bool(client_id and secret), env


def ensure_plaid_tables():
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS plaid_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Scac VARCHAR(20) NOT NULL,
            ItemId VARCHAR(128) NOT NULL UNIQUE,
            AccessToken VARCHAR(512) NOT NULL,
            InstitutionId VARCHAR(64),
            InstitutionName VARCHAR(150),
            Products TEXT,
            AvailableProducts TEXT,
            TransactionsCursor TEXT,
            LastSyncAt DATETIME,
            LastSuccessfulUpdate DATETIME,
            ItemError TEXT,
            Active BOOLEAN NOT NULL DEFAULT TRUE,
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_plaid_items_scac (Scac)
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS plaid_accounts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            PlaidItemId INT NOT NULL,
            AccountId VARCHAR(128) NOT NULL UNIQUE,
            LocalAccountId INT,
            Name VARCHAR(150),
            OfficialName VARCHAR(200),
            Mask VARCHAR(10),
            Type VARCHAR(45),
            Subtype VARCHAR(45),
            CurrentBalance INT,
            AvailableBalance INT,
            IsoCurrencyCode VARCHAR(10),
            Active BOOLEAN NOT NULL DEFAULT TRUE,
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_plaid_accounts_item (PlaidItemId),
            INDEX idx_plaid_accounts_local (LocalAccountId)
        )
    """))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS plaid_transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            TransactionId VARCHAR(128) NOT NULL UNIQUE,
            PlaidItemId INT NOT NULL,
            PlaidAccountId INT NOT NULL,
            LocalAccountId INT,
            Date DATE,
            AuthorizedDate DATE,
            Name VARCHAR(400),
            MerchantName VARCHAR(200),
            Amount INT,
            Pending BOOLEAN NOT NULL DEFAULT FALSE,
            PaymentChannel VARCHAR(45),
            TransactionType VARCHAR(45),
            CategoryPrimary VARCHAR(100),
            CategoryDetailed VARCHAR(150),
            Status VARCHAR(30) NOT NULL DEFAULT 'new',
            BillId INT,
            GledgerId INT,
            ReviewNote VARCHAR(250),
            ReviewedAt DATETIME,
            ReviewedBy VARCHAR(30),
            RawJson TEXT,
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_plaid_transactions_item (PlaidItemId),
            INDEX idx_plaid_transactions_account (PlaidAccountId),
            INDEX idx_plaid_transactions_local (LocalAccountId),
            INDEX idx_plaid_transactions_date (Date)
        )
    """))
    existing_columns = {
        row[0] for row in db.session.execute(text('SHOW COLUMNS FROM plaid_transactions'))
    }
    for name, definition in {
        'BillId': 'INT',
        'ReviewNote': 'VARCHAR(250)',
        'ReviewedAt': 'DATETIME',
        'ReviewedBy': 'VARCHAR(30)',
    }.items():
        if name not in existing_columns:
            db.session.execute(text(f'ALTER TABLE plaid_transactions ADD COLUMN {name} {definition}'))
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS plaid_vendor_rules (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Scac VARCHAR(20) NOT NULL,
            MerchantKey VARCHAR(200) NOT NULL,
            VendorName VARCHAR(50),
            ExpenseAccountId INT,
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_plaid_vendor_rule (Scac, MerchantKey),
            INDEX idx_plaid_vendor_rules_scac (Scac)
        )
    """))
    db.session.commit()


def plaid_post(endpoint, payload):
    client_id, secret, env, base_url = plaid_config()
    if not client_id or not secret:
        raise RuntimeError('Plaid client id and secret are not configured.')
    request_payload = {
        'client_id': client_id,
        'secret': secret,
    }
    request_payload.update(payload)
    response = requests.post(
        f'{base_url}{endpoint}',
        json=request_payload,
        headers={'Content-Type': 'application/json'},
        timeout=30,
    )
    try:
        data = response.json()
    except:
        data = {'error_message': response.text}
    if response.status_code >= 400:
        message = data.get('error_message') or data.get('display_message') or response.text
        raise RuntimeError(f'Plaid {endpoint} failed: {message}')
    return data


def create_link_token(user_id, username):
    client_user_id = f'{scac}-{user_id or username}'
    return plaid_post('/link/token/create', {
        'client_name': f'{scac} Class8',
        'country_codes': ['US'],
        'language': 'en',
        'user': {'client_user_id': client_user_id},
        'products': ['transactions'],
    })


def exchange_public_token(public_token):
    data = plaid_post('/item/public_token/exchange', {'public_token': public_token})
    return data['access_token'], data['item_id']


def get_accounts(access_token):
    return plaid_post('/accounts/get', {'access_token': access_token})


def get_item(access_token):
    return plaid_post('/item/get', {'access_token': access_token})


def upsert_item_from_exchange(access_token, item_id):
    ensure_plaid_tables()
    accounts_data = get_accounts(access_token)
    item_data = accounts_data.get('item', {})
    item = PlaidItem.query.filter_by(ItemId=item_id).first()
    now = datetime.datetime.utcnow()
    if item is None:
        item = PlaidItem(
            Scac=scac,
            ItemId=item_id,
            AccessToken=access_token,
            CreatedAt=now,
            UpdatedAt=now,
        )
        db.session.add(item)
        db.session.flush()

    item.AccessToken = access_token
    item.Scac = scac
    item.InstitutionId = item_data.get('institution_id')
    item.InstitutionName = item_data.get('institution_name')
    item.Products = json.dumps(item_data.get('products') or [])
    item.AvailableProducts = json.dumps(item_data.get('available_products') or [])
    item.ItemError = json.dumps(item_data.get('error')) if item_data.get('error') else None
    item.Active = True
    item.UpdatedAt = now
    db.session.commit()

    upsert_accounts(item, accounts_data.get('accounts') or [])
    return item


def upsert_accounts(item, accounts):
    now = datetime.datetime.utcnow()
    seen = set()
    for acct in accounts:
        account_id = acct.get('account_id')
        if not account_id:
            continue
        seen.add(account_id)
        row = PlaidAccount.query.filter_by(AccountId=account_id).first()
        if row is None:
            row = PlaidAccount(
                PlaidItemId=item.id,
                AccountId=account_id,
                CreatedAt=now,
                UpdatedAt=now,
            )
            db.session.add(row)

        balances = acct.get('balances') or {}
        row.PlaidItemId = item.id
        row.Name = acct.get('name')
        row.OfficialName = acct.get('official_name')
        row.Mask = acct.get('mask')
        row.Type = acct.get('type')
        row.Subtype = acct.get('subtype')
        row.CurrentBalance = cents(balances.get('current'))
        row.AvailableBalance = cents(balances.get('available'))
        row.IsoCurrencyCode = balances.get('iso_currency_code')
        row.Active = True
        row.UpdatedAt = now

    existing = PlaidAccount.query.filter_by(PlaidItemId=item.id).all()
    for row in existing:
        if row.AccountId not in seen:
            row.Active = False
            row.UpdatedAt = now
    db.session.commit()


def update_item_status(item):
    data = get_item(item.AccessToken)
    now = datetime.datetime.utcnow()
    item_data = data.get('item') or {}
    status = data.get('status') or {}
    transactions_status = status.get('transactions') or {}
    item.InstitutionId = item_data.get('institution_id')
    item.InstitutionName = item_data.get('institution_name')
    item.Products = json.dumps(item_data.get('products') or [])
    item.AvailableProducts = json.dumps(item_data.get('available_products') or [])
    item.ItemError = json.dumps(item_data.get('error')) if item_data.get('error') else None
    item.LastSuccessfulUpdate = parse_datetime(transactions_status.get('last_successful_update'))
    item.UpdatedAt = now
    db.session.commit()
    return data


def sync_item_transactions(item):
    ensure_plaid_tables()
    added_count = modified_count = removed_count = 0
    cursor = item.TransactionsCursor
    has_more = True
    latest_cursor = cursor

    while has_more:
        payload = {
            'access_token': item.AccessToken,
            'count': 500,
        }
        if latest_cursor:
            payload['cursor'] = latest_cursor
        data = plaid_post('/transactions/sync', payload)
        upsert_accounts(item, data.get('accounts') or [])

        for tx in data.get('added') or []:
            upsert_transaction(item, tx, removed=False)
            added_count += 1
        for tx in data.get('modified') or []:
            upsert_transaction(item, tx, removed=False)
            modified_count += 1
        for tx in data.get('removed') or []:
            mark_transaction_removed(tx)
            removed_count += 1

        latest_cursor = data.get('next_cursor') or latest_cursor
        has_more = bool(data.get('has_more'))

    item.TransactionsCursor = latest_cursor
    item.LastSyncAt = datetime.datetime.utcnow()
    item.UpdatedAt = datetime.datetime.utcnow()
    db.session.commit()
    return added_count, modified_count, removed_count


def upsert_transaction(item, tx, removed=False):
    transaction_id = tx.get('transaction_id')
    account_id = tx.get('account_id')
    plaid_account = PlaidAccount.query.filter_by(AccountId=account_id).first()
    if transaction_id is None or plaid_account is None:
        return

    now = datetime.datetime.utcnow()
    row = PlaidTransaction.query.filter_by(TransactionId=transaction_id).first()
    if row is None:
        row = PlaidTransaction(
            TransactionId=transaction_id,
            PlaidItemId=item.id,
            PlaidAccountId=plaid_account.id,
            CreatedAt=now,
            UpdatedAt=now,
        )
        db.session.add(row)

    pfc = tx.get('personal_finance_category') or {}
    row.PlaidItemId = item.id
    row.PlaidAccountId = plaid_account.id
    row.LocalAccountId = plaid_account.LocalAccountId
    row.Date = parse_date(tx.get('date'))
    row.AuthorizedDate = parse_date(tx.get('authorized_date'))
    row.Name = tx.get('name')
    row.MerchantName = tx.get('merchant_name')
    row.Amount = cents(tx.get('amount'))
    row.Pending = bool(tx.get('pending'))
    row.PaymentChannel = tx.get('payment_channel')
    row.TransactionType = tx.get('transaction_type')
    row.CategoryPrimary = pfc.get('primary')
    row.CategoryDetailed = pfc.get('detailed')
    row.Status = 'removed' if removed else (row.Status if row.Status not in [None, 'removed'] else 'new')
    row.RawJson = json.dumps(tx)
    row.UpdatedAt = now
    db.session.commit()


def mark_transaction_removed(tx):
    transaction_id = tx.get('transaction_id')
    if not transaction_id:
        return
    row = PlaidTransaction.query.filter_by(TransactionId=transaction_id).first()
    if row is not None:
        row.Status = 'removed'
        row.UpdatedAt = datetime.datetime.utcnow()
        db.session.commit()


def account_mapping_options():
    return Accounts.query.filter(Accounts.Type.in_(['Bank', 'Credit Card'])).order_by(Accounts.Co, Accounts.Name).all()


def plaid_expense_account_options():
    return (
        Accounts.query
        .filter(Accounts.Type.in_(['Expense', 'Cost of Goods Sold', 'Other Expense']))
        .order_by(Accounts.Co, Accounts.Category, Accounts.Name)
        .all()
    )


def plaid_transfer_account_options():
    return (
        Accounts.query
        .filter(Accounts.Type.in_(['Bank', 'Exch', 'Credit Card']))
        .order_by(Accounts.Co, Accounts.Name)
        .all()
    )


def merchant_key_for_transaction(tx):
    text = (tx.MerchantName or tx.Name or '').strip().lower()
    return ' '.join(text.split())[:200]


def plaid_vendor_rule_lookup(transactions):
    ensure_plaid_tables()
    rules = PlaidVendorRule.query.filter_by(Scac=scac).all()
    by_key = {rule.MerchantKey: rule for rule in rules}
    lookup = {}
    for tx in transactions:
        key = merchant_key_for_transaction(tx)
        if key in by_key:
            lookup[tx.id] = by_key[key]
    return lookup


def save_vendor_rule(tx, vendor_name, expense_account_id):
    key = merchant_key_for_transaction(tx)
    if not key or not expense_account_id:
        return
    now = datetime.datetime.utcnow()
    rule = PlaidVendorRule.query.filter_by(Scac=scac, MerchantKey=key).first()
    if rule is None:
        rule = PlaidVendorRule(
            Scac=scac,
            MerchantKey=key,
            CreatedAt=now,
        )
        db.session.add(rule)
    rule.VendorName = (vendor_name or tx.MerchantName or tx.Name or '')[:50]
    rule.ExpenseAccountId = expense_account_id
    rule.UpdatedAt = now
    db.session.commit()


def plaid_dashboard_data():
    ensure_plaid_tables()
    items = PlaidItem.query.filter_by(Scac=scac).order_by(PlaidItem.id.desc()).all()
    item_ids = [item.id for item in items]
    plaid_accounts = []
    transactions = []
    if item_ids:
        plaid_accounts = PlaidAccount.query.filter(PlaidAccount.PlaidItemId.in_(item_ids)).order_by(PlaidAccount.id).all()
        transactions = (
            PlaidTransaction.query
            .filter(PlaidTransaction.PlaidItemId.in_(item_ids))
            .order_by(PlaidTransaction.Date.desc(), PlaidTransaction.id.desc())
            .limit(200)
            .all()
        )
    local_accounts = {acct.id: acct for acct in Accounts.query.all()}
    plaid_account_lookup = {acct.id: acct for acct in plaid_accounts}
    return items, plaid_accounts, transactions, local_accounts, plaid_account_lookup, account_mapping_options()


def plaid_review_transactions():
    ensure_plaid_tables()
    items = PlaidItem.query.filter_by(Scac=scac).all()
    item_ids = [item.id for item in items]
    if not item_ids:
        return []
    return (
        PlaidTransaction.query
        .filter(PlaidTransaction.PlaidItemId.in_(item_ids))
        .filter(PlaidTransaction.Status == 'new')
        .filter(PlaidTransaction.LocalAccountId.isnot(None))
        .filter(PlaidTransaction.Pending == False)
        .order_by(PlaidTransaction.Date.desc(), PlaidTransaction.id.desc())
        .limit(100)
        .all()
    )


def plaid_processed_transactions():
    ensure_plaid_tables()
    items = PlaidItem.query.filter_by(Scac=scac).all()
    item_ids = [item.id for item in items]
    if not item_ids:
        return []
    return (
        PlaidTransaction.query
        .filter(PlaidTransaction.PlaidItemId.in_(item_ids))
        .filter(PlaidTransaction.Status.in_(['bill_created', 'bill_matched', 'transfer_created', 'ignored']))
        .order_by(PlaidTransaction.ReviewedAt.desc(), PlaidTransaction.Date.desc(), PlaidTransaction.id.desc())
        .limit(100)
        .all()
    )


def plaid_bill_match_options(transactions):
    options = {}
    for tx in transactions:
        if not tx.LocalAccountId or not tx.Amount or tx.Amount <= 0:
            options[tx.id] = []
            continue
        bank = Accounts.query.get(tx.LocalAccountId)
        if bank is None or tx.Date is None:
            options[tx.id] = []
            continue
        amount = f'{tx.Amount / 100:.2f}'
        start = datetime.datetime.combine(tx.Date - datetime.timedelta(days=10), datetime.time.min)
        end = datetime.datetime.combine(tx.Date + datetime.timedelta(days=10), datetime.time.max)
        options[tx.id] = (
            Bills.query
            .filter(Bills.Co == bank.Co)
            .filter(Bills.pAccount == bank.Name)
            .filter(Bills.pAmount == amount)
            .filter(Bills.pDate >= start)
            .filter(Bills.pDate <= end)
            .order_by(Bills.pDate.desc(), Bills.id.desc())
            .limit(20)
            .all()
        )
    return options


def get_or_create_vendor(name):
    vendor_name = (name or '').strip()[:50] or 'Plaid Vendor'
    vendor = People.query.filter(
        (People.Ptype == 'Vendor') &
        (People.Company == vendor_name)
    ).first()
    if vendor is not None:
        return vendor

    parts = vendor_name.split()
    first = parts[0] if parts else ''
    last = parts[-1] if len(parts) > 1 else ''
    middle = ' '.join(parts[1:-1]) if len(parts) > 2 else ''
    vendor = People(
        Ptype='Vendor',
        Company=vendor_name,
        First=first,
        Middle=middle,
        Last=last,
        Addr1=None,
        Addr2=None,
        Addr3=None,
        Idtype=None,
        Idnumber=None,
        Telephone=None,
        Email=None,
        Associate1=None,
        Associate2=None,
        Temp1='Plaid',
        Temp2=None,
        Date1=datetime.datetime.now(),
        Date2=None,
        Source=vendor_name,
        Accountid=None,
        Saljp=None,
        Saloa=None,
        Salap=None,
    )
    db.session.add(vendor)
    db.session.flush()
    return vendor


def ignore_plaid_transaction(transaction_id, username=None, note=None):
    ensure_plaid_tables()
    tx = PlaidTransaction.query.get(transaction_id)
    if tx is None:
        return ['Plaid transaction not found.']
    tx.Status = 'ignored'
    tx.ReviewNote = (note or 'Ignored during Plaid review')[:250]
    tx.ReviewedAt = datetime.datetime.utcnow()
    tx.ReviewedBy = (username or '')[:30] or None
    tx.UpdatedAt = datetime.datetime.utcnow()
    db.session.commit()
    return []


def match_plaid_transaction_to_bill(transaction_id, bill_id, expense_account_id=None, vendor_name=None, username=None):
    ensure_plaid_tables()
    tx = PlaidTransaction.query.get(transaction_id)
    bill = Bills.query.get(bill_id)
    if tx is None:
        return ['Plaid transaction not found.']
    if bill is None:
        return ['Choose an existing bill payment to match.']
    if tx.Status != 'new':
        return [f'Plaid transaction is already marked {tx.Status}.']
    if not tx.LocalAccountId:
        return ['Map this Plaid account before matching a bill payment.']

    bank = Accounts.query.get(tx.LocalAccountId)
    if bank is None:
        return ['Mapped bank account could not be found.']
    if bill.Co != bank.Co:
        return [f'Bill company {bill.Co} does not match payment account company {bank.Co}.']
    if bill.pAccount != bank.Name:
        return [f'Bill payment account {bill.pAccount} does not match Plaid account {bank.Name}.']
    if cents(bill.pAmount) != tx.Amount:
        return ['Bill payment amount does not match the Plaid transaction amount.']

    tx.Status = 'bill_matched'
    tx.BillId = bill.id
    tx.GledgerId = bill.id
    tx.ReviewNote = f'Matched bill {bill.Jo}'[:250]
    tx.ReviewedAt = datetime.datetime.utcnow()
    tx.ReviewedBy = (username or '')[:30] or None
    tx.UpdatedAt = datetime.datetime.utcnow()
    db.session.commit()

    try:
        expense_account_id = int(expense_account_id)
    except:
        expense_account_id = None
    if expense_account_id:
        save_vendor_rule(tx, vendor_name or bill.Company, expense_account_id)
    return []


def is_transfer_endpoint_account(account):
    if account is None or account.Co not in ['K', 'J', 'N']:
        return False
    account_type = account.Type or ''
    account_text = ' '.join([
        account.Name or '',
        account.Description or '',
        account.Category or '',
        account.Subcategory or '',
    ]).lower()
    if account_type in ['Bank', 'Exch', 'Credit Card']:
        return True
    if account_type == 'Current Liability':
        internal_terms = ['accounts payable', 'due to', 'payroll', 'tax', 'opening balance', 'accrued']
        return not any(term in account_text for term in internal_terms)
    return False


def company_label(code):
    labels = {'K': 'One Stop Logistics', 'J': 'Jays Auto', 'N': 'Owner Personal'}
    return f"{labels.get(code, code)} Account {code}"


def find_due_account(book_company, target_company):
    labels = {'K': 'One Stop Logistics', 'J': 'Jays Auto', 'N': 'Owner Personal'}
    base_query = Accounts.query.filter(
        (Accounts.Co == book_company) &
        (Accounts.Name.contains('Due'))
    )
    for term in [labels.get(target_company, target_company), target_company]:
        account = base_query.filter(Accounts.Name.contains(term)).first()
        if account is not None:
            return account
    return None


def ensure_due_account(book_company, target_company):
    account = find_due_account(book_company, target_company)
    if account is not None:
        return account
    labels = {'K': 'One Stop Logistics', 'J': 'Jays Auto', 'N': 'Owner Personal'}
    account = Accounts(
        Name=f'Due to {labels.get(target_company, target_company)}',
        Balance=0.00,
        AcctNumber=None,
        Routing=None,
        Payee=None,
        Type='Current Liability',
        Description='Created automatically for Plaid account transfers',
        Category='Liabilities',
        Subcategory='Current Liabilities',
        Taxrollup=None,
        Co=book_company,
        QBmap=None,
        Shared=None,
    )
    db.session.add(account)
    db.session.flush()
    return account


def find_owner_equity_account(company_code):
    query = Accounts.query.filter(
        (Accounts.Co == company_code) &
        (Accounts.Type == 'Equity')
    )
    for term in ['Owner', 'Draw', 'Distribution', 'Capital', 'Equity']:
        account = query.filter(Accounts.Name.contains(term)).first()
        if account is not None:
            return account
    return query.first()


def ensure_owner_equity_account(company_code):
    account = find_owner_equity_account(company_code)
    if account is not None:
        return account
    if company_code == 'N':
        name = 'Owner Equity'
        subcategory = 'Owner Equity'
        description = 'Created automatically for owner personal transfers'
    else:
        name = 'Owner Draw / Distributions'
        subcategory = 'Owner Draws'
        description = 'Created automatically for owner equity transfers'
    account = Accounts(
        Name=name,
        Balance=0.00,
        AcctNumber=None,
        Routing=None,
        Payee=None,
        Type='Equity',
        Description=description,
        Category='Equity',
        Subcategory=subcategory,
        Taxrollup=None,
        Co=company_code,
        QBmap=None,
        Shared=None,
    )
    db.session.add(account)
    db.session.flush()
    return account


def build_transfer_line(amount, debit, account, source_account, line_type, tcode, entry_date, ref):
    return {
        'debit': amount if debit else 0,
        'credit': 0 if debit else amount,
        'account': account.Name,
        'aid': account.id,
        'source': source_account.Name,
        'sid': source_account.id,
        'type': line_type,
        'tcode': tcode,
        'com': account.Co,
        'recorded': datetime.datetime.now(),
        'date': entry_date,
        'ref': ref,
        'match_aid': True,
    }


def transfer_journal_lines(amount, from_account, to_account, tcode, entry_date, ref, owner_transfer_treatment):
    if from_account.Co == to_account.Co:
        return [
            build_transfer_line(amount, True, to_account, from_account, 'XD', tcode, entry_date, ref),
            build_transfer_line(amount, False, from_account, to_account, 'XC', tcode, entry_date, ref),
        ], []

    owner_involved = 'N' in [from_account.Co, to_account.Co]
    if owner_involved and owner_transfer_treatment == 'equity':
        from_equity = ensure_owner_equity_account(from_account.Co)
        to_equity = ensure_owner_equity_account(to_account.Co)
        return [
            build_transfer_line(amount, True, to_account, from_account, 'XD', tcode, entry_date, ref),
            build_transfer_line(amount, False, to_equity, from_account, 'OC', tcode, entry_date, ref),
            build_transfer_line(amount, True, from_equity, to_account, 'OD', tcode, entry_date, ref),
            build_transfer_line(amount, False, from_account, to_account, 'XC', tcode, entry_date, ref),
        ], []

    due_in_from_company = ensure_due_account(from_account.Co, to_account.Co)
    due_in_to_company = ensure_due_account(to_account.Co, from_account.Co)
    return [
        build_transfer_line(amount, True, due_in_from_company, to_account, 'IA', tcode, entry_date, ref),
        build_transfer_line(amount, False, from_account, to_account, 'XC', tcode, entry_date, ref),
        build_transfer_line(amount, True, to_account, from_account, 'XD', tcode, entry_date, ref),
        build_transfer_line(amount, False, due_in_to_company, from_account, 'IL', tcode, entry_date, ref),
    ], []


def create_transfer_from_plaid_transaction(transaction_id, other_account_id, owner_transfer_treatment=None, username=None):
    ensure_plaid_tables()
    tx = PlaidTransaction.query.get(transaction_id)
    if tx is None:
        return ['Plaid transaction not found.'], None
    if tx.Status != 'new':
        return [f'Plaid transaction is already marked {tx.Status}.'], None
    if tx.Pending:
        return ['Pending Plaid transactions cannot be posted as transfers yet.'], None
    if not tx.LocalAccountId:
        return ['Map this Plaid account before posting a transfer.'], None
    if not tx.Amount:
        return ['Plaid transaction amount is missing.'], None

    plaid_account = Accounts.query.get(tx.LocalAccountId)
    other_account = Accounts.query.get(other_account_id or 0)
    if not is_transfer_endpoint_account(plaid_account):
        return ['Mapped Plaid account is not a transfer endpoint account.'], None
    if not is_transfer_endpoint_account(other_account):
        return ['Choose a valid transfer account.'], None
    if plaid_account.id == other_account.id:
        return ['Transfer accounts must be different.'], None

    if tx.Amount > 0:
        from_account = plaid_account
        to_account = other_account
        amount = tx.Amount
    else:
        from_account = other_account
        to_account = plaid_account
        amount = abs(tx.Amount)

    if from_account.Co != to_account.Co and 'N' in [from_account.Co, to_account.Co] and owner_transfer_treatment not in ['loan', 'equity']:
        return ['Choose whether this owner transfer is repayable or owner equity.'], None

    transfer_date = tx.Date or datetime.date.today()
    tcode = newjo('XF', transfer_date.strftime('%Y-%m-%d'))
    journal_id = f'TRANSFER-{tcode}'
    ref = (tx.TransactionId or '')[:50]
    memo = f'Plaid transfer: {tx.Name or from_account.Name}'
    lines, transfer_err = transfer_journal_lines(
        amount,
        from_account,
        to_account,
        tcode,
        transfer_date,
        ref,
        owner_transfer_treatment,
    )
    if transfer_err:
        return transfer_err, None

    post_err = post_balanced_journal(
        lines,
        journal_id=journal_id,
        journal_memo=memo[:200],
        posted_by='plaid_transfer',
        source_table='AccountTransfer',
    )
    if post_err:
        return post_err, None

    tx.Status = 'transfer_created'
    tx.ReviewNote = f'Created transfer {tcode}'[:250]
    tx.ReviewedAt = datetime.datetime.utcnow()
    tx.ReviewedBy = (username or '')[:30] or None
    tx.UpdatedAt = datetime.datetime.utcnow()
    db.session.commit()
    return [], tcode


def create_bill_from_plaid_transaction(transaction_id, expense_account_id, vendor_name, username=None):
    ensure_plaid_tables()
    tx = PlaidTransaction.query.get(transaction_id)
    if tx is None:
        return ['Plaid transaction not found.'], None
    if tx.Status != 'new':
        return [f'Plaid transaction is already marked {tx.Status}.'], None
    if tx.Pending:
        return ['Pending Plaid transactions cannot be imported as bill payments yet.'], None
    if not tx.LocalAccountId:
        return ['Map this Plaid account before creating a bill payment.'], None
    if not tx.Amount or tx.Amount <= 0:
        return ['Only positive Plaid withdrawal amounts can be imported as bill payments.'], None

    try:
        expense_account_id = int(expense_account_id)
    except:
        return ['Expense account is required.'], None

    bank = Accounts.query.get(tx.LocalAccountId)
    expense = Accounts.query.get(expense_account_id)
    if bank is None:
        return ['Mapped bank account could not be found.'], None
    if expense is None:
        return ['Expense account is required.'], None
    if expense.Co != bank.Co:
        return [f'Expense account company {expense.Co} does not match payment account company {bank.Co}.'], None

    vendor = get_or_create_vendor(vendor_name or tx.MerchantName or tx.Name)
    tx_date = tx.Date or datetime.date.today()
    amount = f'{tx.Amount / 100:.2f}'
    ref = (tx.TransactionId or '')[:50]
    memo = (tx.MerchantName or tx.Name or 'Plaid bill payment')[:50]
    description = (tx.Name or tx.MerchantName or 'Plaid bill payment')[:600]
    jo = newjo(f'{bank.Co}B', tx_date.strftime('%Y-%m-%d'))
    bill_datetime = datetime.datetime.combine(tx_date, datetime.time.min)

    bill = Bills(
        Jo=jo,
        Pid=vendor.id,
        Company=vendor.Company,
        Memo=memo,
        Description=description,
        bAmount=amount,
        Status='Paid',
        Scache=0,
        Source='Plaid',
        Ref=ref,
        Date=bill_datetime,
        pDate=bill_datetime,
        pAmount=amount,
        pMulti=None,
        pAccount=bank.Name,
        bAccount=expense.Name,
        bType=expense.Type,
        bCat=expense.Category,
        bSubcat=expense.Subcategory,
        Link=None,
        User=(username or 'plaid')[:25],
        Co=bank.Co,
        Temp1='PlaidTransaction',
        Temp2=tx.TransactionId,
        Recurring=0,
        dDate=bill_datetime,
        pAmount2='0.00',
        pDate2=None,
        Proof=None,
        Check=None,
        Ccache=0,
        QBi=0,
        iflag=0,
        PmtList=amount,
        PacctList=bank.Name,
        RefList=ref,
        MemoList=memo,
        PdateList=tx_date.strftime('%Y-%m-%d'),
        CheckList=None,
        MethList='Plaid',
        Pcache=0,
        pMeth='Plaid',
    )
    db.session.add(bill)
    db.session.commit()

    err = gledger_write(['newbill'], bill.Jo, bill.bAccount, bill.pAccount, 0)
    if err:
        return err, bill
    err = gledger_write(['paybill'], bill.Jo, bill.bAccount, bill.pAccount, 0)
    if err:
        return err, bill

    tx.Status = 'bill_created'
    tx.BillId = bill.id
    tx.GledgerId = bill.id
    tx.ReviewNote = f'Created bill {bill.Jo}'[:250]
    tx.ReviewedAt = datetime.datetime.utcnow()
    tx.ReviewedBy = (username or '')[:30] or None
    tx.UpdatedAt = datetime.datetime.utcnow()
    db.session.commit()
    save_vendor_rule(tx, vendor.Company, expense.id)
    return [], bill



def plaid_accounts_for_current_scac():
    ensure_plaid_tables()
    items = PlaidItem.query.filter_by(Scac=scac).all()
    item_ids = [item.id for item in items]
    if not item_ids:
        return []
    return PlaidAccount.query.filter(PlaidAccount.PlaidItemId.in_(item_ids)).all()
