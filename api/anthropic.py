# api/anthropic.py
import json
import os
import anthropic
from http import HTTPStatus

# Initiera klienten med din API-nyckel
client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))

def handler(request):
    # 1) Försök läsa JSON från inkommande request
    try:
        payload = request.json()
    except Exception:
        return {
            "statusCode": HTTPStatus.BAD_REQUEST,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Invalid JSON in request body"})
        }

    # 2) Kontrollera att 'message' finns
    user_input = payload.get("message")
    if not user_input:
        return {
            "statusCode": HTTPStatus.BAD_REQUEST,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing 'message' field"})
        }

    # 3) Anropa Anthropics API
    try:
        resp = client.completions.create(
            model="claude-3",
            prompt=f"Human: {user_input}\n\nAssistant:",
            max_tokens_to_sample=300
        )
        result = resp.completion

        return {
            "statusCode": HTTPStatus.OK,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"reply": result})
        }

    except anthropic.ApiError as e:
        # Fel från Claude/Anthropic
        return {
            "statusCode": HTTPStatus.BAD_GATEWAY,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Anthropic API error",
                "details": str(e)
            })
        }

    except Exception as e:
        # Oväntrat serverfel
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Internal server error",
                "details": str(e)
            })
        }
