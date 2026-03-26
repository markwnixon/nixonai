from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token

from webapp.extensions import bcrypt
from webapp.models import BotClient  # we’ll create this if you don’t have it yet

bot_auth = Blueprint('bot_auth', __name__)


@bot_auth.route('/api_bot_token', methods=['POST'])
def api_bot_token():
    data = request.get_json(silent=True) or {}

    client_id = (data.get('client_id') or '').strip()
    client_secret = data.get('client_secret') or ''

    if not client_id or not client_secret:
        return jsonify({"message": "client_id and client_secret required"}), 400

    bot = BotClient.query.filter_by(client_id=client_id, active=True).first()

    if bot is None:
        return jsonify({"message": "Invalid credentials"}), 401

    if not bcrypt.check_password_hash(bot.client_secret, client_secret):
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(
        identity=bot.client_id,
        additional_claims={
            "token_type": "bot",
            "client_id": bot.client_id,
            "scopes": bot.scopes.split() if bot.scopes else []
        }
    )

    return jsonify({
        "access_token": access_token,
        "token_type": "bearer",
        "scopes": bot.scopes
    }), 200