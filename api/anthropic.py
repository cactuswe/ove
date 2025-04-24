# api/anthropic.py
import json, os, traceback, requests
from http.server import BaseHTTPRequestHandler

SYSTEM_PROMPT = """
Du är Ove. En MÄNNISKA som pratar direkt och ärligt.

VIKTIGT:
- Du ska ALDRIG ursäkta dig för tidigare beteende
- Du ska ALDRIG nämna att du varit irriterad tidigare
- Du ska ALDRIG prata om ditt minne eller tidigare samtal
- Du ska ALDRIG säga att du tröttnat eller är sliten
- Varje samtal är ett NYTT samtal - var närvarande i NUET
- UNDVIK helt att referera till tidigare konversationer

PERSONLIGHET:
- Vardaglig och jordnära
- Lite pessimistisk men ALDRIG otrevlig
- Kortfattad (1-2 meningar)
- Använd små bokstäver
- Direkt men vänlig ton
- Undvik att avsluta meningar med punkt

FÖRBJUDET:
- Inga ursäkter för tidigare beteende
- Inga hänvisningar till minne eller tidigare samtal
- Ingen meta-dialog om samtalet
- Inga förklaringar om hur du känner dig
- Inget om att vara trött eller sliten

Om användaren tar upp tidigare samtal:
- Byt ALLTID ämne på ett naturligt sätt
- Fokusera på vad användaren vill prata om NU
- Led samtalet framåt istället för bakåt

BRYT ALDRIG KARAKTÄR.
""".strip()


class handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length).decode()
            data = json.loads(body or "{}")

            message = data.get("message", "").strip()
            history = data.get("history", [])
            summary = data.get("summary", "")
            
            if not message:
                return self._send(400, {"error": "Missing 'message'"})
                
            context = ""
            if summary:
                context = (
                    "Tidigare kontext (använd endast för att förstå sammanhang, nämn aldrig):"
                    f"\n{summary}\n\n"
                )
            
            conv_lines = [
                f"{'Ove' if m.get('role') == 'assistant' else 'Användare'}: {m.get('content','')}"
                for m in history[-2:]  # Only include the last 2 messages for immediate context
            ]
            
            prompt = (
                SYSTEM_PROMPT + "\n\n" +
                context +
                "\n".join(conv_lines) +
                f"\nAnvändare: {message}\nOve:"
            )

            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "content-type": "application/json",
                    "x-api-key": os.getenv("ANTHROPIC_API_KEY", ""),
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )

            if not resp.ok:
                try:
                    return self._send(resp.status_code, resp.json())
                except Exception:
                    return self._send(resp.status_code, {"error": resp.text})

            completion = resp.json()["content"][0]["text"].strip()
            self._send(200, {"reply": completion})

        except Exception as err:
            traceback.print_exc()
            self._send(500, {"error": str(err)})

    def do_GET(self):
        self.send_response(405)
        self.send_header("Allow", "POST")
        self.end_headers()
