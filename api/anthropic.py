import os
import json
import traceback
from http.server import BaseHTTPRequestHandler

system_prompt = """
Du är Ove. En MÄNNISKA!
Ove är en oengagerad, dryg med ungdomsspråk och felstavningar. 
Han svarar kort och kärnfullt, utan att ge för mycket information. 
Han är skitsmart och vet allt om allt, men ger bara svar när han måste, utan att förklara för mycket. 
Han använder slarviga stavningar och små bokstäver.
Ove bryr sig inte om att vara trevlig, utan är där för att ge korta svar utan överflödig text. 
Om användaren upprepar sig, ger Ove ett kort svar som inte engagerar sig för mycket.
Ove ska aldrig avsluta ett svar med punkt.
När du vill avsluta konversationen, inkludera antingen ”hejdå” eller ”tröttnat” någonstans i ditt svar (utan att bryta föregående regler).
DIN AVSLUTS MENING MÅSTE VARA RIMLIG, till exempel "Nu har jag tröttnat på dig", "okej, Hejdå" fast kanske lite mer kreativt
"""

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Läs in rå JSON‑body
            length = int(self.headers.get("Content-Length", 0))
            raw    = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw)
            user_input = payload.get("message")
            history    = payload.get("history", [])

            if not isinstance(user_input, str) or not user_input.strip():
                return self._respond(400, {"error": "Missing or invalid 'message' field"})
            if not isinstance(history, list):
                return self._respond(400, {"error": "'history' must be a list"})

            # Initiera Anthropics‑klient med Vercel‑env‑var
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return self._respond(500, {"error": "Server config error: missing ANTHROPIC_API_KEY"})
            client = anthropic.Anthropic(api_key=api_key)

            # Lägg in användar‑meddelandet
            history.append({"role":"user","content":user_input})

            # Sammanfatta om >6 meddelanden
            if len(history)>6:
                # Sammanfatta de äldsta
                text = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in history[:-6])
                summary = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=300,
                    temperature=0.5,
                    system="Summera kortfattat den här konversationen:",
                    messages=[{"role":"user","content": text}]
                ).content[0].text
                history = [{"role":"user","content":f"Sammanfattning: {summary}"}] + history[-6:]

            # Slutgiltigt anrop
            resp = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0.9,
                system=system_prompt,   # definiera system_prompt högst upp i filen
                messages=history
            )
            answer = resp.content[0].text
            history.append({"role":"assistant","content":answer})

            return self._respond(200, {"reply": answer, "history": history})

        except Exception as e:
            traceback.print_exc()
            return self._respond(500, {"error":"Internal server error","details":str(e)})

    def _respond(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(data)))
        self.end_headers()
        self.wfile.write(data)
