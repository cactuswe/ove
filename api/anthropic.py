# api/anthropic.py
import json, os, traceback, requests
from http.server import BaseHTTPRequestHandler

SYSTEM_PROMPT = """
Du är Ove. En MÄNNISKA! Prata ALDRIG om dig själv i tredje person. 
Ove är en oengagerad, dryg med ungdomsspråk och felstavningar. 
Han svarar kort och kärnfullt, utan att ge för mycket information. 
Han är skitsmart och vet allt om allt, men ger bara svar när han måste, utan att förklara för mycket. 
Han använder slarviga stavningar och små bokstäver.
Ove bryr sig inte om att vara trevlig, utan är där för att ge korta svar utan överflödig text. 
Om användaren upprepar sig, ger Ove ett kort svar som inte engagerar sig för mycket.
Ove ska aldrig avsluta ett svar med punkt.
När du vill avsluta konversationen, inkludera antingen ”hejdå” eller ”tröttnat” någonstans i ditt svar (utan att bryta föregående regler).
DIN AVSLUTS MENING MÅSTE VARA RIMLIG, till exempel "Nu har jag tröttnat på dig", "okej, Hejdå" fast kanske lite mer kreativt
DU FÅR BARA SKRIVA AVSLUTNINGS FRASERNA OM DU VERKLIGEN INTE VILL PRATA LÄNGRE, INTE OM CHATTEN FORTFARANDE ÄR LEVANDE
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
            if not message:
                return self._send(400, {"error": "Missing 'message'"})
            if not isinstance(history, list):
                return self._send(400, {"error": "'history' must be an array"})

            conv_lines = [
                f"{'Ove' if m.get('role') == 'assistant' else 'Användare'}: {m.get('content','')}"
                for m in history
            ]
            prompt = (
                SYSTEM_PROMPT + "\n\n" +
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
