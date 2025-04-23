# api/anthropic.py

import os
import json
import traceback
from http.server import BaseHTTPRequestHandler

# Din system-prompt
system_prompt = """
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
"""

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1) Läs längd & body
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")

        # 2) JSON-parse
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return self._respond(400, {"error": "Invalid JSON in request body"})

        user_input = payload.get("message")
        history    = payload.get("history", [])

        if not isinstance(user_input, str) or not user_input.strip():
            return self._respond(400, {"error": "Missing or invalid 'message' field"})
        if not isinstance(history, list):
            return self._respond(400, {"error": "'history' must be a list"})

        # 3) Initiera Anthropics-klient
        try:
            import anthropic
        except ImportError:
            return self._respond(500, {"error": "Anthropic SDK not installed"})

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return self._respond(500, {"error": "Missing ANTHROPIC_API_KEY"})

        client = anthropic.Client(api_key=api_key)

        # 4) Lägg på användarens meddelande i historiken
        history.append({"role": "user", "content": user_input})

        # 5) (Valfritt) sammanfatta om historiken blir för lång
        if len(history) > 6:
            to_summarize = history[:-6]
            text = "\n".join(f"{m['role']}: {m['content']}" for m in to_summarize)
            summary_resp = client.completions.create(
                model="claude-3",
                prompt=f"Sammanfatta kort:\n{text}",
                max_tokens_to_sample=200
            )
            summary = summary_resp.completion.strip()
            history = [{"role": "assistant", "content": f"Sammanfattning: {summary}"}] + history[-6:]

        # 6) Skicka den fulla prompten till Claude 3
        full_resp = client.completions.create(
            model="claude-3",
            prompt=system_prompt + "\n\n" + "\n".join(
                f"{m['role'].capitalize()}: {m['content']}" for m in history
            ),
            max_tokens_to_sample=300
        )
        answer = full_resp.completion.strip()
        history.append({"role": "assistant", "content": answer})

        # 7) Svara med JSON
        return self._respond(200, {"reply": answer, "history": history})

    def _respond(self, status, body_obj):
        body = json.dumps(body_obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
