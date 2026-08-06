from flask import Flask
from flask_jwt_extended import create_access_token
from pathlib import Path

from webapp.bot.routes import bot_bp
from webapp.bot_skills import (
    DELIVERY_ORDER_SKILL_KEY,
    QUOTE_SKILL_KEY,
    bot_skill_rows,
    get_bot_skill_setting,
    set_bot_skill_enabled,
)
from webapp.bot_usage import record_usage_events, usage_dashboard
from webapp.authenticate.routes import authenticate
from webapp.extensions import db, jwt, login_manager
from webapp.models import users
from webapp.routes import main


def make_app():
    template_folder = Path(__file__).resolve().parents[1] / 'webapp' / 'templates'
    app = Flask(__name__, template_folder=str(template_folder))
    app.config.update(
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)
    return app


def test_quote_skill_defaults_enabled_and_can_be_disabled():
    app = make_app()
    with app.app_context():
        setting = get_bot_skill_setting(QUOTE_SKILL_KEY)
        assert setting.enabled is True

        setting = set_bot_skill_enabled(QUOTE_SKILL_KEY, False, 'admin-user')
        assert setting.enabled is False
        assert setting.updated_by == 'admin-user'

        rows = bot_skill_rows()
        assert rows[0]['key'] == QUOTE_SKILL_KEY
        assert rows[0]['enabled'] is False
        assert rows[1]['key'] == DELIVERY_ORDER_SKILL_KEY
        assert rows[1]['enabled'] is True


def test_unknown_skill_is_rejected():
    app = make_app()
    with app.app_context():
        assert get_bot_skill_setting('not-a-skill') is None
        assert set_bot_skill_enabled('not-a-skill', False) is None


def test_bot_status_endpoint_returns_company_setting():
    app = make_app()
    app.config['JWT_SECRET_KEY'] = 'test-secret-key-that-is-at-least-32-bytes-long'
    jwt.init_app(app)
    app.register_blueprint(bot_bp)

    with app.app_context():
        set_bot_skill_enabled(QUOTE_SKILL_KEY, False, 'admin-user')
        token = create_access_token(
            identity='test-bot',
            additional_claims={
                'token_type': 'bot',
                'scopes': ['read:orders'],
            },
        )

    response = app.test_client().get(
        f'/bot/skills/{QUOTE_SKILL_KEY}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200
    assert response.get_json()['enabled'] is False


def test_usage_events_are_deduplicated_and_summarized():
    app = make_app()
    event = {
        'event_key': 'session-1:response-1', 'skill_key': DELIVERY_ORDER_SKILL_KEY,
        'session_id': 'session-1', 'response_id': 'response-1', 'model': 'gpt-5.4',
        'input_tokens': 100, 'output_tokens': 20, 'cache_read_tokens': 50,
        'cache_write_tokens': 0, 'total_tokens': 170, 'cost_usd': '0.0123',
        'occurred_at': '2026-08-06T12:30:00Z',
    }
    with app.app_context():
        assert record_usage_events('test-bot', [event]) == (1, 0)
        assert record_usage_events('test-bot', [event]) == (0, 1)
        usage = usage_dashboard(now=__import__('datetime').datetime(2026, 8, 6, 12, 45))
        assert usage['hour']['tokens'] == 170
        assert str(usage['day']['cost']) == '0.01230000'
        assert usage['rows'][0]['skill_key'] == DELIVERY_ORDER_SKILL_KEY


def test_bot_can_report_usage():
    app = make_app()
    app.config['JWT_SECRET_KEY'] = 'test-secret-key-that-is-at-least-32-bytes-long'
    jwt.init_app(app)
    app.register_blueprint(bot_bp)
    with app.app_context():
        token = create_access_token(identity='test-bot', additional_claims={
            'token_type': 'bot', 'scopes': ['write:orders'],
        })
    event = {
        'event_key': 'session-2:response-2', 'skill_key': DELIVERY_ORDER_SKILL_KEY,
        'session_id': 'session-2', 'response_id': 'response-2', 'model': 'gpt-5.4',
        'input_tokens': 10, 'output_tokens': 5, 'total_tokens': 15,
        'cost_usd': 0.001, 'occurred_at': '2026-08-06T12:30:00Z',
    }
    response = app.test_client().post('/bot/usage', json={'events': [event]},
                                      headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert response.get_json()['inserted'] == 1


def test_admin_can_render_and_toggle_bot_skill_page():
    app = make_app()
    app.config.update(
        SECRET_KEY='test-session-secret',
        TESTING=True,
    )
    login_manager.init_app(app)
    app.register_blueprint(authenticate)
    app.register_blueprint(main)

    with app.app_context():
        users.__table__.create(bind=db.engine, checkfirst=True)
        admin = users(
            name='Admin User',
            email='admin@example.com',
            username='admin-user',
            password='unused',
            authority='admin',
        )
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    client = app.test_client()
    with client.session_transaction() as user_session:
        user_session['_user_id'] = str(admin_id)
        user_session['_fresh'] = True
        user_session['authority'] = 'admin'

    response = client.get('/admin/bot-skills')
    assert response.status_code == 200
    assert b'Bot automation' in response.data
    assert b'Quote automation' in response.data
    assert b'AI usage' in response.data

    response = client.post(
        '/admin/bot-skills',
        data={'skill_key': QUOTE_SKILL_KEY, 'enabled': '0'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b'Quote automation turned off.' in response.data
    with app.app_context():
        assert get_bot_skill_setting(QUOTE_SKILL_KEY).enabled is False
