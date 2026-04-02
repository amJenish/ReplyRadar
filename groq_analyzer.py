import json
import re
from groq import Groq


def needs_response(email_data, api_key):
    client = Groq(api_key=api_key)

    prompt = f"""You are an email assistant. Decide whether the following email requires a response from the recipient.

From: {email_data['sender']}
Subject: {email_data['subject']}
Body:
{email_data['body']}

Emails that need a response: direct questions, requests, meeting invites, action items, emails expecting a reply.
Emails that do NOT need a response: newsletters, automated notifications, receipts, one-way announcements, marketing emails, social media alerts.

Respond ONLY with this JSON:
{{"needs_response": true or false, "reason": "one sentence explanation"}}

No other text."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()

    try:
        result = json.loads(raw)
        return result.get("needs_response", False), result.get("reason", "")
    except json.JSONDecodeError:
        return False, "Could not parse response"