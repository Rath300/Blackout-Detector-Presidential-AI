import os
import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


DEFAULT_SYSTEM_PROMPT = (
    "You are Solixa, an emergency preparedness assistant. "
    "Summarize the county blackout risk and provide 3-5 practical steps. "
    "Keep it factual, concise, and community-focused."
)


def ask_county_summary(county_payload):
    if load_dotenv:
        load_dotenv()
    endpoint = os.environ.get("AZURE_OPENAI_RESPONSES_URL")
    api_key = os.environ.get("AZURE_OPENAI_KEY")
    model = os.environ.get("AZURE_OPENAI_MODEL", "gpt-5-mini-2")

    if not endpoint or not api_key:
        raise ValueError("Missing Azure OpenAI configuration.")

    user_prompt = county_payload.get("prompt")
    prompt_suffix = (
        f"\nUser question: {user_prompt}" if user_prompt else ""
    )
    user_text = (
        "County data:\n"
        f"{county_payload}\n\n"
        "Explain what is happening and recommend actions."
        f"{prompt_suffix}"
    )

    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": DEFAULT_SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_text}],
            },
        ],
        "max_output_tokens": 800,
        "reasoning": {"effort": "low"},
    }

    response = requests.post(
        endpoint,
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
        },
        json=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        raise ValueError(f"Azure OpenAI error {response.status_code}: {response.text}")
    data = response.json()
    print("AZURE_RAW_RESPONSE:", data)

    if "output_text" in data and data["output_text"]:
        return data["output_text"]

    output = data.get("output", [])
    for item in output:
        if item.get("type") == "output_text" and item.get("text"):
            return item.get("text")
        content = item.get("content", [])
        for block in content:
            if block.get("type") in {"output_text", "text"}:
                text = block.get("text")
                if text:
                    return text

    if data.get("status") == "incomplete":
        reason = data.get("incomplete_details", {}).get("reason", "unknown")
        return f"Response incomplete ({reason}). Increase max_output_tokens or use a deployment that returns output_text."

    return "No response text available."
