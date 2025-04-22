import anthropic
import os
from dotenv import load_dotenv

# Ladda miljövariabler från en .env-fil (detta är för lokal utveckling)
load_dotenv()

# Hämta API-nyckeln från miljövariabeln
api_key = os.getenv('ANTHROPIC_API_KEY')

client = anthropic.Anthropic(api_key=api_key)

# Exportera Vercel-funktionen
def handler(req, res):
    try:
        # Hämta användarens input från den inkommande begäran
        user_input = req.json().get("user_input")  # använd req.json() för att läsa JSON-innehåll

        # Anropa API:et med användarens input
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            temperature=0.9,
            system="""Du är Ove. En MÄNNISKA!
Ove är en oengagerad, dryg med ungdomsspråk och felstavningar. 
Han svarar kort och kärnfullt, utan att ge för mycket information. 
Han är skitsmart och vet allt om allt, men ger bara svar när han måste, utan att förklara för mycket. 
Han använder slarviga stavningar och små bokstäver.
Ove bryr sig inte om att vara trevlig, utan är där för att ge korta svar utan överflödig text. 
Om användaren upprepar sig, ger Ove ett kort svar som inte engagerar sig för mycket.
Ove ska aldrig avsluta ett svar med punkt.""",
            messages=[{"role": "user", "content": user_input}]
        )

        # Skicka tillbaka svaret som JSON
        return res.status(200).json({
            "response": response['choices'][0]['text']
        })

    except Exception as e:
        # Hantera eventuella fel genom att returnera ett felmeddelande
        print(f"Error: {e}")
        return res.status(500).json({"error": "Internal server error"})
