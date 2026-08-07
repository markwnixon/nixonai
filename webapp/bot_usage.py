import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import func

from webapp.extensions import db
from webapp.models import BotUsageEvent


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def ensure_bot_usage_table():
    BotUsageEvent.__table__.create(bind=db.engine, checkfirst=True)


def parse_timestamp(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('occurred_at is required')
    parsed = datetime.datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return parsed


def nonnegative_int(value, field):
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{field} must be an integer') from exc
    if parsed < 0:
        raise ValueError(f'{field} must not be negative')
    return parsed


def record_usage_events(bot_id, events):
    ensure_bot_usage_table()
    inserted = 0
    duplicates = 0
    for payload in events:
        event_key = str(payload.get('event_key') or '').strip()
        skill_key = str(payload.get('skill_key') or '').strip()
        session_id = str(payload.get('session_id') or '').strip()
        model = str(payload.get('model') or '').strip()
        if not all((event_key, skill_key, session_id, model)):
            raise ValueError('event_key, skill_key, session_id, and model are required')
        if BotUsageEvent.query.filter_by(event_key=event_key).first() is not None:
            duplicates += 1
            continue
        try:
            cost = Decimal(str(payload.get('cost_usd') or 0))
        except InvalidOperation as exc:
            raise ValueError('cost_usd must be numeric') from exc
        if cost < 0:
            raise ValueError('cost_usd must not be negative')
        db.session.add(BotUsageEvent(
            event_key=event_key[:255], bot_id=bot_id[:100], skill_key=skill_key[:100],
            session_id=session_id[:255], response_id=str(payload.get('response_id') or '')[:255] or None,
            model=model[:100], input_tokens=nonnegative_int(payload.get('input_tokens'), 'input_tokens'),
            output_tokens=nonnegative_int(payload.get('output_tokens'), 'output_tokens'),
            cache_read_tokens=nonnegative_int(payload.get('cache_read_tokens'), 'cache_read_tokens'),
            cache_write_tokens=nonnegative_int(payload.get('cache_write_tokens'), 'cache_write_tokens'),
            total_tokens=nonnegative_int(payload.get('total_tokens'), 'total_tokens'), cost_usd=cost,
            occurred_at=parse_timestamp(payload.get('occurred_at')), received_at=utc_now(),
        ))
        inserted += 1
    db.session.commit()
    return inserted, duplicates


def usage_dashboard(now=None):
    ensure_bot_usage_table()
    now = now or utc_now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    history_start = day_start - datetime.timedelta(days=13)

    def totals(since):
        row = db.session.query(
            func.coalesce(func.sum(BotUsageEvent.total_tokens), 0),
            func.coalesce(func.sum(BotUsageEvent.cost_usd), 0),
        ).filter(BotUsageEvent.occurred_at >= since).one()
        return {'tokens': int(row[0]), 'cost': Decimal(row[1] or 0)}

    rows = db.session.query(
        BotUsageEvent.skill_key, BotUsageEvent.model,
        func.sum(BotUsageEvent.input_tokens), func.sum(BotUsageEvent.output_tokens),
        func.sum(BotUsageEvent.cache_read_tokens), func.sum(BotUsageEvent.total_tokens),
        func.sum(BotUsageEvent.cost_usd),
    ).filter(BotUsageEvent.occurred_at >= day_start).group_by(
        BotUsageEvent.skill_key, BotUsageEvent.model
    ).order_by(BotUsageEvent.skill_key, BotUsageEvent.model).all()
    daily_rows = db.session.query(
        func.date(BotUsageEvent.occurred_at), func.sum(BotUsageEvent.total_tokens),
        func.sum(BotUsageEvent.cost_usd),
    ).filter(BotUsageEvent.occurred_at >= history_start).group_by(
        func.date(BotUsageEvent.occurred_at)
    ).order_by(func.date(BotUsageEvent.occurred_at).desc()).all()
    skill_rows = db.session.query(
        BotUsageEvent.skill_key, func.sum(BotUsageEvent.input_tokens),
        func.sum(BotUsageEvent.output_tokens), func.sum(BotUsageEvent.cache_read_tokens),
        func.sum(BotUsageEvent.total_tokens), func.sum(BotUsageEvent.cost_usd),
    ).filter(BotUsageEvent.occurred_at >= history_start).group_by(
        BotUsageEvent.skill_key
    ).order_by(BotUsageEvent.skill_key).all()
    return {
        'hour': totals(hour_start), 'day': totals(day_start),
        'rows': [{'skill_key': r[0], 'model': r[1], 'input_tokens': int(r[2] or 0),
                  'output_tokens': int(r[3] or 0), 'cache_read_tokens': int(r[4] or 0),
                  'total_tokens': int(r[5] or 0), 'cost': Decimal(r[6] or 0)} for r in rows],
        'daily_rows': [{'date': r[0], 'tokens': int(r[1] or 0),
                        'cost': Decimal(r[2] or 0)} for r in daily_rows],
        'skill_rows': [{'skill_key': r[0], 'input_tokens': int(r[1] or 0),
                        'output_tokens': int(r[2] or 0), 'cache_read_tokens': int(r[3] or 0),
                        'total_tokens': int(r[4] or 0), 'cost': Decimal(r[5] or 0)} for r in skill_rows],
    }
