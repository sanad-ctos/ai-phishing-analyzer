#!/usr/bin/env python3
"""
AI Phishing Email Analyzer
---------------------------
Feeds a raw .eml email to a LOCAL AI model (via Ollama) and gets back an
automated SOC-analyst verdict: phishing or not, the red flags, extracted IOCs,
and MITRE ATT&CK mapping — in seconds, with nothing sent to the cloud.

Usage:
    python3 analyze.py phishing_sample.eml

Requires: Ollama running locally with a model pulled (see the project guide).
"""

import sys
import json
import email
from email import policy
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"   # change to whatever model you pulled (e.g. "llama3.1")


def read_email(path):
    """Parse an .eml file into readable headers + body text."""
    with open(path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    headers = {
        "From": msg.get("From", ""),
        "Reply-To": msg.get("Reply-To", ""),
        "To": msg.get("To", ""),
        "Subject": msg.get("Subject", ""),
        "Date": msg.get("Date", ""),
        "Return-Path": msg.get("Return-Path", ""),
        "Authentication-Results": msg.get("Authentication-Results", ""),
    }

    # get the plain-text body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body += part.get_content()
    else:
        body = msg.get_content()

    header_text = "\n".join(f"{k}: {v}" for k, v in headers.items() if v)
    return header_text, body


def build_prompt(header_text, body):
    """The SOC-analyst instruction we give the AI model."""
    return f"""You are a Tier 1 SOC analyst. Analyze the following email that was reported as suspicious.
Decide whether it is PHISHING or BENIGN, and explain your reasoning like an analyst writing a ticket.

Respond in EXACTLY this format:

VERDICT: <Phishing or Benign>
CONFIDENCE: <Low / Medium / High>

RED FLAGS:
- <each suspicious indicator you found, one per line>

INDICATORS OF COMPROMISE (IOCs):
- <domains, IPs, URLs, sender addresses, attachment names you found>

MITRE ATT&CK:
- <relevant technique IDs and names, e.g. T1566.001 Spearphishing Attachment>

RECOMMENDED ACTION:
- <what the SOC should do next>

--- EMAIL HEADERS ---
{header_text}

--- EMAIL BODY ---
{body}
"""


def ask_ai(prompt):
    """Send the prompt to the local Ollama model and return its answer."""
    data = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result.get("response", "").strip()


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 analyze.py <email.eml>")
        sys.exit(1)

    path = sys.argv[1]
    print(f"[*] Reading email: {path}")
    header_text, body = read_email(path)

    print(f"[*] Sending to local AI model ({MODEL}) via Ollama...")
    print("[*] (running fully offline — nothing leaves your machine)\n")
    prompt = build_prompt(header_text, body)
    answer = ask_ai(prompt)

    print("=" * 60)
    print("   AI PHISHING ANALYSIS REPORT")
    print("=" * 60)
    print(answer)
    print("=" * 60)


if __name__ == "__main__":
    main()
