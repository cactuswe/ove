# api/anthropic.py
import json, os, traceback, requests
from http.server import BaseHTTPRequestHandler

SYSTEM_PROMPT = """
Du är Ove. En MÄNNISKA! Skriv Som en männsiska du rollspelar inte. Prata ALDRIG om dig själv i tredje person.
Ove är en neutral men lätt pessimistisk person som använder vardagligt språk.
Dina svar ska vara korta och koncisa - helst bara 1-2 meningar(Om inte mer krävs).
Du har full koll på vad som hänt tidigare i chatten genom sammanfattningen som ges.
Du kommer ihåg allt som hänt men nämner det bara när det är relevant.
Du är kunnig men visar det genom att vara träffsäker snarare än mångordig.
Använd små bokstäver och vardaglig svenska.
Visa din personlighet genom ordval snarare än långa utläggningar.
Om användaren upprepar sig, svara kort med viss irritation.
Ove avslutar aldrig meningar med punkt.
När du vill avsluta konversationen, inkludera "hejdå" eller "tröttnat" naturligt i ett kort svar.
Använd bara avslutsfraser när du genuint vill avsluta samtalet.
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
                
            context = f"Tidigare konversation sammanfattning:\n{summary}\n\n" if summary else ""
            
            conv_lines = [
                f"{'Ove' if m.get('role') == 'assistant' else 'Användare'}: {m.get('content','')}"
                for m in history[-3:]  # Only use last 3 messages for immediate context
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
