# ReplyRadar

A lightweight Windows background agent that watches your Gmail inbox and reminds you when an email needs a reply. It uses an LLM to decide whether each email actually requires a response, so you only get notified when it matters. Set it up once and it runs forever, automatically, every time you log into your PC.

---

## How the System Works

ReplyRadar has two parts: a setup app and a background agent.

The setup app is what you run once. You fill in your credentials and preferences, click Inject, and it handles everything else. It copies the background agent into your AppData folder, writes your config, registers a Windows Task Scheduler task so the agent launches on every login, and immediately starts the agent. After that you can delete the setup app. It has done its job.

The background agent is what actually does the work. It runs silently with no window, no tray icon, nothing. Here is exactly what happens every minute:

**Email fetching**

Every run, the agent calculates a fetch window. It looks back as far as your configured threshold (default 3 days) but never before the day before you first set it up. So if your threshold is 3 days and your PC was off for a week, it still only looks at the last 3 days. It never digs further back than that no matter what.

**LLM classification**

Every fetched email that the agent has not seen before gets sent to Groq, which runs a LLaMA model, with a single question: does this email require a response? The model looks at the subject, sender, and body and returns a yes or no with a reason. Automated emails, newsletters, job alerts, security notifications and anything that does not expect a human reply back get filtered out. Only emails where a real human is waiting on you get flagged.

**State tracking**

When an email is flagged as needing a reply, it gets saved to a local `state.json` file in your AppData folder. This file persists across restarts so the agent always knows what it is tracking. If you send a reply, the agent checks your Sent folder and removes that email from state automatically.

**Notifications**

Two types of notifications are sent:

**Reply Needed** fires the first time a new email is flagged. It tells you the subject and who it is from.

**Reminder** fires every N hours (whatever you configured) if you still have not replied. It tells you the subject, who it is from, and which reminder number this is so you know how long it has been sitting there.

Once an email is older than your configured day threshold it gets dropped from state and you stop getting reminders for it.

**On restart**

Because the Task Scheduler task runs the agent on every login, the agent picks up exactly where it left off. The state file still has all the emails it was tracking. The fetch window is always computed fresh from your config. Nothing resets, nothing is lost.

---

## What You Need Before Running This

**A Gmail app password**

Google does not allow third party apps to log in with your regular password. You need to generate an app password.

1. Go to myaccount.google.com
2. Go to Security and make sure 2 Step Verification is turned on
3. Search for App Passwords in the search bar
4. Create a new one, name it anything, and copy the 16 character password it gives you

That is what goes in the Gmail app password field.

**A Groq API key**

Groq runs the LLM that classifies your emails. It is free to sign up.

1. Go to console.groq.com and create a free account
2. Go to API Keys and generate a new key
3. Copy it

That is what goes in the Groq API key field.

---

## Installation

Download `setup.exe` from the `dist` folder in this repository. That is the only file you need. Nothing else to install, no Python required, no dependencies to manage.

Double click `setup.exe`. If Windows shows a security warning click More info and then Run anyway. This happens because the exe is unsigned.

Fill in the following:

- **Gmail address** — your full Gmail address
- **Gmail app password** — the 16 character password from the steps above, not your regular Gmail password
- **Groq API key** — from console.groq.com
- **Stop reminding after N days** — how many days before the agent gives up on an unanswered email (default 3)
- **Remind every N hours** — how often you get re-notified about an email you have not replied to (default 8)
- **New email notifications** — toggle this off if you only want reminders and not notifications for brand new emails

Click Inject. The agent starts immediately. You can close or delete the setup app.

---

## Removing It

Open `setup.exe` again. It will detect that an agent is already running and disable the Inject button. Click Remove. It will kill the agent, delete everything from AppData, and remove the scheduled task. Clean uninstall, nothing left behind.

---

## Logs

The agent logs everything it does to:

```
C:\Users\YourName\AppData\Roaming\EmailAgent\agent.log
```

You can watch it live in PowerShell:

```powershell
Get-Content "$env:APPDATA\EmailAgent\agent.log" -Wait
```

Every email it fetches gets logged with whether it needs a response and why. If something is not working this is the first place to look.

---

## Project Structure

```
ReplyRadar/
    agent.py            Main loop, scheduling, and orchestration
    email_fetcher.py    IMAP connection and email retrieval
    groq_analyzer.py    Sends emails to Groq LLM for classification
    notifier.py         Windows toast notifications via plyer
    state.py            Reads and writes state.json to track emails
    setup_app.py        CustomTkinter GUI installer
    dist/
        setup.exe       The only file end users need
```

---

## Built With

- Python
- CustomTkinter for the setup GUI
- imaplib for Gmail IMAP access
- Groq API with LLaMA for email classification
- plyer for Windows toast notifications
- schedule for the run loop
- PyInstaller to compile everything into a single distributable exe
