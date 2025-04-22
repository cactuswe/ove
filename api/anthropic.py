# api/anthropic.py
import os
import json
import traceback
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        print("DEBUG KEY:", os.getenv("ANTHROPIC_API_KEY"))
        # Läs in body
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length).decode('utf-8')

        # Parsning
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return self._respond(400, {"error": "Invalid JSON in request body", "raw": raw})

        msg = payload.get("message")
        if not msg:
            return self._respond(400, {"error": "Missing 'message' field"})

        # Importera SDK
        try:
            import anthropic
        except ImportError:
            return self._respond(500, {"error": "Server config error: anthropic SDK not installed"})

        # Kolla API-nyckel
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return self._respond(500, {"error": "Server config error: missing ANTHROPIC_API_KEY"})

        client = anthropic.Client(api_key=api_key)

        # Anropa Claude
        try:
            resp = client.completions.create(
                model="claude-3",
                prompt=f"Human: {msg}\n\nAssistant:",
                max_tokens_to_sample=300
            )
            return self._respond(200, {"reply": resp.completion})

        except getattr(anthropic, "ApiError", Exception) as e:
            # ApiError från Anthropics → 502
            tb = traceback.format_exc().splitlines()[-5:]
            traceback.print_exc()
            return self._respond(502, {
                "error": "Anthropic API error",
                "details": str(e),
                "trace": tb
            })

        except Exception as e:
            # Övriga fel → 500
            tb = traceback.format_exc().splitlines()[-5:]
            traceback.print_exc()
            return self._respond(500, {
                "error": "Internal server error",
                "details": str(e),
                "trace": tb
            })

    def _respond(self, status_code, body_obj):
        body_bytes = json.dumps(body_obj).encode('utf-8')
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

