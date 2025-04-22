# api/anthropic.py
import os
import json
import importlib
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1) Läs in rå body
        length = int(self.headers.get('Content-Length', 0))
        raw_body = self.rfile.read(length).decode('utf-8')

        # 2) Parsning av JSON
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return self._respond(400, {"error": "Invalid JSON in request body"})

        msg = payload.get("message")
        if not msg:
            return self._respond(400, {"error": "Missing 'message' field"})

        # 3) Ladda SDK (catch ImportError)
        try:
            anthropic = importlib.import_module("anthropic")
        except ImportError:
            return self._respond(500, {
                "error": "Server configuration error: anthropic SDK not installed"
            })

        # 4) Kontrollera att API-nyckel finns
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return self._respond(500, {
                "error": "Server configuration error: missing ANTHROPIC_API_KEY"
            })

        client = anthropic.Client(api_key=api_key)

        # 5) Anropa Claude 3
        try:
            resp = client.completions.create(
                model="claude-3",
                prompt=f"Human: {msg}\n\nAssistant:",
                max_tokens_to_sample=300
            )
            return self._respond(200, {"reply": resp.completion})

        except getattr(anthropic, "ApiError", Exception) as e:
            # ApiError → 502, övriga → 500
            code = 502 if hasattr(anthropic, "ApiError") and isinstance(e, anthropic.ApiError) else 500
            err_type = "Anthropic API error" if code == 502 else "Internal server error"
            return self._respond(code, {"error": err_type, "details": str(e)})

    def _respond(self, status_code, body_obj):
        body = json.dumps(body_obj).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
