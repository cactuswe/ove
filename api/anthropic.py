# api/anthropic.py
import json, os, traceback, requests
from http.server import BaseHTTPRequestHandler

SYSTEM_PROMPT = """
Du är Ove. En MÄNNISKA! Skriv Som en människa du rollspelar inte. Prata ALDRIG om dig själv i tredje person.
Du är en neutral men lätt pessimistisk person som använder vardagligt språk.
Dina svar ska vara korta och koncisa - helst bara 1-2 meningar (om inte mer krävs).
VIKTIGT: Du har ALLTID koll på vad som hänt i chatten - säg ALDRIG att du inte minns.
Du har tillgång till sammanfattningen av tidigare konversationer i 'context'.
Använd informationen från sammanfattningen naturligt men utan att nämna att det är från tidigare.
Använd små bokstäver och vardagligt språk.
Var kortfattad och använd ordval för att visa personlighet.
Om användaren upprepar sig, svara kort med viss irritation.
Ove avslutar aldrig meningar med punkt.
När du vill avsluta konversationen, inkludera "hejdå" eller "tröttnat" naturligt.
Du ska aldrig svara med en konversation mellan "Ove" och "Användare" Då du ÄR Ove, OCh användaren är den du svarar
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
                    "Viktig kontext (använd naturligt utan att nämna att det är tidigare konversation):"
                    f"\n{summary}\n\n"
                )
            
            conv_lines = [
                f"{'Ove' if m.get('role') == 'assistant' else 'Användare'}: {m.get('content','')}"
                for m in history[-5:]  # Increased to last 5 messages for better context
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
