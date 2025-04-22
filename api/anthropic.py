# api/anthropic.py
import os
import json
import importlib
import traceback
from http import HTTPStatus

def handler(request):
    try:
        # --- Läs body ---
        raw = request.body.decode('utf-8') if hasattr(request, 'body') else request.json()
        try:
            payload = json.loads(raw)
        except Exception:
            return _resp(400, {"error": "Invalid JSON in request body", "raw": raw})

        msg = payload.get("message")
        if not msg:
            return _resp(400, {"error": "Missing 'message' field"})

        # --- Ladda SDK ---
        try:
            anthropic = importlib.import_module("anthropic")
        except ImportError:
            return _resp(500, {"error": "anthropic SDK not installed"})

        # --- Kolla API‑key ---
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return _resp(500, {"error": "Missing ANTHROPIC_API_KEY in env"})

        client = anthropic.Client(api_key=api_key)

        # --- Anropa Claude 3 ---
        resp = client.completions.create(
            model="claude-3",
            prompt=f"Human: {msg}\n\nAssistant:",
            max_tokens_to_sample=300
        )
        return _resp(200, {"reply": resp.completion})

    except Exception as e:
        tb = traceback.format_exc()
        # Skriver samtidigt ut till logs
        print(tb)
        return _resp(500, {
            "error": "Internal server error",
            "details": str(e),
            "trace": tb.splitlines()[-3:]  # de sista tre raderna av trace
        })

def _resp(status, obj):
    body = json.dumps(obj)
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": body
    }
