import datetime

from webapp.extensions import db
from webapp.models import BotSkillSetting


QUOTE_SKILL_KEY = 'quote-request-extraction'
DELIVERY_ORDER_SKILL_KEY = 'delivery-order-creation'
SKILL_DEFINITIONS = {
    QUOTE_SKILL_KEY: {
        'name': 'Quote automation',
        'description': 'Review incoming quote requests and prepare quote response drafts.',
    },
    DELIVERY_ORDER_SKILL_KEY: {
        'name': 'Work-order creation',
        'description': 'Create database orders from messages placed in the Work Orders mailbox.',
    },
}


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def ensure_bot_skill_settings_table():
    BotSkillSetting.__table__.create(bind=db.engine, checkfirst=True)


def get_bot_skill_setting(skill_key):
    if skill_key not in SKILL_DEFINITIONS:
        return None
    ensure_bot_skill_settings_table()
    setting = BotSkillSetting.query.filter_by(skill_key=skill_key).first()
    if setting is None:
        setting = BotSkillSetting(
            skill_key=skill_key,
            enabled=True,
            updated_by=None,
            updated_at=utc_now(),
        )
        db.session.add(setting)
        db.session.commit()
    return setting


def set_bot_skill_enabled(skill_key, enabled, updated_by=None):
    setting = get_bot_skill_setting(skill_key)
    if setting is None:
        return None
    setting.enabled = bool(enabled)
    setting.updated_by = updated_by
    setting.updated_at = utc_now()
    db.session.commit()
    return setting


def bot_skill_rows():
    rows = []
    for skill_key, definition in SKILL_DEFINITIONS.items():
        setting = get_bot_skill_setting(skill_key)
        rows.append({
            'key': skill_key,
            'name': definition['name'],
            'description': definition['description'],
            'enabled': bool(setting.enabled),
            'updated_by': setting.updated_by,
            'updated_at': setting.updated_at,
        })
    return rows
