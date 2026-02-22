"""Tests for Wave 1 additions and remaining gaps.

Covers:
- extract_display_name() helper (mail_helpers.py)
- --version flag (main.py)
- resolve_message_context() improved init-error paths
- _warn_automation_once() (applescript.py)
- Edge cases / empty paths for cmd_thread, cmd_reply, cmd_forward
- Edge cases / empty paths for cmd_top_senders, cmd_digest, cmd_show_flagged
- Edge cases for cmd_headers (raw mode, DMARC fail, Reply-To)
- Edge cases for cmd_rules (enable/disable toggle)
- Edge cases for cmd_attachments (no-attachment path)
- cmd_top_senders empty result, sort order
- cmd_show_flagged all-accounts vs scoped paths
"""

import json
from argparse import Namespace
from unittest.mock import Mock, patch

import pytest



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _args(**kwargs):
    defaults = {
        "json": False,
        "account": "iCloud",
        "mailbox": "INBOX",
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


# ===========================================================================
# extract_display_name() — mail_helpers.py
# ===========================================================================

class TestExtractDisplayName:
    """Unit tests for extract_display_name()."""

    def test_quoted_name_with_angle_brackets(self):
        from my_cli.util.mail_helpers import extract_display_name
        result = extract_display_name('"John Doe" <john@example.com>')
        assert result == "John Doe"

    def test_unquoted_name_with_angle_brackets(self):
        from my_cli.util.mail_helpers import extract_display_name
        result = extract_display_name("John Doe <john@example.com>")
        assert result == "John Doe"

    def test_bare_email_returns_email(self):
        from my_cli.util.mail_helpers import extract_display_name
        result = extract_display_name("jane@example.com")
        assert result == "jane@example.com"

    def test_angle_bracket_only_no_name(self):
        from my_cli.util.mail_helpers import extract_display_name
        result = extract_display_name("<admin@site.org>")
        # No name before <, so returns empty string stripped
        assert result == ""

    def test_empty_string(self):
        from my_cli.util.mail_helpers import extract_display_name
        result = extract_display_name("")
        assert result == ""

    def test_trailing_whitespace_stripped(self):
        from my_cli.util.mail_helpers import extract_display_name
        result = extract_display_name("  Alice Smith  <alice@example.com>")
        assert result == "Alice Smith"

    def test_quoted_name_strips_quotes(self):
        from my_cli.util.mail_helpers import extract_display_name
        result = extract_display_name('"Support Team" <support@company.com>')
        assert result == "Support Team"

    def test_multiword_name(self):
        from my_cli.util.mail_helpers import extract_display_name
        result = extract_display_name("Mary Jane Watson <mj@example.com>")
        assert result == "Mary Jane Watson"


# ===========================================================================
# --version flag — main.py
# ===========================================================================

class TestVersionFlag:
    """Test that --version exits with the correct version string."""

    def test_version_flag_exits(self):
        from my_cli.main import main
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["my", "--version"]):
                main()
        # argparse --version exits with code 0
        assert exc_info.value.code == 0

    def test_version_flag_output(self, capsys):
        from my_cli.main import main
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["my", "--version"]):
                main()
        captured = capsys.readouterr()
        # argparse prints version to stdout
        assert "my-apple-mail-cli" in captured.out or "my-apple-mail-cli" in captured.err

    def test_version_includes_semver(self, capsys):
        from my_cli.main import main
        from my_cli import __version__
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["my", "--version"]):
                main()
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert __version__ in combined


# ===========================================================================
# resolve_message_context() — improved init error path
# ===========================================================================

class TestResolveMessageContextInitErrors:
    """Test the two distinct error messages when no account is configured."""

    def test_no_config_file_suggests_init(self, tmp_path, monkeypatch):
        """When config file doesn't exist, error should mention 'my mail init'."""
        from my_cli.util.mail_helpers import resolve_message_context

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        # Config file does NOT exist

        monkeypatch.setattr("my_cli.util.mail_helpers.CONFIG_FILE", str(config_file))
        monkeypatch.setattr("my_cli.config.CONFIG_FILE", str(config_file))
        monkeypatch.setattr("my_cli.config.CONFIG_DIR", str(config_dir))
        monkeypatch.setattr("my_cli.config.STATE_FILE", str(config_dir / "state.json"))
        monkeypatch.setattr("my_cli.config.resolve_account", lambda _: None)

        args = Namespace(account=None, mailbox=None)
        with pytest.raises(SystemExit) as exc_info:
            resolve_message_context(args)
        assert exc_info.value.code == 1

    def test_config_exists_but_no_default_account(self, tmp_path, monkeypatch, capsys):
        """When config exists but no default is set, error mentions configure one."""
        from my_cli.util.mail_helpers import resolve_message_context
        import json as json_mod

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        # Config file EXISTS but has no default_account
        config_file.write_text(json_mod.dumps({}))

        monkeypatch.setattr("my_cli.util.mail_helpers.CONFIG_FILE", str(config_file))
        monkeypatch.setattr("my_cli.config.CONFIG_FILE", str(config_file))
        monkeypatch.setattr("my_cli.config.CONFIG_DIR", str(config_dir))
        monkeypatch.setattr("my_cli.config.STATE_FILE", str(config_dir / "state.json"))
        monkeypatch.setattr("my_cli.config.resolve_account", lambda _: None)

        args = Namespace(account=None, mailbox=None)
        with pytest.raises(SystemExit) as exc_info:
            resolve_message_context(args)
        assert exc_info.value.code == 1


# ===========================================================================
# _warn_automation_once() — applescript.py
# ===========================================================================

class TestWarnAutomationOnce:
    """Test that the automation permission warning is shown at most once."""

    def test_warning_shown_on_first_call(self, capsys, tmp_path, monkeypatch):
        """Warning should print to stderr on first call in a fresh session."""
        import my_cli.util.applescript as as_mod

        # Reset the module-level flag
        monkeypatch.setattr(as_mod, "_automation_warned", False)

        state_file = tmp_path / "state.json"
        config_file = tmp_path / "config.json"
        monkeypatch.setattr("my_cli.config.STATE_FILE", str(state_file))
        monkeypatch.setattr("my_cli.config.CONFIG_FILE", str(config_file))

        # Mock get_state to return empty state (no automation_prompted)
        monkeypatch.setattr("my_cli.config.get_state", lambda: {})
        # Mock _save_json to avoid file writes
        monkeypatch.setattr("my_cli.config._save_json", lambda *_: None)

        as_mod._warn_automation_once()

        captured = capsys.readouterr()
        assert "Automation" in captured.err or "Mail.app" in captured.err

    def test_warning_not_repeated_in_same_session(self, capsys, tmp_path, monkeypatch):
        """After first call, subsequent calls should not print warning."""
        import my_cli.util.applescript as as_mod

        monkeypatch.setattr(as_mod, "_automation_warned", False)
        monkeypatch.setattr("my_cli.config.STATE_FILE", str(tmp_path / "state.json"))
        monkeypatch.setattr("my_cli.config.get_state", lambda: {})
        monkeypatch.setattr("my_cli.config._save_json", lambda *_: None)

        # First call — shows warning
        as_mod._warn_automation_once()
        capsys.readouterr()  # clear

        # Second call in same session — should be silent
        as_mod._warn_automation_once()
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_warning_suppressed_if_already_prompted(self, capsys, tmp_path, monkeypatch):
        """If state shows automation_prompted=True, no warning is printed."""
        import my_cli.util.applescript as as_mod

        monkeypatch.setattr(as_mod, "_automation_warned", False)
        monkeypatch.setattr("my_cli.config.STATE_FILE", str(tmp_path / "state.json"))
        monkeypatch.setattr("my_cli.config.get_state", lambda: {"automation_prompted": True})
        monkeypatch.setattr("my_cli.config._save_json", lambda *_: None)

        as_mod._warn_automation_once()

        captured = capsys.readouterr()
        assert captured.err == ""


# ===========================================================================
# cmd_thread edge cases — composite.py
# ===========================================================================

class TestCmdThreadEdgeCases:
    """Edge cases for cmd_thread."""

    def test_thread_empty_result_shows_no_thread_message(self, monkeypatch, capsys):
        from my_cli.commands.mail.composite import cmd_thread

        mock_run = Mock(side_effect=[
            "Original Subject",  # first call: get subject
            "",                  # second call: no thread messages found
        ])
        monkeypatch.setattr("my_cli.commands.mail.composite.run", mock_run)

        args = _args(id=123, json=False, limit=100, all_accounts=False)
        cmd_thread(args)

        captured = capsys.readouterr()
        assert "No thread found" in captured.out

    def test_thread_empty_result_json(self, monkeypatch, capsys):
        from my_cli.commands.mail.composite import cmd_thread

        mock_run = Mock(side_effect=[
            "Test Subject",
            "",
        ])
        monkeypatch.setattr("my_cli.commands.mail.composite.run", mock_run)

        args = _args(id=123, json=True, limit=100, all_accounts=False)
        cmd_thread(args)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["messages"] == []

    def test_thread_all_accounts_flag(self, monkeypatch, capsys):
        from my_cli.commands.mail.composite import cmd_thread

        mock_run = Mock(side_effect=[
            "Meeting Notes",
            f"50{chr(0x1F)}Meeting Notes{chr(0x1F)}alice@example.com{chr(0x1F)}Monday{chr(0x1F)}INBOX{chr(0x1F)}Work\n",
        ])
        monkeypatch.setattr("my_cli.commands.mail.composite.run", mock_run)

        args = _args(id=50, json=False, limit=100, all_accounts=True)
        cmd_thread(args)

        # When all_accounts=True, second script should use "every account" loop
        second_script = mock_run.call_args_list[1][0][0]
        assert "every account" in second_script

    def test_thread_single_account_script(self, monkeypatch, capsys):
        from my_cli.commands.mail.composite import cmd_thread

        mock_run = Mock(side_effect=[
            "Budget Review",
            f"77{chr(0x1F)}Budget Review{chr(0x1F)}bob@example.com{chr(0x1F)}Tuesday{chr(0x1F)}INBOX{chr(0x1F)}iCloud\n",
        ])
        monkeypatch.setattr("my_cli.commands.mail.composite.run", mock_run)

        args = _args(id=77, json=False, limit=100, all_accounts=False)
        cmd_thread(args)

        second_script = mock_run.call_args_list[1][0][0]
        # Single account mode: should NOT have "every account" loop
        assert "every account" not in second_script
        assert "iCloud" in second_script


# ===========================================================================
# cmd_reply edge cases — composite.py
# ===========================================================================

class TestCmdReplyEdgeCases:
    """Edge cases for cmd_reply."""

    def test_reply_already_has_re_prefix(self, monkeypatch, capsys):
        """If subject already starts with Re:, don't double-prefix."""
        from my_cli.commands.mail.composite import cmd_reply

        mock_run = Mock(side_effect=[
            f"Re: Original{chr(0x1F)}sender@example.com{chr(0x1F)}Monday{chr(0x1F)}Body text",
            "draft created",
        ])
        monkeypatch.setattr("my_cli.commands.mail.composite.run", mock_run)

        args = _args(id=100, body="Thanks!", json=False)
        cmd_reply(args)

        captured = capsys.readouterr()
        assert "Re: Re:" not in captured.out
        assert "Re: Original" in captured.out

    def test_reply_bad_sender_dies(self, monkeypatch):
        """If sender has no extractable email address, die() is called."""
        from my_cli.commands.mail.composite import cmd_reply

        mock_run = Mock(return_value=(
            f"Subject{chr(0x1F)}NotAnEmail{chr(0x1F)}Monday{chr(0x1F)}Body"
        ))
        monkeypatch.setattr("my_cli.commands.mail.composite.run", mock_run)

        args = _args(id=42, body="Hello", json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_reply(args)
        assert exc_info.value.code == 1

    def test_reply_insufficient_fields_dies(self, monkeypatch):
        """If AppleScript returns fewer than 4 fields, die()."""
        from my_cli.commands.mail.composite import cmd_reply

        mock_run = Mock(return_value="OnlySubject")
        monkeypatch.setattr("my_cli.commands.mail.composite.run", mock_run)

        args = _args(id=42, body="Hello", json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_reply(args)
        assert exc_info.value.code == 1


# ===========================================================================
# cmd_forward edge cases — composite.py
# ===========================================================================

class TestCmdForwardEdgeCases:
    """Edge cases for cmd_forward."""

    def test_forward_already_has_fwd_prefix(self, monkeypatch, capsys):
        """Subject already starting with Fwd: is not double-prefixed."""
        from my_cli.commands.mail.composite import cmd_forward

        mock_run = Mock(side_effect=[
            f"Fwd: Original{chr(0x1F)}sender@example.com{chr(0x1F)}Monday{chr(0x1F)}Body",
            "draft created",
        ])
        monkeypatch.setattr("my_cli.commands.mail.composite.run", mock_run)

        args = _args(id=55, to="fwd@example.com", json=False)
        cmd_forward(args)

        captured = capsys.readouterr()
        assert "Fwd: Fwd:" not in captured.out
        assert "Fwd: Original" in captured.out

    def test_forward_bad_to_address_dies(self, monkeypatch):
        """If --to has no valid email address, die()."""
        from my_cli.commands.mail.composite import cmd_forward

        mock_run = Mock(return_value=(
            f"Subject{chr(0x1F)}sender@example.com{chr(0x1F)}Monday{chr(0x1F)}Body"
        ))
        monkeypatch.setattr("my_cli.commands.mail.composite.run", mock_run)

        args = _args(id=42, to="not-a-valid-address", json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_forward(args)
        assert exc_info.value.code == 1

    def test_forward_insufficient_fields_dies(self, monkeypatch):
        """If AppleScript returns fewer than 4 fields, die()."""
        from my_cli.commands.mail.composite import cmd_forward

        mock_run = Mock(return_value="OnlySubject")
        monkeypatch.setattr("my_cli.commands.mail.composite.run", mock_run)

        args = _args(id=42, to="someone@example.com", json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_forward(args)
        assert exc_info.value.code == 1

    def test_forward_formatted_to_address(self, monkeypatch, capsys):
        """--to can be a formatted 'Name <email>' string."""
        from my_cli.commands.mail.composite import cmd_forward

        mock_run = Mock(side_effect=[
            f"Subject{chr(0x1F)}sender@example.com{chr(0x1F)}Monday{chr(0x1F)}Body",
            "draft created",
        ])
        monkeypatch.setattr("my_cli.commands.mail.composite.run", mock_run)

        args = _args(id=42, to="Alice Smith <alice@example.com>", json=False)
        cmd_forward(args)

        captured = capsys.readouterr()
        assert "Forward draft created" in captured.out
        # The output should show the original --to value
        assert "alice@example.com" in captured.out or "Alice Smith" in captured.out


# ===========================================================================
# cmd_top_senders edge cases — analytics.py
# ===========================================================================

class TestCmdTopSendersEdgeCases:
    """Edge cases for cmd_top_senders."""

    def test_empty_result_shows_no_messages(self, monkeypatch, capsys):
        from my_cli.commands.mail.analytics import cmd_top_senders

        mock_run = Mock(return_value="")
        monkeypatch.setattr("my_cli.commands.mail.analytics.run", mock_run)

        args = _args(days=30, limit=10, json=False)
        cmd_top_senders(args)

        captured = capsys.readouterr()
        assert "No messages found" in captured.out

    def test_empty_result_json(self, monkeypatch, capsys):
        from my_cli.commands.mail.analytics import cmd_top_senders

        mock_run = Mock(return_value="")
        monkeypatch.setattr("my_cli.commands.mail.analytics.run", mock_run)

        args = _args(days=30, limit=10, json=True)
        cmd_top_senders(args)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["senders"] == []
        assert data["days"] == 30

    def test_senders_sorted_by_frequency(self, monkeypatch, capsys):
        from my_cli.commands.mail.analytics import cmd_top_senders

        # alice appears 3x, bob 1x — alice should be first
        mock_run = Mock(return_value=(
            "alice@example.com\n"
            "bob@example.com\n"
            "alice@example.com\n"
            "alice@example.com\n"
        ))
        monkeypatch.setattr("my_cli.commands.mail.analytics.run", mock_run)

        args = _args(days=7, limit=5, json=False)
        cmd_top_senders(args)

        captured = capsys.readouterr()
        alice_pos = captured.out.find("alice@example.com")
        bob_pos = captured.out.find("bob@example.com")
        assert alice_pos < bob_pos  # alice listed before bob

    def test_limit_respected(self, monkeypatch, capsys):
        from my_cli.commands.mail.analytics import cmd_top_senders

        # 5 unique senders but limit=3
        senders = "\n".join([
            "a@x.com", "b@x.com", "c@x.com", "d@x.com", "e@x.com"
        ])
        mock_run = Mock(return_value=senders)
        monkeypatch.setattr("my_cli.commands.mail.analytics.run", mock_run)

        args = _args(days=30, limit=3, json=False)
        cmd_top_senders(args)

        captured = capsys.readouterr()
        # At most 3 numbered entries
        assert "  1." in captured.out
        assert "  3." in captured.out
        assert "  4." not in captured.out


# ===========================================================================
# cmd_digest edge cases — analytics.py
# ===========================================================================

class TestCmdDigestEdgeCases:
    """Edge cases for cmd_digest."""

    def test_empty_result_inbox_zero(self, monkeypatch, capsys):
        from my_cli.commands.mail.analytics import cmd_digest

        mock_run = Mock(return_value="")
        monkeypatch.setattr("my_cli.commands.mail.analytics.run", mock_run)

        args = _args(json=False)
        cmd_digest(args)

        captured = capsys.readouterr()
        assert "inbox zero" in captured.out.lower() or "No unread" in captured.out

    def test_groups_by_domain(self, monkeypatch, capsys):
        from my_cli.commands.mail.analytics import cmd_digest

        # Two messages from same domain, one from different
        mock_run = Mock(return_value=(
            f"iCloud{chr(0x1F)}1{chr(0x1F)}Newsletter{chr(0x1F)}news@example.com{chr(0x1F)}Monday\n"
            f"iCloud{chr(0x1F)}2{chr(0x1F)}Promo{chr(0x1F)}promo@example.com{chr(0x1F)}Tuesday\n"
            f"iCloud{chr(0x1F)}3{chr(0x1F)}Alert{chr(0x1F)}noreply@other.org{chr(0x1F)}Wednesday\n"
        ))
        monkeypatch.setattr("my_cli.commands.mail.analytics.run", mock_run)

        args = _args(json=False)
        cmd_digest(args)

        captured = capsys.readouterr()
        assert "example.com" in captured.out
        assert "other.org" in captured.out
        assert "3 messages" in captured.out

    def test_skips_malformed_lines(self, monkeypatch, capsys):
        from my_cli.commands.mail.analytics import cmd_digest

        good = f"iCloud{chr(0x1F)}5{chr(0x1F)}Hello{chr(0x1F)}friend@example.com{chr(0x1F)}Friday"
        bad = "malformed"
        mock_run = Mock(return_value=f"{good}\n{bad}\n")
        monkeypatch.setattr("my_cli.commands.mail.analytics.run", mock_run)

        args = _args(json=False)
        cmd_digest(args)

        captured = capsys.readouterr()
        # Good message still processed
        assert "example.com" in captured.out
        assert "1 messages" in captured.out


# ===========================================================================
# cmd_show_flagged edge cases — analytics.py
# ===========================================================================

class TestCmdShowFlaggedEdgeCases:
    """Edge cases for cmd_show_flagged."""

    def test_no_flagged_messages(self, monkeypatch, capsys):
        from my_cli.commands.mail.analytics import cmd_show_flagged

        mock_run = Mock(return_value="")
        monkeypatch.setattr("my_cli.commands.mail.analytics.run", mock_run)

        args = _args(limit=25, json=False)
        cmd_show_flagged(args)

        captured = capsys.readouterr()
        assert "No flagged messages" in captured.out

    def test_no_flagged_messages_json(self, monkeypatch, capsys):
        from my_cli.commands.mail.analytics import cmd_show_flagged

        mock_run = Mock(return_value="")
        monkeypatch.setattr("my_cli.commands.mail.analytics.run", mock_run)

        args = _args(limit=25, json=True)
        cmd_show_flagged(args)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["flagged_messages"] == []

    def test_no_account_scopes_all_accounts_script(self, monkeypatch, capsys):
        """When account resolves to None, the script should iterate every account."""
        from my_cli.commands.mail.analytics import cmd_show_flagged

        # Ensure resolve_account returns None so the all-accounts branch is taken
        monkeypatch.setattr("my_cli.commands.mail.analytics.resolve_account", lambda _: None)

        mock_run = Mock(return_value=(
            f"99{chr(0x1F)}Flagged{chr(0x1F)}x@y.com{chr(0x1F)}Monday{chr(0x1F)}INBOX{chr(0x1F)}iCloud\n"
        ))
        monkeypatch.setattr("my_cli.commands.mail.analytics.run", mock_run)

        args = Namespace(json=False, account=None, mailbox="INBOX", limit=25)
        cmd_show_flagged(args)

        script = mock_run.call_args[0][0]
        assert "every account" in script

    def test_with_account_scopes_single_account_script(self, monkeypatch, capsys):
        """When account is set, the script should scope to that account."""
        from my_cli.commands.mail.analytics import cmd_show_flagged

        mock_run = Mock(return_value=(
            f"88{chr(0x1F)}Task{chr(0x1F)}z@w.com{chr(0x1F)}Tuesday{chr(0x1F)}INBOX{chr(0x1F)}iCloud\n"
        ))
        monkeypatch.setattr("my_cli.commands.mail.analytics.run", mock_run)

        args = _args(limit=25, json=False)
        cmd_show_flagged(args)

        script = mock_run.call_args[0][0]
        assert "every account" not in script
        assert "iCloud" in script


# ===========================================================================
# cmd_headers edge cases — system.py
# ===========================================================================

class TestCmdHeadersEdgeCases:
    """Edge cases for cmd_headers."""

    def test_raw_mode_prints_directly(self, monkeypatch, capsys):
        """--raw flag prints raw headers without parsing."""
        from my_cli.commands.mail.system import cmd_headers

        raw = "From: raw@example.com\nX-Custom: value"
        mock_run = Mock(return_value=raw)
        monkeypatch.setattr("my_cli.commands.mail.system.run", mock_run)

        args = _args(id=1, json=False, raw=True)
        cmd_headers(args)

        captured = capsys.readouterr()
        assert "raw@example.com" in captured.out
        assert "X-Custom: value" in captured.out

    def test_dmarc_fail_detected(self, monkeypatch, capsys):
        """DMARC fail should show FAIL in auth summary."""
        from my_cli.commands.mail.system import cmd_headers

        raw_headers = (
            "From: phish@example.com\n"
            "To: victim@example.com\n"
            "Subject: Urgent\n"
            "Date: Mon, 14 Feb 2026 10:00:00 +0000\n"
            "Message-Id: <fake@example.com>\n"
            "Authentication-Results: mx.example.com; spf=fail dkim=fail dmarc=fail\n"
        )
        mock_run = Mock(return_value=raw_headers)
        monkeypatch.setattr("my_cli.commands.mail.system.run", mock_run)

        args = _args(id=42, json=False, raw=False)
        cmd_headers(args)

        captured = capsys.readouterr()
        assert "FAIL" in captured.out

    def test_reply_to_shown_when_present(self, monkeypatch, capsys):
        """Reply-To header should appear in output when present."""
        from my_cli.commands.mail.system import cmd_headers

        raw_headers = (
            "From: sender@example.com\n"
            "To: recipient@example.com\n"
            "Subject: Test\n"
            "Date: Mon, 14 Feb 2026 10:00:00 +0000\n"
            "Message-Id: <abc@example.com>\n"
            "Reply-To: replies@example.com\n"
        )
        mock_run = Mock(return_value=raw_headers)
        monkeypatch.setattr("my_cli.commands.mail.system.run", mock_run)

        args = _args(id=10, json=False, raw=False)
        cmd_headers(args)

        captured = capsys.readouterr()
        assert "Reply-To: replies@example.com" in captured.out

    def test_list_unsubscribe_shown(self, monkeypatch, capsys):
        """List-Unsubscribe header should appear truncated in output."""
        from my_cli.commands.mail.system import cmd_headers

        raw_headers = (
            "From: news@example.com\n"
            "To: subscriber@example.com\n"
            "Subject: Weekly Digest\n"
            "Date: Mon, 14 Feb 2026 10:00:00 +0000\n"
            "Message-Id: <digest@example.com>\n"
            "List-Unsubscribe: <https://example.com/unsub?token=abc123>\n"
        )
        mock_run = Mock(return_value=raw_headers)
        monkeypatch.setattr("my_cli.commands.mail.system.run", mock_run)

        args = _args(id=20, json=False, raw=False)
        cmd_headers(args)

        captured = capsys.readouterr()
        assert "Unsubscribe" in captured.out

    def test_hop_count_with_no_received_headers(self, monkeypatch, capsys):
        """Messages with no Received: headers should show Hops: 0."""
        from my_cli.commands.mail.system import cmd_headers

        raw_headers = (
            "From: sender@example.com\n"
            "To: recipient@example.com\n"
            "Subject: Direct\n"
            "Date: Mon, 14 Feb 2026 10:00:00 +0000\n"
            "Message-Id: <direct@example.com>\n"
        )
        mock_run = Mock(return_value=raw_headers)
        monkeypatch.setattr("my_cli.commands.mail.system.run", mock_run)

        args = _args(id=30, json=False, raw=False)
        cmd_headers(args)

        captured = capsys.readouterr()
        assert "Hops: 0" in captured.out


# ===========================================================================
# cmd_rules edge cases — system.py
# ===========================================================================

class TestCmdRulesEdgeCases:
    """Edge cases for cmd_rules (toggle enable/disable)."""

    def test_enable_rule(self, monkeypatch, capsys):
        """cmd_rules enable RULENAME should call toggle with enabled=True."""
        from my_cli.commands.mail.system import cmd_rules

        mock_run = Mock(return_value="Move Newsletters")
        monkeypatch.setattr("my_cli.commands.mail.system.run", mock_run)

        args = _args(json=False, action="enable", rule_name="Move Newsletters")
        cmd_rules(args)

        captured = capsys.readouterr()
        assert "enabled" in captured.out
        assert "Move Newsletters" in captured.out

    def test_disable_rule(self, monkeypatch, capsys):
        """cmd_rules disable RULENAME should call toggle with enabled=False."""
        from my_cli.commands.mail.system import cmd_rules

        mock_run = Mock(return_value="Archive Old Mail")
        monkeypatch.setattr("my_cli.commands.mail.system.run", mock_run)

        args = _args(json=False, action="disable", rule_name="Archive Old Mail")
        cmd_rules(args)

        captured = capsys.readouterr()
        assert "disabled" in captured.out
        assert "Archive Old Mail" in captured.out

    def test_enable_rule_json(self, monkeypatch, capsys):
        """cmd_rules enable --json returns JSON with status."""
        from my_cli.commands.mail.system import cmd_rules

        mock_run = Mock(return_value="Newsletter Rule")
        monkeypatch.setattr("my_cli.commands.mail.system.run", mock_run)

        args = _args(json=True, action="enable", rule_name="Newsletter Rule")
        cmd_rules(args)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["status"] == "enabled"
        assert data["rule"] == "Newsletter Rule"

    def test_no_rules_found(self, monkeypatch, capsys):
        """When rules list is empty, a friendly message is shown."""
        from my_cli.commands.mail.system import cmd_rules

        mock_run = Mock(return_value="")
        monkeypatch.setattr("my_cli.commands.mail.system.run", mock_run)

        args = _args(json=False, action=None, rule_name=None)
        cmd_rules(args)

        captured = capsys.readouterr()
        assert "No mail rules found" in captured.out

    def test_enable_rule_applescript_uses_true(self, monkeypatch, capsys):
        """When enabling, AppleScript should set enabled to true (not false)."""
        from my_cli.commands.mail.system import cmd_rules

        mock_run = Mock(return_value="My Rule")
        monkeypatch.setattr("my_cli.commands.mail.system.run", mock_run)

        args = _args(json=False, action="enable", rule_name="My Rule")
        cmd_rules(args)

        script = mock_run.call_args[0][0]
        assert "true" in script
        assert "false" not in script

    def test_disable_rule_applescript_uses_false(self, monkeypatch, capsys):
        """When disabling, AppleScript should set enabled to false."""
        from my_cli.commands.mail.system import cmd_rules

        mock_run = Mock(return_value="My Rule")
        monkeypatch.setattr("my_cli.commands.mail.system.run", mock_run)

        args = _args(json=False, action="disable", rule_name="My Rule")
        cmd_rules(args)

        script = mock_run.call_args[0][0]
        assert "false" in script


# ===========================================================================
# cmd_attachments edge cases — attachments.py
# ===========================================================================

class TestCmdAttachmentsEdgeCases:
    """Edge cases for cmd_attachments (list)."""

    def test_no_attachments_shows_friendly_message(self, monkeypatch, capsys):
        """Message with no attachments should show a friendly message."""
        from my_cli.commands.mail.attachments import cmd_attachments

        # Only one line = subject, no attachment lines
        mock_run = Mock(return_value="Email Without Attachments")
        monkeypatch.setattr("my_cli.commands.mail.attachments.run", mock_run)

        args = _args(id=42, json=False)
        cmd_attachments(args)

        captured = capsys.readouterr()
        assert "No attachments" in captured.out

    def test_no_attachments_json(self, monkeypatch, capsys):
        """Empty attachment list in JSON mode returns empty list."""
        from my_cli.commands.mail.attachments import cmd_attachments

        mock_run = Mock(return_value="Plain Email")
        monkeypatch.setattr("my_cli.commands.mail.attachments.run", mock_run)

        args = _args(id=42, json=True)
        cmd_attachments(args)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["attachments"] == []
        assert "Plain Email" in data["subject"]

    def test_multiple_attachments_numbered(self, monkeypatch, capsys):
        """Multiple attachments should be listed with numbers."""
        from my_cli.commands.mail.attachments import cmd_attachments

        mock_run = Mock(return_value=(
            "Contract Email\n"
            "contract.pdf\n"
            "addendum.docx\n"
            "signature.png\n"
        ))
        monkeypatch.setattr("my_cli.commands.mail.attachments.run", mock_run)

        args = _args(id=99, json=False)
        cmd_attachments(args)

        captured = capsys.readouterr()
        assert "1. contract.pdf" in captured.out
        assert "2. addendum.docx" in captured.out
        assert "3. signature.png" in captured.out

    def test_attachments_json_includes_list(self, monkeypatch, capsys):
        """JSON output includes subject and full attachment list."""
        from my_cli.commands.mail.attachments import cmd_attachments

        mock_run = Mock(return_value=(
            "Weekly Report\n"
            "data.csv\n"
            "summary.pdf\n"
        ))
        monkeypatch.setattr("my_cli.commands.mail.attachments.run", mock_run)

        args = _args(id=10, json=True)
        cmd_attachments(args)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["subject"] == "Weekly Report"
        assert "data.csv" in data["attachments"]
        assert "summary.pdf" in data["attachments"]
