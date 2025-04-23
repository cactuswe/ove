# api/anthropic.py
#
# Vercel Serverless Function i Python som motsvarar din gamla
# api/anthropic.js.  Kräver `requests` i requirements.txt.

from http.server import BaseHTTPRequestHandler
import json, os, traceback, requests


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


class handler(BaseHTTPRequestHandler):                   # Vercel fångar klassen "handler" :contentReference[oaicite:0]{index=0}
    """POST /api/anthropic  — returnerar { reply: <text> }"""

    # –– Hjälpmetod –––––––––––––––––––––––––––––––––––––––
    def _json(self, status: int, obj: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())
        return

    # –– Enda tillåtna metod ––––––––––––––––––––––––––––––
    def do_POST(self):                                      # pylint: disable=invalid-name
        # 1. Läs body
        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            data = json.loads(raw or b"{}")
        except Exception:                                   # noqa: E722
            return self._json(400, {"error": "Invalid JSON"})

        # 2. Validera
        message = data.get("message", "").strip()
        history = data.get("history", [])
        if not message:
            return self._json(400, {"error": "Missing or invalid 'message' field"})
        if not isinstance(history, list):
            return self._json(400, {"error": "'history' must be an array"})

        # 3. Bygg prompt
        conv_lines = [
            f"{'Ove' if m.get('role') == 'assistant' else 'Användare'}: {m.get('content','')}"
            for m in history
        ]
        prompt = (
            SYSTEM_PROMPT
            + "\n\n"
            + "\n".join(conv_lines)
            + f"\nAnvändare: {message}\nOve:"
        )

        # 4. Ring Anthropic
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/complete",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": os.getenv("ANTHROPIC_API_KEY", ""),
                },
                json={"model": "claude-3", "prompt": prompt, "max_tokens_to_sample": 300},
                timeout=30,
            )
        except Exception as err:                            # noqa: E722
            traceback.print_exc()
            return self._json(500, {"error": f"Server error: {err}"})

        if not resp.ok:
            return self._json(resp.status_code, {"error": resp.text})

        completion = resp.json().get("completion")
        if not isinstance(completion, str):
            return self._json(502, {"error": "Invalid response from Anthropic"})

        return self._json(200, {"reply": completion.strip()})
