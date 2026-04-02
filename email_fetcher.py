import imaplib
import email
from datetime import datetime, timedelta


def connect(email_address, password):
    """Connect and log in to Gmail via IMAP."""
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(email_address, password)
    return mail


def _parse_email(mail, email_id):

    status, data = mail.fetch(email_id, "(RFC822)")
    if status != "OK":
        return None
    
    msg = email.message_from_bytes(data[0][1])

    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="ignore")

    return {
        "subject": msg.get("Subject", "(no subject)"),
        "sender": msg.get("From", ""),
        "to": msg.get("To", ""),
        "message_id": msg.get("Message-ID", "").strip(),
        "in_reply_to": msg.get("In-Reply-To", "").strip(),
        "date": msg.get("Date", ""),
        "body": body[:1500],
    }

def _you_replied(mail, message_id, your_email):
    """Check if you replied to a given email by searching Sent folder."""
    mail.select('"[Gmail]/Sent Mail"')
    status, results = mail.search(None, f'HEADER In-Reply-To "{message_id}"')
    replied = status == "OK" and bool(results[0])
    mail.select("INBOX")
    return replied

def _fetch_inbox_ids(mail, search_criteria):
    """Select inbox and return email IDs matching a search criteria string."""
    mail.select("INBOX")
    status, messages = mail.search(None, search_criteria)
    if status != "OK" or not messages[0]:
        return []
    return messages[0].split()



def fetch_since(mail, since_date, your_email):
    """
    Catch-up mode — fetch inbox emails received since a given datetime.
    Filters out emails you've already replied to.
    Returns a list of parsed email dicts.
    """
    date_str = since_date.strftime("%d-%b-%Y")
    ids = _fetch_inbox_ids(mail, f'SINCE "{date_str}"')
 
    results = []
    for eid in ids:
        parsed = _parse_email(mail, eid)
        if not parsed:
            continue
        if not parsed["message_id"]:
            continue
        # Skip emails sent by yourself
        if your_email.lower() in parsed["sender"].lower():
            continue
        # Skip if you already replied
        if _you_replied(mail, parsed["message_id"], your_email):
            continue
        results.append(parsed)
 
    return results

def fetch_last_minute(mail, your_email):
    """
    Live mode — fetch inbox emails received in the last 60 seconds.
    Filters out emails you sent yourself.
    Returns a list of parsed email dicts.
    """
    # IMAP SINCE is date-only so we fetch today and filter by time ourselves
    today_str = datetime.now().strftime("%d-%b-%Y")
    ids = _fetch_inbox_ids(mail, f'SINCE "{today_str}"')
 
    cutoff = datetime.now() - timedelta(seconds=60)
    results = []
 
    for eid in ids:
        parsed = _parse_email(mail, eid)
        if not parsed:
            continue
        if not parsed["message_id"]:
            continue
        if your_email.lower() in parsed["sender"].lower():
            continue
 
        # Parse the email date and filter to last 60 seconds
        try:
            from email.utils import parsedate_to_datetime
            email_dt = parsedate_to_datetime(parsed["date"])
            # Make cutoff timezone-aware if email_dt is aware
            if email_dt.tzinfo is not None:
                import pytz
                cutoff_aware = cutoff.replace(tzinfo=pytz.UTC)
                if email_dt < cutoff_aware:
                    continue
            else:
                if email_dt < cutoff:
                    continue
        except Exception:
            continue
 
        results.append(parsed)
 
    return results