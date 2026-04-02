import os

import logging
from pathlib import Path



import time
import schedule
from datetime import datetime

import json
import state
import email_fetcher
import groq_analyzer
import notifier
from datetime import timedelta


def process_emails(emails, cfg, st, mail, silent=False):
    to_notify = []

    for em in emails:
        mid = em["message_id"]
        if not mid:
            continue
        if state.is_known(st, mid):
            continue

        needs, reason = groq_analyzer.needs_response(em, cfg["groq_api_key"])
        logging.info(f"  [{em['subject'][:40]}] needs_response={needs} — {reason}")

        if needs:
            state.add_email(st, mid, em["subject"], em["sender"])
            if not silent:  # ← don't notify during catch-up
                to_notify.append({
                    "subject":        em["subject"],
                    "sender":         em["sender"],
                    "times_notified": 1,
                    "reason":         reason,
                })

    return to_notify


def reminder_loop(cfg, st):
    """
    Check all tracked emails:
    - If older than days_threshold → remove from state
    - If hours since last notification >= hours_interval → remind again
    Returns list of emails to re-notify.
    """
    days_threshold  = cfg["followup_reminders"]["days_threshold"]
    hours_interval  = cfg["followup_reminders"]["hours_intervals"]
    to_notify       = []

    for mid in list(st["emails"].keys()):
        days_old = state.days_since_received(st, mid)
        if days_old > days_threshold:
            logging.info(f"  Dropping {mid[:30]}... (older than {days_threshold} days)")
            state.remove_email(st, mid)
            continue

        hours_since = state.hours_since_last_notified(st, mid)
        if hours_since >= hours_interval:
            entry = st["emails"][mid]
            state.update_notification(st, mid)
            to_notify.append({
                "subject":        entry["subject"],
                "sender":         entry["sender"],
                "times_notified": entry["times_notified"],
                "reason":         "Still waiting for your response.",
            })

    return to_notify


def run(cfg, st, mail):
    logging.info(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running...")

    days_threshold = cfg["followup_reminders"]["days_threshold"]
    start_date = datetime.fromisoformat(cfg["start_date"]) - timedelta(days=1)
    earliest_allowed = datetime.now() - timedelta(days=days_threshold)

    # Never look before start_date - 1, never look beyond threshold
    fetch_since = max(start_date, earliest_allowed)

    emails = email_fetcher.fetch_since(mail, fetch_since, cfg["EMAIL"])
    logging.info(f"  Fetched {len(emails)} email(s) since {fetch_since.strftime('%Y-%m-%d %H:%M')}")

    new_email_notif_enabled = cfg.get("new_email_notifications", {}).get("enabled", True)
    new_notifications = process_emails(
        emails, cfg, st, mail,
        silent=not new_email_notif_enabled
    )

    reminder_notifications = []
    if cfg["followup_reminders"]["enabled"]:
        reminder_notifications = reminder_loop(cfg, st)

    state.save(st)

    all_notifications = new_notifications + reminder_notifications
    if all_notifications:
        notifier.send_notification(all_notifications)
    else:
        logging.info("  Nothing to notify.")


def main():
    log_file = Path(os.environ.get("APPDATA", "")) / "EmailAgent" / "agent.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )


    with open("config.json", "r") as f:
        cfg = json.load(f)
    st = state.load()

    logging.info("Email Response Agent starting...")
    mail = email_fetcher.connect(cfg["EMAIL"], cfg["PASSWORD"])
    logging.info("  Connected to Gmail via IMAP")

    run(cfg, st, mail)

    #  run every minute 
    schedule.every(1).minutes.do(run, cfg=cfg, st=st, mail=mail)

    logging.info(f"\nRunning every minute. Press Ctrl+C to stop.\n")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()