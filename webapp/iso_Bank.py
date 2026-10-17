from webapp import db
from webapp.models import Income, Accounts, users, JO, Gledger, Reconciliations, Orders, Bills
from flask import session, logging, request
import datetime
import calendar
import re
import os
import shutil
import json
import subprocess
from webapp.report_maker import reportmaker
from webapp.viewfuncs import d2s
from webapp.CCC_system_setup import scac

BANK_DEPOSIT_TYPES = ['DD', 'XD']
BANK_WITHDRAWAL_TYPES = ['PC', 'XC', 'AC']

def reset_trial(ix, bankacct=None, ledger_ids=None):
    query = Gledger.query.filter(Gledger.Reconciled == 25)
    if bankacct is not None:
        query = query.filter(Gledger.Account == bankacct)
    if ledger_ids is not None:
        query = query.filter(Gledger.id.in_(ledger_ids))
    gdata = query.all()
    for gdat in gdata:
        gdat.Reconciled = ix
    db.session.commit()

def trial_ids(odata):
    selected = [row.id for row in odata if row.Reconciled == 25]
    return selected if selected else [0]

def parse_money(value):
    try:
        return float(str(value).replace('$', '').replace(',', '').strip())
    except:
        return 0.00

def mark_reconciled_payment_jobs(ledger_ids):
    updated = 0
    for ledger_id in ledger_ids:
        ledger_line = Gledger.query.get(ledger_id)
        if ledger_line is None or ledger_line.Type not in ['DD', 'XD']:
            continue
        if ledger_line.SourceTable == 'ManualDeposit':
            continue
        if not ledger_line.Tcode:
            continue
        order = Orders.query.filter(Orders.Jo == ledger_line.Tcode).first()
        if order is None:
            continue
        if order.Istat not in [5, 8, 9]:
            continue
        if parse_money(order.BalDue) > .01:
            continue
        if order.Istat != 9:
            order.Istat = 9
            updated += 1
    if updated:
        db.session.commit()
    return updated

def sync_bills_for_ledger_ids(ledger_ids):
    if not ledger_ids:
        return 0
    ledger_rows = Gledger.query.filter(Gledger.id.in_(ledger_ids)).all()
    tcodes = {row.Tcode for row in ledger_rows if row.Tcode}
    if not tcodes:
        return 0

    updated = 0
    payment_types = ['PD', 'PC', 'DD', 'QD', 'QC']
    for tcode in tcodes:
        bills = Bills.query.filter(Bills.Jo == tcode).all()
        if not bills:
            continue
        reconciled_rows = Gledger.query.filter(
            (Gledger.Tcode == tcode) &
            (Gledger.Type.in_(payment_types)) &
            (Gledger.Reconciled.isnot(None)) &
            (~Gledger.Reconciled.in_([0, 25]))
        ).all()
        values = []
        for row in reconciled_rows:
            try:
                values.append(int(row.Reconciled or 0))
            except:
                pass
        reconciled_value = max(values) if values else 0
        for bill in bills:
            current_value = getattr(bill, 'Reconciled', None) or 0
            try:
                current_value = int(current_value)
            except:
                current_value = 0
            if current_value != reconciled_value:
                bill.Reconciled = reconciled_value
                updated += 1
    if updated:
        db.session.commit()
    return updated

def latest_reconciliation(bankacct):
    return Reconciliations.query.filter(
        (Reconciliations.Account == bankacct) &
        (Reconciliations.Status == 1)
    ).order_by(Reconciliations.Rdate.desc()).first()

def finalized_reconciliations(bankacct, limit=2):
    return Reconciliations.query.filter(
        (Reconciliations.Account == bankacct) &
        (Reconciliations.Status == 1)
    ).order_by(Reconciliations.Rdate.desc()).limit(limit).all()

def trial_reconciliation(bankacct):
    return Reconciliations.query.filter(
        (Reconciliations.Account == bankacct) &
        (Reconciliations.Status == 25)
    ).order_by(Reconciliations.Rdate.desc()).first()

def reconciliation_date_bounds(value):
    if isinstance(value, datetime.datetime):
        start = datetime.datetime.combine(value.date(), datetime.time.min)
    elif isinstance(value, datetime.date):
        start = datetime.datetime.combine(value, datetime.time.min)
    else:
        start = datetime.datetime.strptime(value, "%Y-%m-%d")
    return start, start + datetime.timedelta(days=1)

def reconciliation_for_date(bankacct, rdate, statuses=None):
    start, end = reconciliation_date_bounds(rdate)
    query = Reconciliations.query.filter(
        (Reconciliations.Account == bankacct) &
        (Reconciliations.Rdate >= start) &
        (Reconciliations.Rdate < end)
    )
    if statuses is not None:
        query = query.filter(Reconciliations.Status.in_(statuses))
    return query.order_by(Reconciliations.id.desc()).first()

def default_beginning_balance(bankacct):
    rdat = latest_reconciliation(bankacct)
    if rdat is not None and rdat.Ebal not in [None, '']:
        return rdat.Ebal
    return '0.00'

def add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)

def default_statement_date(bankacct, today_str):
    finalized = finalized_reconciliations(bankacct, 2)
    if not finalized or finalized[0].Rdate is None:
        return today_str

    latest_date = finalized[0].Rdate.date() if isinstance(finalized[0].Rdate, datetime.datetime) else finalized[0].Rdate
    if len(finalized) == 1 or finalized[1].Rdate is None:
        return add_months(latest_date, 1).strftime('%Y-%m-%d')

    previous_date = finalized[1].Rdate.date() if isinstance(finalized[1].Rdate, datetime.datetime) else finalized[1].Rdate
    if latest_date.day == previous_date.day:
        return add_months(latest_date, 1).strftime('%Y-%m-%d')

    interval = latest_date - previous_date
    if interval.days > 0:
        return (latest_date + interval).strftime('%Y-%m-%d')
    return add_months(latest_date, 1).strftime('%Y-%m-%d')

def is_credit_reconciliation_account(bankacct):
    adat = Accounts.query.filter(Accounts.Name == bankacct).first()
    if adat is None:
        return False
    values = [
        adat.Name,
        adat.Type,
        adat.Description,
        adat.Category,
        adat.Subcategory,
    ]
    text = ' '.join(str(value or '').lower() for value in values)
    return any(token in text for token in ['credit card', 'liability', 'loan'])

def statement_defaults(bankacct, today_str):
    defaults = {
        'rdate': default_statement_date(bankacct, today_str),
        'begbal': default_beginning_balance(bankacct),
        'endbal': '0.00',
    }
    rdat = trial_reconciliation(bankacct)
    if rdat is not None:
        if rdat.Rdate is not None:
            defaults['rdate'] = rdat.Rdate.strftime('%Y-%m-%d')
        if rdat.Bbal not in [None, '']:
            defaults['begbal'] = rdat.Bbal
        if rdat.Ebal not in [None, '']:
            defaults['endbal'] = rdat.Ebal
    return defaults

def recon_list_text(values):
    try:
        return json.dumps(values)
    except:
        return None

def save_trial_reconciliation(bankacct, rdate, bbal, ebal, deposits, withdraws, servicefees, dlist, wlist, diff, reconciliation_id=None, statement_values=None):
    try:
        dlists = recon_list_text(dlist)
    except:
        dlists = None
    try:
        wlists = recon_list_text(wlist)
    except:
        wlists = None

    rdat = None
    if reconciliation_id not in [None, '']:
        try:
            rdat = Reconciliations.query.get(int(reconciliation_id))
        except:
            rdat = None
        if rdat is not None and rdat.Account != bankacct:
            rdat = None
        if rdat is not None:
            target = reconciliation_for_date(bankacct, rdate, [0, 25, 1])
            if target is not None and target.id != rdat.id:
                raise ValueError(
                    f'Another reconciliation already exists for {bankacct} dated {rdate.strftime("%Y-%m-%d")}.'
                )
    if rdat is None:
        rdat = reconciliation_for_date(bankacct, rdate, [0, 25, 1])
    if rdat is None:
        rdat = trial_reconciliation(bankacct)
    if rdat is None:
        rdat = Reconciliations(
            Account=bankacct,
            Rdate=rdate,
            Bbal=bbal,
            Ebal=ebal,
            Deposits=deposits,
            Withdraws=withdraws,
            Servicefees=servicefees,
            DepositList=dlists,
            WithdrawList=wlists,
            Status=25,
            Diff=diff,
        )
        db.session.add(rdat)
    else:
        rdat.Account = bankacct
        rdat.Rdate = rdate
        rdat.Bbal = bbal
        rdat.Ebal = ebal
        rdat.Deposits = deposits
        rdat.Withdraws = withdraws
        rdat.Servicefees = servicefees
        rdat.DepositList = dlists
        rdat.WithdrawList = wlists
        rdat.Status = 25
        rdat.Diff = diff
    period_start, period_end = parse_statement_period_override(statement_values)
    if period_start is not None:
        rdat.PeriodStart = period_start.date()
    if period_end is not None:
        rdat.PeriodEnd = period_end.date()
    db.session.commit()
    return rdat

def baseline_reconciliation(bankacct, cutoff_date, trusted_balance):
    cutoff_end = cutoff_date + datetime.timedelta(days=1)
    rows = Gledger.query.filter(
        (Gledger.Account == bankacct) &
        (Gledger.Date < cutoff_end) &
        ((Gledger.Reconciled == 0) | (Gledger.Reconciled == 25))
    ).all()

    deposits = 0
    withdrawals = 0
    for row in rows:
        if row.Type in BANK_DEPOSIT_TYPES:
            deposits += row.Debit or 0
        if row.Type in BANK_WITHDRAWAL_TYPES:
            withdrawals += row.Credit or 0
        row.Reconciled = cutoff_date.month

    trusted_balance = d2s(trusted_balance)
    existing = reconciliation_for_date(bankacct, cutoff_date)
    if existing is None:
        existing = Reconciliations(
            Account=bankacct,
            Rdate=cutoff_date,
            Bbal='0.00',
            Ebal=trusted_balance,
            Deposits=d2s(float(deposits) / 100),
            Withdraws=d2s(float(withdrawals) / 100),
            Servicefees='0.00',
            DepositList='baseline',
            WithdrawList='baseline',
            Status=1,
            Diff='0.00',
        )
        db.session.add(existing)
    else:
        existing.Bbal = '0.00'
        existing.Ebal = trusted_balance
        existing.Deposits = d2s(float(deposits) / 100)
        existing.Withdraws = d2s(float(withdrawals) / 100)
        existing.Servicefees = '0.00'
        existing.DepositList = 'baseline'
        existing.WithdrawList = 'baseline'
        existing.Status = 1
        existing.Diff = '0.00'

    db.session.commit()
    return len(rows), d2s(float(deposits) / 100), d2s(float(withdrawals) / 100), trusted_balance

def reconciliation_list_ids(value):
    try:
        parsed = json.loads(value or '')
    except:
        return []
    if not isinstance(parsed, list):
        return []
    ids = []
    for item in parsed:
        try:
            ids.append(int(item))
        except:
            pass
    return ids

def previous_reconciliation_before(bankacct, rdate):
    start, _ = reconciliation_date_bounds(rdate)
    return Reconciliations.query.filter(
        (Reconciliations.Account == bankacct) &
        (Reconciliations.Rdate < start)
    ).order_by(Reconciliations.Rdate.desc(), Reconciliations.id.desc()).first()

def parse_statement_period_override(statement_values=None):
    values = statement_values or request.values
    start_value = values.get('statement_period_start') if values is not None else None
    end_value = values.get('statement_period_end') if values is not None else None
    if start_value in [None, ''] and end_value in [None, '']:
        return None, None
    try:
        start = datetime.datetime.combine(
            datetime.datetime.strptime(start_value, "%Y-%m-%d").date(),
            datetime.time.min,
        ) if start_value not in [None, ''] else None
    except:
        start = None
    try:
        end = datetime.datetime.combine(
            datetime.datetime.strptime(end_value, "%Y-%m-%d").date(),
            datetime.time.max,
        ) if end_value not in [None, ''] else None
    except:
        end = None
    return start, end

def statement_period_bounds(bankacct, statement_date, statement_values=None):
    override_start, override_end = parse_statement_period_override(statement_values)
    if override_start is not None or override_end is not None:
        return override_start, override_end
    if statement_date in [None, '']:
        return None, None
    if isinstance(statement_date, datetime.datetime):
        statement_day = statement_date.date()
    elif isinstance(statement_date, datetime.date):
        statement_day = statement_date
    else:
        try:
            statement_day = datetime.datetime.strptime(str(statement_date), "%Y-%m-%d").date()
        except:
            return None, None
    saved = reconciliation_for_date(bankacct, statement_day)
    if saved is not None and (saved.PeriodStart is not None or saved.PeriodEnd is not None):
        start = datetime.datetime.combine(saved.PeriodStart, datetime.time.min) if saved.PeriodStart else None
        end = datetime.datetime.combine(saved.PeriodEnd or statement_day, datetime.time.max)
        return start, end
    if statement_day.day == 1:
        start = datetime.datetime.combine(statement_day, datetime.time.min)
        month_end = datetime.date(
            statement_day.year,
            statement_day.month,
            calendar.monthrange(statement_day.year, statement_day.month)[1],
        )
        return start, datetime.datetime.combine(month_end, datetime.time.max)
    previous = previous_reconciliation_before(bankacct, statement_day)
    if previous is not None and previous.Rdate is not None:
        previous_end = statement_cutoff_datetime(previous.Rdate)
        start = previous_end + datetime.timedelta(microseconds=1) if previous_end else None
    else:
        start = None
    return start, statement_cutoff_datetime(statement_day)

def ledger_date_in_statement_period(ledger_date, bankacct, rdate, statement_values=None):
    start, end = statement_period_bounds(bankacct, rdate, statement_values)
    if end is None or ledger_date in [None, '']:
        return False
    if isinstance(ledger_date, datetime.datetime):
        compare_date = ledger_date
    elif isinstance(ledger_date, datetime.date):
        compare_date = datetime.datetime.combine(ledger_date, datetime.time.min)
    else:
        try:
            compare_date = datetime.datetime.strptime(str(ledger_date)[:10], "%Y-%m-%d")
        except:
            return False
    if compare_date > end:
        return False
    if start is not None and compare_date < start:
        return False
    return True

def ledger_datetime(value):
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min)
    if value in [None, '']:
        return None
    try:
        return datetime.datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except:
        return None

def finalized_statement_periods(bankacct):
    periods = []
    rows = Reconciliations.query.filter(
        (Reconciliations.Account == bankacct) &
        (Reconciliations.Status == 1)
    ).order_by(Reconciliations.Rdate, Reconciliations.id).all()
    for row in rows:
        start, end = statement_period_bounds(bankacct, row.Rdate)
        if end is not None:
            periods.append((start, end))
    return periods

def ledger_row_in_finalized_period(row, periods):
    row_date = ledger_datetime(row.Date)
    if row_date is None:
        return False
    for start, end in periods:
        if row_date <= end and (start is None or row_date >= start):
            return True
    return False

def ledger_row_effectively_unreconciled(row, periods):
    if row.Reconciled == 25:
        return True
    if row.Reconciled in [None, 0]:
        return not ledger_row_in_finalized_period(row, periods)
    return False

def filter_statement_rows(rows, rdat):
    if rdat is None:
        return []
    return [
        row for row in rows
        if ledger_date_in_statement_period(row.Date, rdat.Account, rdat.Rdate)
    ]

def statement_side_rows(rdat, tx_types, list_value):
    ids, complete = reconciliation_explicit_ids(list_value)
    if complete and ids:
        return Gledger.query.filter(
            (Gledger.Account == rdat.Account) &
            (Gledger.id.in_(ids))
        ).all()

    if ids:
        compact_rows = compact_statement_side_rows(rdat, tx_types, list_value)
        if compact_rows is not None:
            return compact_rows

    period_start, period_end = statement_period_bounds(rdat.Account, rdat.Rdate)
    query = Gledger.query.filter(
        (Gledger.Account == rdat.Account) &
        (Gledger.Type.in_(tx_types))
    )
    if period_start is not None:
        query = query.filter(Gledger.Date >= period_start)
    if period_end is not None:
        query = query.filter(Gledger.Date <= period_end)
    return query.all()

def statement_rows_from_saved_reconciliation(rdat):
    if rdat is None:
        return []
    rows_by_id = {}
    for row in statement_side_rows(rdat, BANK_DEPOSIT_TYPES, rdat.DepositList):
        rows_by_id[row.id] = row
    for row in statement_side_rows(rdat, BANK_WITHDRAWAL_TYPES, rdat.WithdrawList):
        rows_by_id[row.id] = row
    return list(rows_by_id.values())

def rows_for_reconciliation(rdat):
    row_ids = reconciliation_list_ids(rdat.DepositList) + reconciliation_list_ids(rdat.WithdrawList)
    if row_ids:
        return statement_rows_from_saved_reconciliation(rdat)

    previous = previous_reconciliation_before(rdat.Account, rdat.Rdate)

    query = Gledger.query.filter(
        (Gledger.Account == rdat.Account) &
        (Gledger.Reconciled == rdat.Rdate.month) &
        (Gledger.Date <= rdat.Rdate)
    )
    if previous is not None and previous.Rdate is not None:
        query = query.filter(Gledger.Date > previous.Rdate)
    return query.all()

def reopen_reconciliation(bankacct, rdate):
    rdat = reconciliation_for_date(bankacct, rdate, [1])
    if rdat is None:
        rdat = reconciliation_for_date(bankacct, rdate, [0, 25])
    if rdat is None:
        return 0, f'No finalized or reopened reconciliation was found for {bankacct} dated {rdate.strftime("%Y-%m-%d")}.'

    rows = rows_for_reconciliation(rdat)
    row_ids = [row.id for row in rows]
    for row in rows:
        row.Reconciled = 25
    rdat.Status = 0
    db.session.commit()
    synced_bills = sync_bills_for_ledger_ids(row_ids)
    if synced_bills:
        return len(rows), f'Reopened reconciliation for {bankacct} dated {rdat.Rdate.strftime("%Y-%m-%d")}. {len(rows)} ledger row(s) were reselected and {synced_bills} bill row(s) are now editable until finalized again.'
    return len(rows), f'Reopened reconciliation for {bankacct} dated {rdat.Rdate.strftime("%Y-%m-%d")}. {len(rows)} ledger row(s) were reselected.'

def selected_bank_ids(odata):
    selected = []
    valid_ids = {row.id for row in odata}
    for row in odata:
        testone = request.values.get('oder' + str(row.id))
        if testone:
            selected.append(int(testone))
    for key, value in request.values.items():
        if key.startswith('bankgroup') and value:
            for item in value.split(','):
                try:
                    row_id = int(item)
                    if row_id in valid_ids and row_id not in selected:
                        selected.append(row_id)
                except:
                    pass
    return selected

def statement_cutoff_datetime(statement_date):
    if statement_date in [None, '']:
        return None
    if isinstance(statement_date, datetime.datetime):
        return statement_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    if isinstance(statement_date, datetime.date):
        return datetime.datetime.combine(statement_date, datetime.time.max)
    try:
        parsed_date = datetime.datetime.strptime(str(statement_date), "%Y-%m-%d").date()
        return datetime.datetime.combine(parsed_date, datetime.time.max)
    except:
        return None

def ledger_date_after_cutoff(ledger_date, cutoff):
    if cutoff is None or ledger_date in [None, '']:
        return False
    if isinstance(ledger_date, datetime.datetime):
        compare_date = ledger_date
    elif isinstance(ledger_date, datetime.date):
        compare_date = datetime.datetime.combine(ledger_date, datetime.time.min)
    else:
        try:
            compare_date = datetime.datetime.strptime(str(ledger_date)[:10], "%Y-%m-%d")
        except:
            return False
    return compare_date > cutoff

def reconciliation_explicit_ids(value):
    try:
        parsed = json.loads(value or '')
    except:
        return set(), False
    if isinstance(parsed, list):
        ids = set()
        for item in parsed:
            try:
                ids.add(int(item))
            except:
                pass
        return ids, True
    if isinstance(parsed, dict):
        ids = set()
        for group in ['first', 'last']:
            for item in parsed.get(group, []) or []:
                try:
                    ids.add(int(item))
                except:
                    pass
        return ids, False
    return set(), False

def reconciliation_list_meta(value):
    try:
        parsed = json.loads(value or '')
    except:
        return None
    if isinstance(parsed, list):
        ids = []
        for item in parsed:
            try:
                ids.append(int(item))
            except:
                pass
        return {'complete': True, 'count': len(ids), 'ids': set(ids)}
    if isinstance(parsed, dict):
        ids = set()
        for group in ['first', 'last']:
            for item in parsed.get(group, []) or []:
                try:
                    ids.add(int(item))
                except:
                    pass
        try:
            count = int(parsed.get('count'))
        except:
            count = None
        return {'complete': False, 'count': count, 'ids': ids}
    return None

def side_amount(row, tx_types):
    if tx_types == BANK_DEPOSIT_TYPES:
        return row.Debit or 0
    return row.Credit or 0

def find_amount_count_subset(rows, needed_count, needed_amount, tx_types):
    if needed_count == 0:
        return [] if needed_amount == 0 else None
    if needed_count < 0 or needed_amount < 0:
        return None
    candidates = [
        row for row in rows
        if side_amount(row, tx_types) <= needed_amount
    ]
    candidates = sorted(
        candidates,
        key=lambda row: (
            ledger_datetime(row.Recorded) or datetime.datetime.min,
            ledger_datetime(row.Date) or datetime.datetime.min,
            row.id,
        ),
        reverse=True,
    )
    suffix_amounts = [0] * (len(candidates) + 1)
    for index in range(len(candidates) - 1, -1, -1):
        suffix_amounts[index] = suffix_amounts[index + 1] + side_amount(candidates[index], tx_types)

    def search(start_index, count_left, amount_left):
        if count_left == 0:
            return [] if amount_left == 0 else None
        if amount_left < 0 or len(candidates) - start_index < count_left:
            return None
        if suffix_amounts[start_index] < amount_left:
            return None
        for index in range(start_index, len(candidates)):
            row = candidates[index]
            amount = side_amount(row, tx_types)
            if amount > amount_left:
                continue
            tail = search(index + 1, count_left - 1, amount_left - amount)
            if tail is not None:
                return [row] + tail
        return None

    return search(0, needed_count, needed_amount)

def compact_statement_side_rows(rdat, tx_types, list_value):
    meta = reconciliation_list_meta(list_value)
    if meta is None or meta.get('count') is None:
        return None
    period_start, period_end = statement_period_bounds(rdat.Account, rdat.Rdate)
    query = Gledger.query.filter(
        (Gledger.Account == rdat.Account) &
        (Gledger.Type.in_(tx_types))
    )
    if period_start is not None:
        query = query.filter(Gledger.Date >= period_start)
    if period_end is not None:
        query = query.filter(Gledger.Date <= period_end)
    period_rows = query.order_by(Gledger.Date, Gledger.id).all()
    pinned_ids = meta.get('ids') or set()
    if pinned_ids:
        existing_ids = {row.id for row in period_rows}
        missing_pinned_ids = pinned_ids - existing_ids
        if missing_pinned_ids:
            pinned_rows = Gledger.query.filter(
                (Gledger.Account == rdat.Account) &
                (Gledger.Type.in_(tx_types)) &
                (Gledger.id.in_(list(missing_pinned_ids)))
            ).all()
            period_rows.extend(pinned_rows)
    target_count = meta['count']
    target_amount = int(round(parse_money(rdat.Deposits if tx_types == BANK_DEPOSIT_TYPES else rdat.Withdraws) * 100))
    current_amount = sum(side_amount(row, tx_types) for row in period_rows)
    current_count = len(period_rows)
    if current_count == target_count and current_amount == target_amount:
        return period_rows

    if current_count > target_count and current_amount > target_amount:
        remove_count = current_count - target_count
        remove_amount = current_amount - target_amount
        removable = [row for row in period_rows if row.id not in pinned_ids]
        remove_rows = find_amount_count_subset(removable, remove_count, remove_amount, tx_types)
        if remove_rows is not None:
            remove_ids = {row.id for row in remove_rows}
            return [row for row in period_rows if row.id not in remove_ids]

    if current_count < target_count and current_amount < target_amount:
        add_count = target_count - current_count
        add_amount = target_amount - current_amount
        window_start = (period_start or statement_cutoff_datetime(rdat.Rdate)) - datetime.timedelta(days=45)
        window_end = (period_end or statement_cutoff_datetime(rdat.Rdate)) + datetime.timedelta(days=45)
        period_ids = {row.id for row in period_rows}
        outside_rows = Gledger.query.filter(
            (Gledger.Account == rdat.Account) &
            (Gledger.Type.in_(tx_types)) &
            (Gledger.Date >= window_start) &
            (Gledger.Date <= window_end) &
            (~Gledger.id.in_(list(period_ids)))
        ).order_by(Gledger.Date, Gledger.id).all()
        add_rows = find_amount_count_subset(outside_rows, add_count, add_amount, tx_types)
        if add_rows is not None:
            return period_rows + add_rows

    return None

def reconciliation_row_ids(rdat):
    if rdat is None:
        return set(), False
    deposit_ids, deposit_complete = reconciliation_explicit_ids(rdat.DepositList)
    withdraw_ids, withdraw_complete = reconciliation_explicit_ids(rdat.WithdrawList)
    return deposit_ids | withdraw_ids, deposit_complete and withdraw_complete

def reconciliation_has_compacted_lists(rdat):
    if rdat is None:
        return False
    deposit_ids, deposit_complete = reconciliation_explicit_ids(rdat.DepositList)
    withdraw_ids, withdraw_complete = reconciliation_explicit_ids(rdat.WithdrawList)
    return bool((deposit_ids and not deposit_complete) or (withdraw_ids and not withdraw_complete))

def statement_saved_totals(rdat):
    if rdat is None:
        return None
    return {
        'deposits': d2s(parse_money(rdat.Deposits)),
        'withdrawals': d2s(parse_money(rdat.Withdraws)),
        'servicefees': d2s(parse_money(rdat.Servicefees)),
    }

def statement_row_totals(rows):
    deposits = 0
    withdrawals = 0
    for row in rows:
        if row.Type in BANK_DEPOSIT_TYPES:
            deposits += row.Debit or 0
        if row.Type in BANK_WITHDRAWAL_TYPES:
            withdrawals += row.Credit or 0
    return d2s(float(deposits) / 100), d2s(float(withdrawals) / 100)

def selected_statement_saved_totals(bankacct, statement_date):
    rdat = selected_statement_reconciliation(bankacct, statement_date)
    if rdat is None:
        return None
    if rdat.Status == 1 and reconciliation_has_compacted_lists(rdat):
        return statement_saved_totals(rdat)
    return None

def legacy_reconciliation_notice(bankacct, statement_date):
    rdat = selected_statement_reconciliation(bankacct, statement_date)
    if rdat is None or not reconciliation_has_compacted_lists(rdat):
        return None
    rows = statement_rows_from_saved_reconciliation(rdat)
    row_deposits, row_withdrawals = statement_row_totals(rows)
    saved = statement_saved_totals(rdat)
    if saved is None:
        return None
    if row_deposits == saved['deposits'] and row_withdrawals == saved['withdrawals']:
        return None
    return {
        'active': True,
        'status': rdat.Status,
        'deposits': saved['deposits'],
        'withdrawals': saved['withdrawals'],
        'row_deposits': row_deposits,
        'row_withdrawals': row_withdrawals,
        'message': (
            'This finalized statement was saved with legacy compact row lists. '
            'The saved statement totals are shown, but the exact row-level selection '
            'cannot be reconstructed from the compact data.'
        ),
    }

def repair_statement_reconciliation_flags(bankacct, rdate):
    rdat = reconciliation_for_date(bankacct, rdate, [1])
    if rdat is None:
        return 0, f'No finalized reconciliation was found for {bankacct} dated {rdate.strftime("%Y-%m-%d")}.'
    rows = statement_rows_from_saved_reconciliation(rdat)
    row_deposits, row_withdrawals = statement_row_totals(rows)
    saved = statement_saved_totals(rdat)
    if saved is None:
        return 0, 'This statement does not have saved reconciliation totals.'
    if row_deposits != saved['deposits'] or row_withdrawals != saved['withdrawals']:
        return 0, (
            'Statement flags were not repaired because the row reconstruction does not match the finalized totals. '
            f'Saved deposits/withdrawals ${saved["deposits"]}/${saved["withdrawals"]}; '
            f'row deposits/withdrawals ${row_deposits}/${row_withdrawals}.'
        )

    statement_date = rdat.Rdate.date() if isinstance(rdat.Rdate, datetime.datetime) else rdat.Rdate
    recon_value = statement_date.month
    changed = 0
    row_ids = []
    for row in rows:
        row_ids.append(row.id)
        if row.Reconciled != recon_value:
            row.Reconciled = recon_value
            changed += 1
    db.session.commit()
    synced_bills = sync_bills_for_ledger_ids(row_ids)
    extra = f' Synced {synced_bills} bill row(s).' if synced_bills else ''
    return changed, f'Repaired {changed} ledger row(s) for {bankacct} statement {statement_date.strftime("%Y-%m-%d")} to Recon {recon_value}.{extra}'

def selected_statement_reconciliation(bankacct, statement_date):
    if statement_date in [None, '']:
        return None
    return reconciliation_for_date(bankacct, statement_date, [0, 25, 1])

def selected_statement_ids(bankacct, statement_date):
    rdat = selected_statement_reconciliation(bankacct, statement_date)
    return [row.id for row in statement_rows_from_saved_reconciliation(rdat)]

def reconciliation_contains_ledger_line(rdat, line):
    explicit_ids, explicit_complete = reconciliation_row_ids(rdat)
    if explicit_ids:
        if line.id in explicit_ids:
            return True
        if explicit_complete:
            return False
    if explicit_complete:
        return False

    if rdat.Rdate is None or line.Date is None:
        return False
    line_date = line.Date.date() if isinstance(line.Date, datetime.datetime) else line.Date
    reconciliation_date = rdat.Rdate.date() if isinstance(rdat.Rdate, datetime.datetime) else rdat.Rdate
    try:
        reconciled_month = int(line.Reconciled or 0)
    except:
        return False
    if reconciled_month != reconciliation_date.month:
        return False
    return line_date <= reconciliation_date

def line_has_final_reconciliation(line):
    if line is None or line.Reconciled in [None, 0, 25]:
        return False
    reconciliations = Reconciliations.query.filter(
        (Reconciliations.Account == line.Account) &
        (Reconciliations.Status == 1)
    ).all()
    return any(reconciliation_contains_ledger_line(rdat, line) for rdat in reconciliations)

def clear_stale_reconciliation_flags(bankacct):
    # This is intentionally not run on normal page load. Older reconciliation
    # rows may have compacted DepositList/WithdrawList values, so a display page
    # cannot always prove a ledger row is stale without risking data changes.
    rows = Gledger.query.filter(
        (Gledger.Account == bankacct) &
        (Gledger.Reconciled.isnot(None)) &
        (~Gledger.Reconciled.in_([0, 25]))
    ).all()
    cleared = 0
    for row in rows:
        if not line_has_final_reconciliation(row):
            row.Reconciled = 0
            cleared += 1
    if cleared:
        db.session.commit()
    return cleared

def dataget_Bank(thismuch, bankacct, statement_date=None, statement_values=None):
    # 0=order,#1=proofs,#2=interchange,#3=people/services
    today = datetime.date.today()
    stopdate = today-datetime.timedelta(days=60)
    if thismuch == '1':
        query = Gledger.query.filter(
            (Gledger.Account == bankacct) &
            ((Gledger.Reconciled.is_(None)) | (Gledger.Reconciled == 0) | (Gledger.Reconciled == 25))
        )
        _, cutoff = statement_period_bounds(bankacct, statement_date, statement_values)
        if cutoff is not None:
            # Reconciliation works against a statement date. Rows after that date
            # must not be available for selection or stale form submission.
            query = query.filter(Gledger.Date <= cutoff)
        odata = query.all()
    elif thismuch == '5':
        rdat = selected_statement_reconciliation(bankacct, statement_date)
        row_ids, explicit_complete = reconciliation_row_ids(rdat)
        if rdat is not None and (rdat.DepositList or rdat.WithdrawList):
            odata = statement_rows_from_saved_reconciliation(rdat)
        else:
            query = Gledger.query.filter((Gledger.Account == bankacct) & (Gledger.Reconciled == 25))
            _, cutoff = statement_period_bounds(bankacct, statement_date, statement_values)
            if cutoff is not None:
                query = query.filter(Gledger.Date <= cutoff)
            odata = query.all()
    elif thismuch == '2':
        stopdate = today-datetime.timedelta(days=45)
        odata = Gledger.query.filter((Gledger.Account==bankacct) & (Gledger.Recorded > stopdate)).all()
    elif thismuch == '3':
        stopdate = today-datetime.timedelta(days=90)
        odata = Gledger.query.filter((Gledger.Account==bankacct) & (Gledger.Recorded > stopdate)).all()
    else:
        odata = Gledger.query.filter(Gledger.Account==bankacct ).all()
    return odata

def recon_totals(bankacct, statement_date=None, use_saved_statement=True, statement_values=None):
    # Find service charges for month:
    dlist = []
    wlist = []
    rdat = selected_statement_reconciliation(bankacct, statement_date) if use_saved_statement else None
    row_ids, explicit_complete = reconciliation_row_ids(rdat)
    saved_totals = selected_statement_saved_totals(bankacct, statement_date) if use_saved_statement else None
    if saved_totals is not None:
        return saved_totals['deposits'], saved_totals['withdrawals'], saved_totals['servicefees'], dlist, wlist
    if rdat is not None and (rdat.DepositList or rdat.WithdrawList):
        gdata = statement_rows_from_saved_reconciliation(rdat)
    else:
        gquery = Gledger.query.filter((Gledger.Account == bankacct) & (Gledger.Reconciled == 25))
        _, cutoff = statement_period_bounds(bankacct, statement_date, statement_values)
        if cutoff is not None:
            gquery = gquery.filter(Gledger.Date <= cutoff)
        gdata = gquery.all()

    gdat = next((row for row in gdata if row.Source == bankacct), None)
    if gdat is not None:
        bkc = gdat.Credit
    else:
        bkc = 0
    totald, totalc = 0.0, 0.0
    for gdat in gdata:
        type = gdat.Type
        if type in BANK_DEPOSIT_TYPES:
            totald = totald + gdat.Debit
            dlist.append(gdat.id)
        if type in BANK_WITHDRAWAL_TYPES:
            totalc = totalc + gdat.Credit
            wlist.append(gdat.id)

    totalc = totalc - bkc
    return d2s(float(totald)/100), d2s(float(totalc)/100), d2s(float(bkc)/100), dlist, wlist

def banktotals(bankacct, statement_values=None, use_saved_statement=True):
    totald=0
    totalc=0
    totald_U = 0
    totalc_U = 0
    defaults = statement_defaults(bankacct, datetime.date.today().strftime('%Y-%m-%d'))
    statement_values = statement_values or request.values
    statement_date = statement_values.get('rdate')
    endbal = statement_values.get('endbal')
    begbal = statement_values.get('begbal')
    if endbal in [None, '']:
        endbal = defaults['endbal']
    if begbal in [None, '']:
        begbal = defaults['begbal']
    print(begbal,endbal)
    try:
        endbal = parse_money(endbal)
    except:
        endbal=0.00
    try:
        begbal = parse_money(begbal)
    except:
        begbal=0.00
    periods = finalized_statement_periods(bankacct)
    gdata = Gledger.query.filter(Gledger.Account==bankacct).all()
    for gdat in gdata:
        type = gdat.Type
        if type in BANK_DEPOSIT_TYPES:
            totald = totald + gdat.Debit
            if ledger_row_effectively_unreconciled(gdat, periods):
                totald_U = totald_U + gdat.Debit

        if type in BANK_WITHDRAWAL_TYPES:
            totalc = totalc + gdat.Credit
            if ledger_row_effectively_unreconciled(gdat, periods):
                totalc_U = totalc_U + gdat.Credit

    trial_dr, trial_cr, bk_charge, dlist, wlist = recon_totals(bankacct, statement_date, use_saved_statement, statement_values)

    totald = float(totald)/100
    totalc = float(totalc)/100
    if is_credit_reconciliation_account(bankacct):
        # Credit card statement balances are entered as positive amounts owed.
        # Ledger net activity is debit-minus-credit, so charges reduce the net.
        diff = begbal - float(trial_dr) + float(trial_cr) + float(bk_charge) - endbal
    else:
        diff = begbal + float(trial_dr) - float(trial_cr) - float(bk_charge) - endbal
    totalds = d2s(totald)
    totalcs = d2s(totalc)
    balance = d2s( (float(totald) - float(totalc))/100 )
    totald_Us = d2s(float(totald_U)/100)
    totalc_Us = d2s(float(totalc_U)/100)
    projbal = d2s( float(totald-totalc-totald_U+totalc_U)/100 )

    acctinfo=[balance,totald_Us,totalc_Us,projbal,d2s(endbal),d2s(diff),bankacct,totalds,totalcs,d2s(begbal)]

    return acctinfo





def isoBank():
    statement_values = {
        'begbal': '',
        'endbal': '',
        'rdate': '',
        'statement_period_start': '',
        'statement_period_end': '',
    }

    if request.method == 'POST':
# ____________________________________________________________________________________________________________________B.FormVariables.General

        from webapp.viewfuncs import parseline, popjo, jovec, newjo, timedata, nonone, nononef, enter_bk_charges
        from webapp.viewfuncs import numcheck, numcheckv, viewbuttons, get_ints, numcheckvec, numcheckv, d2s, erud

        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        hv = [0]*9

        #Zero and blank items for default
        username = session['username'].capitalize()
        cache=request.values.get('cache')
        cache=nonone(cache)

        modata=0
        modlink=0
        docref=''
        oderstring=''
        acname = request.values.get('acname')



        today = datetime.date.today()
        now = datetime.datetime.now().strftime('%I:%M %p')
        err = []

        leftsize=10

        match    =  request.values.get('Match')
        modify   =  request.values.get('Qmod')
        vmod   =  request.values.get('Vmod')
        viewo     =  request.values.get('View')
        returnhit = request.values.get('Return')
        deletehit = request.values.get('Delete')
        delfile = request.values.get('DELF')
        # hidden values
        update   =  request.values.get('Update')
        newact=request.values.get('NewA')
        thisjob=request.values.get('ThisJob')
        oder=request.values.get('oder')
        modlink = request.values.get('modlink')
        depositmake = request.values.get('depositmake')
        recdeposit = request.values.get('recdeposit')
        unrecord = request.values.get('unrecord')
        thismuch = request.values.get('thismuch')
        recothese = request.values.get('recothese')
        finalize = request.values.get('finalize')
        undothese = request.values.get('undothese')
        baselinehit = request.values.get('baseline_reconcile')
        reopenhit = request.values.get('reopen_reconciliation')
        repairhit = request.values.get('repair_reconciliation_flags')
        selected_reconciliation_id = request.values.get('selected_reconciliation_id')
        baseline_date = request.values.get('baseline_date')
        baseline_balance = request.values.get('baseline_balance')
        previous_acname = request.values.get('previous_acname')
        account_changed = previous_acname not in [None, ''] and previous_acname != acname
        defaults = statement_defaults(acname, today_str)
        rdate = request.values.get('rdate')
        if rdate is None or account_changed:
            rdate = defaults['rdate']
        hv[0] = rdate
        hv[1] = [0]
        endbal = request.values.get('endbal')
        begbal = request.values.get('begbal')
        if endbal in [None, ''] or account_changed:
            endbal = defaults['endbal']
        if begbal in [None, ''] or account_changed:
            begbal = defaults['begbal']
        statement_period_start = request.values.get('statement_period_start')
        statement_period_end = request.values.get('statement_period_end')
        if account_changed:
            statement_period_start = None
            statement_period_end = None
        statement_values = {
            'begbal': begbal,
            'endbal': endbal,
            'rdate': rdate,
            'statement_period_start': statement_period_start,
            'statement_period_end': statement_period_end,
        }
        recready = 1
        try:
            endbal=parse_money(endbal)
        except:
            endbal=0.00
            err.append('No Statement Balance Entered for Reconciliation')
            recready=0
        try:
            begbal=parse_money(begbal)
        except:
            endbal=0.00
            err.append('No Statement Ending Entered for Reconciliation')
            recready=0


        oder=nonone(oder)
        modlink=nonone(modlink)

        leftscreen=1
        err=['All is well', ' ', ' ', ' ', ' ']

        if returnhit is not None:
            modlink=0
            depojo=0


# ____________________________________________________________________________________________________________________E.FormVariables.General
# ____________________________________________________________________________________________________________________B.DataUpdates.General

        if modlink==1:
            if oder > 0:
                modata=Income.query.get(oder)
                vals=['jo','subjo','pid','description','amount','ref','pdate','original']
                a=list(range(len(vals)))
                for i,v in enumerate(vals):
                    a[i]=request.values.get(v)

                modata.Jo=a[0]
                modata.Account=a[1]
                modata.Pid=a[2]
                modata.Description=a[3]
                modata.Amount=a[4]
                modata.Ref=a[5]
                modata.Date=a[6]
                modata.Original=a[7]
                db.session.commit()
                err[3]= 'Modification to Income id ' + str(modata.id) + ' completed.'
                if update is not None:
                    modlink=0
                    leftsize=10
                else:
                    leftsize=6
                    leftscreen=0
                    modata=Income.query.get(oder)

# ____________________________________________________________________________________________________________________B.GetData.General
        #odata = Income.query.all()
        print('acname=',acname)
        odata = dataget_Bank(thismuch, acname, hv[0], statement_values)
        hv[1] = selected_statement_ids(acname, hv[0]) or trial_ids(odata)
        acctinfo = banktotals(acname, statement_values)
# ____________________________________________________________________________________________________________________B.Search.General

        if baselinehit is not None:
            try:
                if baseline_balance in [None, '']:
                    raise ValueError('trusted bank balance is required')
                cutoff_date = datetime.datetime.strptime(baseline_date, "%Y-%m-%d")
                trusted_balance = parse_money(baseline_balance)
                row_count, deposits, withdrawals, trusted = baseline_reconciliation(acname, cutoff_date, trusted_balance)
                err[0] = f'Baseline completed for {acname} through {baseline_date}'
                err[1] = f'Marked {row_count} ledger rows reconciled; deposits ${deposits}; withdrawals ${withdrawals}'
                err[2] = f'Beginning balance for future reconciliation defaults to ${trusted}'
                thismuch = '1'
                odata = dataget_Bank(thismuch, acname, hv[0], statement_values)
                acctinfo = banktotals(acname, statement_values)
            except Exception as exc:
                err[0] = f'Baseline failed: {exc}'

        if reopenhit is not None:
            try:
                reopen_rdate = request.values.get('reopen_rdate') or rdate
                recdate = datetime.datetime.strptime(reopen_rdate, "%Y-%m-%d")
                hv[0] = reopen_rdate
                rdate = reopen_rdate
                row_count, reopen_msg = reopen_reconciliation(acname, recdate)
                err[0] = reopen_msg
                if row_count:
                    thismuch = '5'
                    odata = dataget_Bank(thismuch, acname, hv[0], statement_values)
                    hv[1] = selected_statement_ids(acname, hv[0]) or trial_ids(odata)
                    reopened = reconciliation_for_date(acname, recdate, [0, 25, 1])
                    if reopened is not None:
                        statement_values.update({'begbal': reopened.Bbal, 'endbal': reopened.Ebal, 'rdate': hv[0]})
                    acctinfo = banktotals(acname, statement_values)
            except Exception as exc:
                err[0] = f'Reopen failed: {exc}'

        if repairhit is not None:
            try:
                repair_rdate = request.values.get('reopen_rdate') or rdate
                recdate = datetime.datetime.strptime(repair_rdate, "%Y-%m-%d")
                hv[0] = repair_rdate
                rdate = repair_rdate
                row_count, repair_msg = repair_statement_reconciliation_flags(acname, recdate)
                err[0] = repair_msg
                thismuch = '5'
                odata = dataget_Bank(thismuch, acname, hv[0], statement_values)
                hv[1] = selected_statement_ids(acname, hv[0]) or trial_ids(odata)
                repaired = reconciliation_for_date(acname, recdate, [0, 25, 1])
                if repaired is not None:
                    statement_values.update({'begbal': repaired.Bbal, 'endbal': repaired.Ebal, 'rdate': hv[0]})
                acctinfo = banktotals(acname, statement_values)
            except Exception as exc:
                err[0] = f'Repair failed: {exc}'

        if modlink==0:
            oder,numchecked=numcheck(1,odata,0,0,0,0,['oder'])
            group_ids = selected_bank_ids(odata)
            if group_ids:
                numchecked = len(group_ids)

# ____________________________________________________________________________________________________________________E.Search.General
        if (recothese is not None or finalize is not None) and recready == 1:

            if numchecked > -1:

                reset_trial(0, acname)
                #Get date of reconciliation and bank charges for month
                rdate = request.values.get('rdate')
                recdate = datetime.datetime.strptime(rdate, "%Y-%m-%d")
                recmo = recdate.month
                #if recothese is not None: recmo = 25 #Do not record month until reconciliation final
                bkchargeid = 0

                selected_odervec = selected_bank_ids(odata)
                _, cutoff = statement_period_bounds(acname, rdate, statement_values)
                odervec = []
                skipped_future = []
                for selected_id in selected_odervec:
                    selected_row = Gledger.query.get(selected_id)
                    if selected_row is not None and ledger_date_after_cutoff(selected_row.Date, cutoff):
                        skipped_future.append(selected_id)
                    else:
                        odervec.append(selected_id)
                if skipped_future:
                    err.append(
                        f'Skipped {len(skipped_future)} item(s) dated after statement date {rdate}.'
                    )
                print('bkid=',bkchargeid)
                if bkchargeid > 0 and bkchargeid not in odervec: odervec.append(bkchargeid)
                hv[1] = odervec
                print('hv[1]', hv[1])
                for oder in odervec:
                    gdat = Gledger.query.get(oder)
                    if gdat is not None and gdat.Account == acname:
                        gdat.Reconciled=25
                db.session.commit()
                acctinfo = banktotals(acname, statement_values, use_saved_statement=False)
                hv[2], hv[3], hv[4], dlist, wlist = recon_totals(acname, rdate, use_saved_statement=False, statement_values=statement_values)
                print(hv[2],hv[3])
                trial_saved = True
                try:
                    save_trial_reconciliation(
                        acname, recdate, acctinfo[9], acctinfo[4], hv[2], hv[3], hv[4], dlist, wlist, acctinfo[5],
                        selected_reconciliation_id,
                        statement_values,
                    )
                except ValueError as exc:
                    trial_saved = False
                    err.append(str(exc))
                thismuch = '5'
                odata = dataget_Bank(thismuch, acname, hv[0], statement_values)
                hv[1] = selected_statement_ids(acname, hv[0]) or trial_ids(odata)

                if finalize is not None and not trial_saved:
                    err.append('Cannot finalize because the trial reconciliation was not saved.')

                if finalize is not None and trial_saved and abs(parse_money(acctinfo[5])) > .01:
                    err.append(f'Cannot finalize because the statement is out of balance by ${acctinfo[5]}.')

                if finalize is not None and trial_saved and abs(parse_money(acctinfo[5])) <= .01:
                    reset_trial(recmo, acname, odervec)
                    synced_bills = sync_bills_for_ledger_ids(odervec)
                    reconciled_jobs = mark_reconciled_payment_jobs(odervec)
                    hv[1] = [0]
                    rdat = reconciliation_for_date(acname, hv[0])
                    try:
                        dlists = recon_list_text(dlist)
                    except:
                        dlists = None
                    try:
                        wlists = recon_list_text(wlist)
                    except:
                        wlists = None
                    if rdat is None:
                        input = Reconciliations(Account=acname,Rdate=hv[0],Bbal=acctinfo[9],Ebal=acctinfo[4],Deposits=hv[2],Withdraws=hv[3],Servicefees=hv[4],DepositList=dlists,WithdrawList=wlists,Status=1,Diff=acctinfo[5])
                        db.session.add(input)
                        db.session.commit()
                    else:
                        print('diff', acctinfo[5])
                        rdat.Account = acname
                        rdat.Bbal = acctinfo[9]
                        rdat.Ebal = acctinfo[4]
                        rdat.Servicefees = hv[4]
                        rdat.Deposits = hv[2]
                        rdat.Withdraws = hv[3]
                        rdat.DepositList = dlists
                        rdat.WithdrawList = wlists
                        rdat.Status = 1
                        rdat.Rdate = hv[0]
                        rdat.Diff = acctinfo[5]
                        db.session.commit()
                    err.append(f'Reconciliation data saved for Account {acname} Date: {hv[0]}')
                    if synced_bills:
                        err.append(f'Marked {synced_bills} bill payment row(s) as bank reconciled')
                    if reconciled_jobs:
                        err.append(f'Marked {reconciled_jobs} paid job(s) as bank reconciled')

            else:
                err.append('No items checked for reconciliation')

        if undothese is not None:

            odervec = selected_bank_ids(odata)
            for oder in odervec:
                gdat = Gledger.query.get(oder)
                if gdat is not None and gdat.Account == acname:
                    gdat.Reconciled=0
                db.session.commit()
                acctinfo = banktotals(acname, statement_values)
            synced_bills = sync_bills_for_ledger_ids(odervec)
            if synced_bills:
                err.append(f'Updated reconciliation status for {synced_bills} bill row(s).')
# ____________________________________________________________________________________________________________________B.Modify.General
        if (modify is not None or vmod is not None) and numchecked==1 :
            modlink=1
            leftsize=6
            if vmod is not None:
                leftscreen=0

            if oder>0:
                modata=Income.query.get(oder)
                docref=modata.Original

        if (modify is not None or vmod is not None) and numchecked!=1:
            modlink=0
            err[0]=' '
            err[2]='Must check exactly one box to use this option'
# ____________________________________________________________________________________________________________________E.Modify.General

# ____________________________________________________________________________________________________________________B.Delete.General
        if deletehit is not None and numchecked==1:
            if oder>0:
                #This section is to determine if we can delete the source file along with the data.  If other data is pointing to this
                #file then we need to keep it.
                modata=Income.query.get(oder)

                Income.query.filter(Income.id == oder).delete()
                db.session.commit()

        if deletehit is not None and numchecked != 1:
            err=[' ', ' ', 'Must have exactly one item checked to use this option', ' ',  ' ']


# ____________________________________________________________________________________________________________________E.Delete.General
        if (depositmake is not None or recdeposit is not None) and depojo is not None:
            err=['Must have exactly one item checked to use this option', ' ',  ' ']

            odervec = numcheckv(odata)
            if len(odervec)>0:
                oderstring = json.dumps(odervec)
            else:
                udat=users.query.filter(users.name=='cache').first()
                oderstring = udat.email
                odervec = json.loads(oderstring)

            if odervec is not None:
                cache = request.values.get('cache')
                if cache is None:
                    cache = 2

                if recdeposit is not None:
                    cache,docref=reportmaker('recdeposit',odervec)
                    for oder in odervec:
                        idat=Income.query.get(oder)
                        subjo = idat.SubJo
                        ref = idat.Ref
                        idata = Income.query.filter((Income.SubJo==subjo) & (Income.Ref==ref) ).all()
                        for data in idata:
                            data.SubJo = depojo
                            db.session.commit()


                    from gledger_write import gledger_write
                    gledger_write('deposit',depojo,acctsel,0, 0, 0)

                else:
                    cache,docref=reportmaker('deposit',odervec)

                leftscreen = 0


        if viewo is not None and numchecked == 1:
            if oder>0:
                modata=Income.query.get(oder)
                depojo = modata.SubJo
                docref = f'tmp/{scac}/data/vdeposits/' + depojo + '.pdf'
                leftscreen = 0



        if unrecord is not None and numchecked!=1:
            modlink=0
            err[0]=' '
            err[2]='Must check exactly one box to use this option'



        if cache is not None:
            #Save the current cache so we do not start from bad place in future
            udat=users.query.filter(users.name=='cache').first()
            udat.username=str(cache)
            udat.email=oderstring
            db.session.commit()

    #This is the else for 1st time through (not posting data from overseas.html)
    else:
        from webapp.viewfuncs import popjo, jovec, timedata, nonone, nononef, init_truck_zero,d2s, erud
        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        hv = [0]*9
        hv[0] = today_str
        hv[1] = [0]
        now = datetime.datetime.now().strftime('%I:%M %p')
        oder=0
        modata=0
        modlink=0
        odata = Income.query.all()
        leftscreen=1
        leftsize=10
        docref=''
        err=['All is well', ' ', ' ', ' ',  ' ']
        thismuch = '1'
        udat=users.query.filter(users.name=='Cache').first()
        cache=udat.username
        cache=nonone(cache)
        adat = Accounts.query.filter(Accounts.Type=='Bank').first()
        bankacct = adat.Name
        defaults = statement_defaults(bankacct, today_str)
        hv[0] = defaults['rdate']
        statement_values = {
            'begbal': defaults['begbal'],
            'endbal': defaults['endbal'],
            'rdate': hv[0],
            'statement_period_start': '',
            'statement_period_end': '',
        }
        acctinfo = banktotals(bankacct, statement_values)
        odata = dataget_Bank(thismuch, bankacct, hv[0], statement_values)
        hv[1] = trial_ids(odata)


    leftsize = 8
    acdata = Accounts.query.filter(
        ~Accounts.Type.in_(['Income', 'Expense'])
    ).order_by(Accounts.Co, Accounts.Type, Accounts.Name).all()
    err=erud(err)



    return odata,oder,err,modata,modlink,leftscreen,leftsize,today,now,docref,cache,acdata,thismuch,acctinfo,hv
