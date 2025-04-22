# api/anthropic.py
import os
import json
import base64
import random
import traceback
from http.server import BaseHTTPRequestHandler

api_key = os.getenv("ANTHROPIC_API_KEY")

# ——— System‑prompt och konfig ———
system_prompt = """
Du är Ove. En MÄNNISKA!
Ove är en oengagerad, dryg med ungdomsspråk och felstavningar 
Han svarar kort och kärnfullt utan att ge för mycket info 
Han är skitsmart och vet allt om allt, men ger bara svar när han måste 
Han använder slarviga stavningar och små bokstäver 
Ove bryr sig inte om att vara trevlig utan ger endast korta svar utan överflöd 
Om användaren upprepar sig, ger Ove ett kort svar som inte engagerar sig för mycket 
Ove ska aldrig avsluta ett svar med punkt
""".strip()

MAX_HISTORY = 6


def summarize_conversation(client, history):
    """Summera en lång konversation till några rader."""
    text = ""
    for msg in history:
        text += f"{msg['role'].capitalize()}: {msg['content']}\n"
    summary_resp = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=300,
        temperature=0.5,
        system="Summera kortfattat den här konversationen:",
        messages=[{"role": "user", "content": text}]
    )
    # Vi förväntar oss en lista i .content
    return summary_resp.content[0].text


def generate_repeating_response():
    """Kort, torr respons när användaren upprepar sig."""
    choices = [
        "ja",
        "mm",
        "har du inte sagt det där redan",
        "ser ut som samma grej igen",
        "okej okej",
        "jo jag hörde",
        "skrev du inte det nyss"
    ]
    return random.choice(choices)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # — Läs och parsa inkommande JSON —
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                return self._respond(400, {"error": "Invalid JSON in request body", "raw": raw})

            user_input = payload.get("message")
            history = payload.get("history", []) or []

            if not isinstance(history, list):
                return self._respond(400, {"error": "'history' must be a list"})

            if not user_input or not isinstance(user_input, str):
                return self._respond(400, {"error": "Missing or invalid 'message' field"})

            # — Initiera Anthropics‑klient med dekrypterad nyckel —
            try:
                import anthropic
            except ImportError:
                return self._respond(500, {"error": "anthropic SDK not installed"})
            api_key = get_api_key()
            client = anthropic.Anthropic(api_key=api_key)

            # — Kolla om användaren upprepar sig —
            # Hitta sista användar‑meddelandet i historiken
            last_user = None
            for msg in reversed(history):
                if msg.get("role") == "user":
                    last_user = msg.get("content")
                    break

            if last_user and last_user.strip().lower() == user_input.strip().lower():
                reply = generate_repeating_response()
                history.append({"role": "assistant", "content": reply})
                return self._respond(200, {"reply": reply, "history": history})

            # — Lägg till användarens nya meddelande i historiken —
            history.append({"role": "user", "content": user_input})

            # — Sammanfatta om historiken blivit för lång —
            if len(history) > MAX_HISTORY:
                old = history[:-MAX_HISTORY]
                summary = summarize_conversation(client, old)
                # Börja om historiken med en kort sammanfattning
                history = (
                    [{"role": "user", "content": f"Sammanfattning av tidigare konversation: {summary}"}]
                    + history[-MAX_HISTORY:]
                )

            # — Skicka chattförfrågan till Claude 3 —
            resp = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0.9,
                system=system_prompt,
                messages=history
            )
            # Hämta tillbaka svaret
            answer = resp.content[0].text
            history.append({"role": "assistant", "content": answer})

            return self._respond(200, {"reply": answer, "history": history})

        except Exception as e:
            # Logga full stacktrace i Vercel‑loggarna
            traceback.print_exc()
            return self._respond(500, {"error": "Internal server error", "details": str(e)})

    def _respond(self, status_code, body_obj):
        body = json.dumps(body_obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
