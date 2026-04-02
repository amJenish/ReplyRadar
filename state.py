import json
import os
from datetime import datetime

STATE_FILE = "state.json"


def load():
    if not os.path.exists(STATE_FILE):
        return {"emails": {}}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def is_known(state, message_id):
    return message_id in state["emails"]


def add_email(state, message_id, subject, sender):
    now = datetime.now().isoformat()
    state["emails"][message_id] = {
        "subject":        subject,
        "sender":         sender,
        "received_at":    now,
        "first_notified": now,
        "last_notified":  now,
        "times_notified": 1,
    }


def update_notification(state, message_id):
    state["emails"][message_id]["last_notified"] = datetime.now().isoformat()
    state["emails"][message_id]["times_notified"] += 1


def remove_email(state, message_id):
    if message_id in state["emails"]:
        del state["emails"][message_id]


def hours_since_last_notified(state, message_id):
    last = state["emails"][message_id]["last_notified"]
    delta = datetime.now() - datetime.fromisoformat(last)
    return delta.total_seconds() / 3600


def days_since_received(state, message_id):
    received = state["emails"][message_id]["received_at"]
    delta = datetime.now() - datetime.fromisoformat(received)
    return delta.total_seconds() / 86400