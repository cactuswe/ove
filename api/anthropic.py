import json
import os
import anthropic
from http import HTTPStatus

client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))

def handler(request):
    try:
        payload = request.json()
    except Exception:
        return {
            "statusCode": HTTPStatus.BAD_REQUEST,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Invalid JSON in request body"})
        }

    user_input = payload.get("message")
    if not user_input:
        return {
            "statusCode": HTTPStatus.BAD_REQUEST,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing ‘message’ field"})
        }

    try:
        # Skicka till Claude 3
        response = client.completions.create(
            model="claude-3",
            prompt=f"Human: {user_input}\n\nAssistant:",
            max_tokens_to_sample=300
        )
        result = response.completion
        # Säkerställ att vi returnerar JSON
        return {
            "statusCode": HTTPStatus.OK,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"reply": result})
        }

    except anthropic.ApiError as e:
        # Fel från Anthropics API
        body = {"error": "Anthropic API error", "details": str(e)}
        return {
            "statusCode": HTTPStatus.BAD_GATEWAY,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body)
        }

    except Exception as e:
        # Ovärntat fel
        body = {"error": "Internal server error", "details": str(e)}
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body)
        }
