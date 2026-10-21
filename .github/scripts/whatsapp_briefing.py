#!/usr/bin/env python3
"""Send Hypewire's daily five-story briefing to WhatsApp via CallMeBot.

Needs two repository secrets: CALLMEBOT_PHONE (with country code, e.g. +447700900123)
and CALLMEBOT_APIKEY (sent to you by CallMeBot when you activate it).
If either is missing, it prints a notice and exits cleanly.
"""
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

SITE = "https://rahuloo7.github.io/hypewire/"
phone = os.environ.get("CALLMEBOT_PHONE", "").strip()
key = os.environ.get("CALLMEBOT_APIKEY", "").strip()
if not phone or not key:
    print("CALLMEBOT_PHONE / CALLMEBOT_APIKEY not set; skipping WhatsApp briefing.")
    sys.exit(0)

data = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "hypewire", "stories.json"), encoding="utf-8"))
try:
    day = dt.datetime.fromisoformat(data["refreshedAt"].replace("Z", "+00:00")).strftime("%a %b %-d")
except Exception:
    day = "today"

lines = [f"*Hypewire: today in five* ({day})", ""]
for i, b in enumerate(data.get("briefing", [])[:5], 1):
    lines.append(f"{i}. {b['text']}")
    lines.append(f"{SITE}s/{b['id']}/")
lines += ["", f"Full feed: {SITE}"]
text = "\n".join(lines)

url = "https://api.callmebot.com/whatsapp.php?" + urllib.parse.urlencode(
    {"phone": phone, "text": text, "apikey": key})
with urllib.request.urlopen(url, timeout=60) as r:
    body = r.read().decode("utf-8", "replace")
print("CallMeBot HTTP", r.status)
if r.status != 200 or "ERROR" in body.upper():
    print(body[:500])
    sys.exit(1)
print("Briefing sent.")
