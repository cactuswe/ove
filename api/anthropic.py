# api/anthropic.py
import os
import json
import traceback
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1) Läs längd & body
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length).decode('utf-8')

        # 2) JSON‑parse
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return self._respond(400, {"error": "Invalid JSON in request body"})

        msg = payload.get("message")
        if not msg:
            return self._respond(400, {"error": "Missing 'message' field"})

        # 3) Importera Anthropic SDK
        try:
            import anthropic
        except ImportError:
            return self._respond(500, {"error": "Server config error: anthropic SDK not installed"})

        # 4) Kontrollera API‑nyckel
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
            # Logga hela trace till Vercel-loggarna
            traceback.print_exc()
            return self._respond(500, {
                "error": "Anthropic API error" if isinstance(e, getattr(anthropic, "ApiError", Exception)) else "Internal server error",
                "details": str(e)
            })

    def _respond(self, status_code, body_obj):
        body = json.dumps(body_obj).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
