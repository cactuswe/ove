# api/anthropic.py
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


def handler(request):
    if request.method != "POST":
        return {
            "statusCode": 405,
            "headers": {"Allow": "POST"},
            "body": json.dumps({"error": "Method Not Allowed"})
        }

    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON"})}

    message = data.get("message", "").strip()
    history = data.get("history", [])
    if not message:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing or invalid 'message' field"})}
    if not isinstance(history, list):
        return {"statusCode": 400, "body": json.dumps({"error": "'history' must be an array"})}

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
    except Exception as err:
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": str(err)})}

    if not resp.ok:
        return {"statusCode": resp.status_code, "body": json.dumps({"error": resp.text})}

    completion = resp.json().get("completion")
    if not isinstance(completion, str):
        return {"statusCode": 502, "body": json.dumps({"error": "Invalid response from Anthropic"})}

    return {
        "statusCode": 200,
        "body": json.dumps({"reply": completion.strip()})
    }
