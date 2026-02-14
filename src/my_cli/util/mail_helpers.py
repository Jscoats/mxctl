"""Shared helper functions for mail commands to eliminate code duplication."""

from __future__ import annotations

import re
from argparse import Namespace
from email.utils import parseaddr

from my_cli.config import DEFAULT_MAILBOX, resolve_account
from my_cli.util.applescript import escape
from my_cli.util.formatting import die


def resolve_message_context(args: Namespace) -> tuple[str, str, str, str]:
    """Resolve and escape account/mailbox from args.

    Returns tuple: (account, mailbox, acct_escaped, mb_escaped)
    Dies if account is not set.
    """
    account = resolve_account(getattr(args, "account", None))
    if not account:
        die("Account required. Use -a ACCOUNT.")
    mailbox = getattr(args, "mailbox", None) or DEFAULT_MAILBOX

    acct_escaped = escape(account)
    mb_escaped = escape(mailbox)

    return account, mailbox, acct_escaped, mb_escaped


def parse_email_headers(raw: str) -> dict[str, str | list[str]]:
    """Parse raw email headers into a dict (multi-value keys become lists)."""
    headers: dict[str, str | list[str]] = {}
    current_key: str | None = None
    for line in raw.split("\n"):
        if ": " in line and not line.startswith(" ") and not line.startswith("\t"):
            key, _, val = line.partition(": ")
            current_key = key
            if key in headers:
                if isinstance(headers[key], list):
                    headers[key].append(val)
                else:
                    headers[key] = [headers[key], val]
            else:
                headers[key] = val
        elif current_key and (line.startswith(" ") or line.startswith("\t")):
            if isinstance(headers[current_key], list):
                headers[current_key][-1] += " " + line.strip()
            else:
                headers[current_key] += " " + line.strip()
    return headers


def extract_email(sender_str: str) -> str:
    """Extract email address from sender string.

    Examples:
        "John Doe <john@example.com>" -> "john@example.com"
        "jane@example.com" -> "jane@example.com"
        "<admin@site.org>" -> "admin@site.org"
    """
    _, email = parseaddr(sender_str)
    return email if email else sender_str


def normalize_subject(subject: str) -> str:
    """Normalize email subject by removing Re:/Fwd:/Fw:/AW:/SV:/VS: prefixes.

    Handles international reply prefixes:
    - Re: (English/most languages)
    - Fwd/Fw: (English forward)
    - AW: (German - Antwort)
    - SV: (Swedish/Norwegian - Svar)
    - VS: (Finnish - Vastaus)

    Handles multiple nested prefixes like "Re: Re: Fwd: Original Subject".
    """
    # Loop to handle multiple nested prefixes
    while True:
        normalized = re.sub(r'^(Re|Fwd|Fw|AW|SV|VS):\s*', '', subject, flags=re.IGNORECASE).strip()
        if normalized == subject:
            break
        subject = normalized
    return subject
