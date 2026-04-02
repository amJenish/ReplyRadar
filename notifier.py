import logging
from datetime import datetime
from plyer import notification


def send_notification(emails_to_notify):
    if not emails_to_notify:
        return

    for em in emails_to_notify:
        is_reminder = em["times_notified"] > 1

        title = (
            f"Reminder: {em['subject'][:50]}"
            if is_reminder
            else f"Reply Needed: {em['subject'][:50]}"
        )

        message = (
            f"From: {em['sender']}\nYou haven't replied yet (reminder #{em['times_notified']})"
            if is_reminder
            else f"From: {em['sender']}\n{em['reason']}"
        )

        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Email Response Agent",
                timeout=8,
            )
            logging.info(f"  Notified: {em['subject'][:40]}")
        except Exception as e:
            logging.error(f"  Notification failed: {e}")

    logging.info(f"[{datetime.now().strftime('%H:%M:%S')}] Notified — {len(emails_to_notify)} email(s)")