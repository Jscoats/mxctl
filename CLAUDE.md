# my-cli

Personal CLI toolkit. Binary: `my`. Installed via `uv tool install -e .`

## Architecture

```
src/my_cli/
├── main.py            # Top-level argparse router
├── config.py          # Constants, FIELD_SEPARATOR, account resolution
├── util/
│   ├── applescript.py          # run(), escape(), sanitize_path()
│   ├── applescript_templates.py # Reusable AppleScript patterns (inbox iteration, message lookup, etc.)
│   ├── formatting.py           # format_output(), truncate(), die()
│   ├── mail_helpers.py         # resolve_message_context(), normalize_subject(), extract_email()
│   └── dates.py                # parse_date(), to_applescript_date()
└── commands/
    └── mail/          # All mail subcommands
        ├── accounts.py            # inbox, accounts, mailboxes
        ├── messages.py            # list, read, search
        ├── actions.py             # mark-read, mark-unread, flag, unflag, move, delete, unsubscribe
        ├── compose.py             # draft (supports --template)
        ├── attachments.py         # attachments, save-attachment
        ├── manage.py              # create-mailbox, delete-mailbox
        ├── batch.py               # batch-read, batch-flag, batch-move, batch-delete
        ├── analytics.py           # stats (--all), top-senders, digest, show-flagged
        ├── system.py              # check, headers, rules, signatures, junk, not-junk
        ├── composite.py           # export, thread, reply, forward
        ├── ai.py                  # summary, triage, context, find-related
        ├── templates.py           # templates list/create/show/delete
        ├── todoist_integration.py # to-todoist
        ├── inbox_tools.py         # process-inbox, clean-newsletters, weekly-review
        └── undo.py                # undo, undo --list (batch operation rollback)
```

## Key Patterns

- **Zero runtime dependencies** — stdlib only (argparse, subprocess, json, etc.)
- **AppleScript bridge** — all Mail.app interaction via `osascript -e` through `util/applescript.py`
- **`FIELD_SEPARATOR` / `RECORD_SEPARATOR`** — AppleScript returns multi-field data separated by ASCII Unit Separator; constants in `config.py`
- **`format_output(args, text, json_data=...)`** — centralized output handler; checks `getattr(args, "json", False)` internally
- **`resolve_message_context(args)`** — shared account/mailbox resolution + escaping (in `util/mail_helpers.py`)
- **`--json` flag** — every command supports structured JSON output
- **Three-tier account resolution** — explicit `-a` > `~/.config/my/config.json` default > last-used in state.json
- **Default mailbox** — `INBOX` when `-m` is omitted
- **Constants in `config.py`** — `APPLESCRIPT_TIMEOUT_*`, `MAX_MESSAGES_BATCH`, `DEFAULT_*` limits

## Adding a New Command

1. Add handler function in the appropriate module under `commands/mail/`
2. Add argparse registration in that module's `register()` function
3. The `__init__.py` router auto-wires all registered modules

## Adding a New Top-Level Subcommand (e.g., `my cal`)

1. Create `commands/cal/` with `__init__.py` that exports `register_cal_subcommand()`
2. Import and call it in `main.py`

## Development

```bash
uv tool install -e .          # Install (editable)
uv tool install -e . --force  # Reinstall after changes
my mail --help                # Verify
```

## Gotchas

- AppleScript operations on large mailboxes can timeout (30s default). Cap iterations.
- The `repeat with m in (list)` pattern in AppleScript is O(n^2). Use indexed `repeat with i from 1 to cap` with explicit caps for any unconstrained query.
- `sender` field in AppleScript often includes display name + email: `"Name" <email@example.com>`
- macOS uv-installed Python lacks CA certs. Use `ssl.create_default_context(cafile="/etc/ssl/cert.pem")` for HTTPS requests.
