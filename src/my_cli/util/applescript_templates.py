"""Reusable AppleScript template functions to reduce duplication.

Common patterns extracted from command modules:
1. Inbox iteration across all accounts
2. Message iteration with cap/limit
3. Single message lookup by ID
4. Field output assembly with separators

Each template function returns a complete AppleScript string.
Use FIELD_SEPARATOR from config.py in the templates.
"""

from my_cli.config import FIELD_SEPARATOR


def inbox_iterator_all_accounts(inner_operations: str, cap: int = 20, account: str | None = None) -> str:
    """Generate AppleScript to iterate over INBOX in all enabled accounts (or one).

    Args:
        inner_operations: AppleScript code to execute for each INBOX message.
                         Available variables: m (message), acct (account),
                         acctName (account name), mbox (INBOX mailbox)
        cap: Maximum number of messages per inbox
        account: If provided, scope iteration to this single account name

    Returns:
        Complete AppleScript string

    Example:
        inner_ops = '''
            set output to output & acctName & "\\x1F" & (id of m) & "\\x1F" & (subject of m) & linefeed
        '''
        script = inbox_iterator_all_accounts(inner_ops, cap=30)
        script = inbox_iterator_all_accounts(inner_ops, cap=30, account="iCloud")
    """
    if account:
        from my_cli.util.applescript import escape
        acct_escaped = escape(account)
        outer_open = f'set acct to account "{acct_escaped}"\n        set acctName to name of acct'
        outer_close = ""
    else:
        outer_open = (
            "repeat with acct in (every account)\n"
            "            if enabled of acct then\n"
            "                set acctName to name of acct"
        )
        outer_close = "            end if\n        end repeat"

    return f"""
    tell application "Mail"
        set output to ""
        set totalFound to 0
        {outer_open}
            repeat with mbox in (mailboxes of acct)
                if name of mbox is "INBOX" then
                    try
                        set unreadMsgs to (every message of mbox whose read status is false)
                        set cap to {cap}
                        if (count of unreadMsgs) < cap then set cap to (count of unreadMsgs)
                        repeat with j from 1 to cap
                            set m to item j of unreadMsgs
                            {inner_operations}
                            set totalFound to totalFound + 1
                        end repeat
                    end try
                    exit repeat
                end if
            end repeat
        {outer_close}
        return output
    end tell
    """


def message_iterator_with_limit(
    account_var: str,
    mailbox_var: str,
    limit: int,
    whose_clause: str = "",
    fields: list[str] | None = None
) -> str:
    """Generate AppleScript to iterate messages with a cap.

    Args:
        account_var: Variable name or escaped account name (e.g., 'acct' or '"iCloud"')
        mailbox_var: Variable name or escaped mailbox name (e.g., 'mb' or '"INBOX"')
        limit: Maximum number of messages to process
        whose_clause: Optional filter (e.g., 'whose read status is false')
        fields: List of message fields to extract (e.g., ['id', 'subject', 'sender'])
                If None, returns full message iteration without field assembly

    Returns:
        Complete AppleScript string

    Example:
        script = message_iterator_with_limit(
            'acct', 'mb', 25,
            whose_clause='whose read status is false',
            fields=['id', 'subject', 'sender', 'date received']
        )
    """
    if fields:
        field_assembly = f' & "{FIELD_SEPARATOR}" & '.join(f"({field} of m)" for field in fields)
        inner_loop = f"""
                set output to output & {field_assembly} & linefeed"""
    else:
        inner_loop = ""

    whose_part = f" {whose_clause}" if whose_clause else ""

    return f"""
    tell application "Mail"
        set mb to mailbox {mailbox_var} of account {account_var}
        set allMsgs to (every message of mb{whose_part})
        set msgCount to count of allMsgs
        set actualLimit to {limit}
        if msgCount < actualLimit then set actualLimit to msgCount
        if actualLimit = 0 then return ""
        set output to ""{inner_loop}
        repeat with i from 1 to actualLimit
            set m to item i of allMsgs
            set output to output & {field_assembly} & linefeed
        end repeat
        return output
    end tell
    """


def single_message_lookup(
    account_var: str,
    mailbox_var: str,
    message_id: int,
    fields: list[str] | None = None,
    return_expression: str | None = None
) -> str:
    """Generate AppleScript to fetch a single message by ID.

    Args:
        account_var: Variable name or escaped account name
        mailbox_var: Variable name or escaped mailbox name
        message_id: Message ID to lookup
        fields: List of message fields to extract (returns field-separated output)
        return_expression: Custom return expression (overrides fields)

    Returns:
        Complete AppleScript string

    Example:
        # Simple field extraction
        script = single_message_lookup(
            '"iCloud"', '"INBOX"', 12345,
            fields=['subject', 'sender', 'date received']
        )

        # Custom return expression
        script = single_message_lookup(
            '"iCloud"', '"INBOX"', 12345,
            return_expression='subject of theMsg'
        )
    """
    if return_expression:
        return_stmt = f"return {return_expression}"
    elif fields:
        field_parts = f' & "{FIELD_SEPARATOR}" & '.join(f"({field} of theMsg)" for field in fields)
        return_stmt = f"return {field_parts}"
    else:
        return_stmt = "return theMsg"

    return f"""
    tell application "Mail"
        set mb to mailbox {mailbox_var} of account {account_var}
        set theMsg to first message of mb whose id is {message_id}
        {return_stmt}
    end tell
    """


def account_iterator(
    mailbox_filter: str | None = None,
    limit: int | None = None,
    inner_operations: str = ""
) -> str:
    """Generate AppleScript to iterate over all accounts.

    Args:
        mailbox_filter: Optional mailbox name to filter (e.g., 'INBOX')
        limit: Optional total message limit across all accounts
        inner_operations: AppleScript code to execute for each account/mailbox
                         Available variables: acct, acctName, mbox (if mailbox_filter set)

    Returns:
        Complete AppleScript string

    Example:
        # Iterate all accounts, INBOX only
        ops = '''
            set unreadCount to unread count of mbox
            set output to output & acctName & "\\x1F" & unreadCount & linefeed
        '''
        script = account_iterator(mailbox_filter='INBOX', inner_operations=ops)
    """
    limit_check = f"if totalFound >= {limit} then exit repeat\n            " if limit else ""

    if mailbox_filter:
        mbox_loop = f"""
            repeat with mbox in (mailboxes of acct)
                if name of mbox is "{mailbox_filter}" then
                    {limit_check}{inner_operations}
                    exit repeat
                end if
            end repeat"""
    else:
        mbox_loop = f"""
            repeat with mbox in (mailboxes of acct)
                {limit_check}{inner_operations}
            end repeat"""

    return f"""
    tell application "Mail"
        set output to ""
        set totalFound to 0
        repeat with acct in (every account)
            set acctName to name of acct
            {mbox_loop}
        end repeat
        return output
    end tell
    """


def set_message_property(
    account_var: str,
    mailbox_var: str,
    message_id: int,
    property_name: str,
    property_value: str
) -> str:
    """Generate AppleScript to set a message property and return subject.

    Args:
        account_var: Variable name or escaped account name
        mailbox_var: Variable name or escaped mailbox name
        message_id: Message ID
        property_name: Property to set (e.g., 'read status', 'flagged status')
        property_value: Value to set (e.g., 'true', 'false')

    Returns:
        Complete AppleScript string

    Example:
        script = set_message_property(
            '"iCloud"', '"INBOX"', 12345,
            'read status', 'true'
        )
    """
    return f"""
    tell application "Mail"
        set mb to mailbox {mailbox_var} of account {account_var}
        set theMsg to first message of mb whose id is {message_id}
        set {property_name} of theMsg to {property_value}
        return subject of theMsg
    end tell
    """


def list_attachments(
    account_var: str,
    mailbox_var: str,
    message_id: int
) -> str:
    """Generate AppleScript to list message attachments.

    Args:
        account_var: Variable name or escaped account name
        mailbox_var: Variable name or escaped mailbox name
        message_id: Message ID

    Returns:
        Complete AppleScript string (subject on first line, attachments below)

    Example:
        script = list_attachments('"iCloud"', '"INBOX"', 12345)
    """
    return f"""
    tell application "Mail"
        set mb to mailbox {mailbox_var} of account {account_var}
        set theMsg to first message of mb whose id is {message_id}
        set msgSubject to subject of theMsg
        set output to msgSubject & linefeed
        repeat with att in (mail attachments of theMsg)
            set attName to name of att
            set output to output & attName & linefeed
        end repeat
        return output
    end tell
    """
