from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def bot_token_required(required_scopes=None):
    required_scopes = set(required_scopes or [])

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()

            claims = get_jwt()

            if claims.get("token_type") != "bot":
                return jsonify({"message": "Bot token required"}), 403

            token_scopes = set(claims.get("scopes", []))

            if not required_scopes.issubset(token_scopes):
                return jsonify({"message": "Insufficient scope"}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator