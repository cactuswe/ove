# api/anthropic.py
import os
import json
import traceback
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1) Läs Content-Length och rå body
        length_str = self.headers.get('Content-Length')
        try:
            length = int(length_str)
        except (TypeError, ValueError):
            length = 0
        raw = self.rfile.read(length).decode('utf-8')

        # 2) Försök parse:a JSON
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return self._respond(400, {"error": "Invalid JSON in request body"})

        msg = payload.get("message")
        if not msg:
            return self._respond(400, {"error": "Missing 'message' field"})

        # 3) Ladda in SDK:t
        try:
            import anthropic
        except ImportError:
            return self._respond(500, {"error": "Server config error: anthropic SDK not installed"})

        # 4) Kontrollera API-nyckeln
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return self._respond(500, {"error": "Server config error: missing ANTHROPIC_API_KEY"})

        client = anthropic.Client(api_key=api_key)

        # 5) Anropa Claude 3
        try:
            resp = client.completions.create(
                model="claude-3",
                prompt=f"Human: {msg}\n\nAssistant:",
                max_tokens_to_sample=300
            )
            return self._respond(200, {"reply": resp.completion})

        except Exception as e:
            # Logga full trace till Vercel-loggarna
            traceback.print_exc()
            is_api_error = hasattr(anthropic, "ApiError") and isinstance(e, anthropic.ApiError)
            status = 502 if is_api_error else 500
            err_type = "Anthropic API error" if is_api_error else "Internal server error"
            return self._respond(status, {"error": err_type, "details": str(e)})

    def _respond(self, status_code, body_obj):
        body_bytes = json.dumps(body_obj).encode('utf-8')
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)
