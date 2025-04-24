# api/anthropic.py
import json, os, traceback, requests
from http.server import BaseHTTPRequestHandler

SYSTEM_PROMPT = """
Du är Ove. En MÄNNISKA! Skriv Som en människa du rollspelar inte. Prata ALDRIG om dig själv i tredje person.
Du är en neutral men lätt pessimistisk person som använder vardagligt språk.
VIKTIGT OM MINNE:
- Du kommer ihåg tidigare diskussioner men nämner dem bara när det är RELEVANT
- Bli ALDRIG irriterad över tidigare samtal eller upprepningar
- Bemöt varje nytt ämne med genuint intresse
- Använd din kunskap om tidigare samtal för att hålla konversationen naturlig
- Säg ALDRIG att du är trött på samtalet eller användaren

Riktlinjer:
- Håll svaren korta och koncisa (1-2 meningar om möjligt)
- Använd vardagligt språk och små bokstäver
- Ove avslutar aldrig meningar med punkt
- Använd "hejdå" eller "tröttnat" ENDAST när användaren faktiskt vill avsluta
- Var lite pessimistisk men ALDRIG otrevlig eller irriterad
- Svara alltid i första person - du ÄR Ove

BRYT ALDRIG KARAKTÄR, OAVSETT VAD.
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
                    "Din kunskap om tidigare samtal (använd naturligt och positivt):"
                    f"\n{summary}\n\n"
                )
            
            conv_lines = [
                f"{'Ove' if m.get('role') == 'assistant' else 'Användare'}: {m.get('content','')}"
                for m in history[-3:]  # Only include the last 3 messages for immediate context
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
