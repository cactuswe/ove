# api/anthropic.py
import json
import os
import importlib
from http import HTTPStatus

def handler(request):
    # 0) Kontrollera att anthropic-SDK finns installerat
    try:
        anthropic = importlib.import_module("anthropic")
    except ImportError:
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Server configuration error: anthropic SDK is not installed"
            })
        }

    # 1) Kontrollera API-nyckeln
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Server configuration error: missing ANTROPIC_API_KEY"
            })
        }

    client = anthropic.Client(api_key=api_key)

    # 2) Läs in och validera POST-body
    try:
        payload = request.json()
    except Exception:
        return {
            "statusCode": HTTPStatus.BAD_REQUEST,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Invalid JSON in request body"})
        }

    user_input = payload.get("message")
    if not user_input:
        return {
            "statusCode": HTTPStatus.BAD_REQUEST,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing 'message' field"})
        }

    # 3) Anropa Anthropics API
    try:
        resp = client.completions.create(
            model="claude-3",
            prompt=f"Human: {user_input}\n\nAssistant:",
            max_tokens_to_sample=300
        )
        return {
            "statusCode": HTTPStatus.OK,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"reply": resp.completion})
        }

    except Exception as e_raw:
        # Dela upp ApiError vs. andra fel
        ApiError = getattr(anthropic, "ApiError", None)
        if ApiError and isinstance(e_raw, ApiError):
            status = HTTPStatus.BAD_GATEWAY
            err_type = "Anthropic API error"
        else:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            err_type = "Internal server error"

        return {
            "statusCode": status,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": err_type,
                "details": str(e_raw)
            })
        }
