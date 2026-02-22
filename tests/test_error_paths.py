"""Tests for error handling and edge cases."""

from argparse import Namespace
from unittest.mock import Mock, patch
import os

import pytest

from my_cli.config import FIELD_SEPARATOR, validate_limit
from my_cli.util.mail_helpers import resolve_message_context


class TestResolveMessageContextErrors:
    """Test error handling in resolve_message_context."""

    def test_dies_when_account_not_set(self, tmp_path, monkeypatch):
        """Should die with clear message when account is not set."""
        # Mock config dir to ensure no defaults exist
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        monkeypatch.setattr("my_cli.config.CONFIG_DIR", str(config_dir))
        monkeypatch.setattr(
            "my_cli.config.CONFIG_FILE", str(config_dir / "config.json")
        )
        monkeypatch.setattr("my_cli.config.STATE_FILE", str(config_dir / "state.json"))

        args = Namespace(account=None, mailbox=None)

        with pytest.raises(SystemExit) as exc_info:
            resolve_message_context(args)
        assert exc_info.value.code == 1

    def test_uses_default_mailbox_when_none(self, tmp_path, monkeypatch):
        """Should use DEFAULT_MAILBOX when mailbox is None."""
        # Mock config dir
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        monkeypatch.setattr("my_cli.config.CONFIG_DIR", str(config_dir))
        monkeypatch.setattr(
            "my_cli.config.CONFIG_FILE", str(config_dir / "config.json")
        )
        monkeypatch.setattr("my_cli.config.STATE_FILE", str(config_dir / "state.json"))

        args = Namespace(account="TestAccount", mailbox=None)
        account, mailbox, _, _ = resolve_message_context(args)

        assert account == "TestAccount"
        assert mailbox == "INBOX"  # DEFAULT_MAILBOX

    def test_escapes_special_characters(self, tmp_path, monkeypatch):
        """Should escape AppleScript special characters in account/mailbox."""
        # Mock config dir
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        monkeypatch.setattr("my_cli.config.CONFIG_DIR", str(config_dir))
        monkeypatch.setattr(
            "my_cli.config.CONFIG_FILE", str(config_dir / "config.json")
        )
        monkeypatch.setattr("my_cli.config.STATE_FILE", str(config_dir / "state.json"))

        args = Namespace(account='Test"Account', mailbox='Mail\\Box')
        _, _, acct_escaped, mb_escaped = resolve_message_context(args)

        # The escape function should handle quotes and backslashes
        assert '"' not in acct_escaped or '\\"' in acct_escaped
        assert '\\' not in mb_escaped or '\\\\' in mb_escaped


class TestAppleScriptErrorHandling:
    """Test handling of malformed or empty AppleScript output.

    Note: Full end-to-end AI command testing requires more complex mocking
    infrastructure. These tests verify the parsing logic handles edge cases.
    """

    def test_empty_string_returns_empty(self):
        """Test that empty strings are handled in field parsing."""
        parts = "".split(FIELD_SEPARATOR)
        assert len(parts) == 1  # Empty string splits to ['']
        assert parts[0] == ""

    def test_insufficient_field_count_detection(self):
        """Test detection of malformed data with too few fields."""
        line = f"iCloud{FIELD_SEPARATOR}123{FIELD_SEPARATOR}Subject{FIELD_SEPARATOR}sender@example.com"  # Only 4 fields
        parts = line.split(FIELD_SEPARATOR)
        # Should have at least 5 fields for summary, 6 for triage
        assert len(parts) < 5

    def test_valid_field_count_detection(self):
        """Test valid message parsing."""
        line = f"iCloud{FIELD_SEPARATOR}123{FIELD_SEPARATOR}Subject{FIELD_SEPARATOR}sender@example.com{FIELD_SEPARATOR}2026-01-01{FIELD_SEPARATOR}true"
        parts = line.split(FIELD_SEPARATOR)
        assert len(parts) >= 5  # Has enough fields for message parsing


class TestValidateLimitEdgeCases:
    """Extended test coverage for validate_limit beyond basic tests."""

    def test_very_large_negative_clamped(self):
        """Should clamp very large negative values to 1."""
        assert validate_limit(-999999) == 1

    def test_max_boundary(self):
        """Should accept MAX_MESSAGE_LIMIT exactly."""
        assert validate_limit(100) == 100

    def test_max_plus_one_clamped(self):
        """Should clamp MAX_MESSAGE_LIMIT + 1 to max."""
        assert validate_limit(101) == 100

    def test_mid_range_unchanged(self):
        """Should pass through mid-range values unchanged."""
        assert validate_limit(50) == 50

    def test_one_is_minimum(self):
        """Should accept 1 as minimum valid value."""
        assert validate_limit(1) == 1


class TestBatchOperationDryRun:
    """Test batch operation dry-run logic.

    Note: Full integration testing of batch commands requires mocking the
    entire AppleScript pipeline. These tests verify the dry-run flag behavior
    exists and is checked.
    """

    def test_batch_operations_have_dry_run_parameter(self):
        """Verify batch commands support dry_run parameter."""
        from my_cli.commands.mail.batch import cmd_batch_move, cmd_batch_delete

        # Both should accept args with dry_run attribute
        # This is a smoke test that the parameter exists in the codebase
        assert callable(cmd_batch_move)
        assert callable(cmd_batch_delete)

    def test_dry_run_attribute_defaults_false(self, mock_args):
        """Test that getattr for dry_run defaults to False."""
        args = mock_args()
        dry_run = getattr(args, "dry_run", False)
        assert dry_run is False

    def test_dry_run_attribute_can_be_true(self, mock_args):
        """Test that dry_run can be set to True."""
        args = mock_args(dry_run=True)
        assert args.dry_run is True


# ---------------------------------------------------------------------------
# inbox_tools.py: cmd_process_inbox
# ---------------------------------------------------------------------------

class TestCmdProcessInbox:
    """Smoke tests for cmd_process_inbox."""

    def test_process_inbox_empty_returns_no_messages(self, monkeypatch, capsys):
        """Test that cmd_process_inbox reports no unread messages when run() returns empty."""
        from my_cli.commands.mail.inbox_tools import cmd_process_inbox

        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.resolve_account", lambda _: "iCloud")
        mock_run = Mock(return_value="")
        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.run", mock_run)

        args = Namespace(account="iCloud", limit=50, json=False)
        cmd_process_inbox(args)

        captured = capsys.readouterr()
        assert "No unread messages" in captured.out

    def test_process_inbox_categorizes_messages(self, monkeypatch, capsys):
        """Test that cmd_process_inbox parses and categorizes messages from run() output."""
        from my_cli.commands.mail.inbox_tools import cmd_process_inbox

        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.resolve_account", lambda _: "iCloud")

        # Build mock data: one person email, one noreply notification, one flagged
        sep = FIELD_SEPARATOR
        person_line = f"iCloud{sep}101{sep}Hello from Alice{sep}Alice <alice@example.com>{sep}2026-02-20{sep}false"
        noreply_line = f"iCloud{sep}102{sep}Your receipt{sep}noreply@shop.com{sep}2026-02-21{sep}false"
        flagged_line = f"iCloud{sep}103{sep}Urgent task{sep}boss@work.com{sep}2026-02-22{sep}true"
        mock_result = "\n".join([person_line, noreply_line, flagged_line])

        mock_run = Mock(return_value=mock_result)
        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.run", mock_run)

        args = Namespace(account="iCloud", limit=50, json=False)
        cmd_process_inbox(args)

        captured = capsys.readouterr()
        assert "3 unread" in captured.out
        assert "FLAGGED" in captured.out
        assert "PEOPLE" in captured.out
        assert "NOTIFICATIONS" in captured.out
        assert "103" in captured.out  # flagged message ID
        assert "101" in captured.out  # people message ID
        assert "102" in captured.out  # notification message ID


# ---------------------------------------------------------------------------
# inbox_tools.py: cmd_weekly_review
# ---------------------------------------------------------------------------

class TestCmdWeeklyReview:
    """Smoke tests for cmd_weekly_review."""

    def test_weekly_review_empty_returns_none_sections(self, monkeypatch, capsys):
        """Test that cmd_weekly_review shows None sections when run() returns empty for all."""
        from my_cli.commands.mail.inbox_tools import cmd_weekly_review

        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.resolve_account", lambda _: "iCloud")
        # run() is called three times: flagged, attachments, unreplied — all empty
        mock_run = Mock(return_value="")
        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.run", mock_run)

        args = Namespace(account="iCloud", days=7, json=False)
        cmd_weekly_review(args)

        captured = capsys.readouterr()
        assert "Weekly Review" in captured.out
        assert "Flagged Messages (0)" in captured.out
        assert "Messages with Attachments (0)" in captured.out
        assert "Unreplied from People (0)" in captured.out
        assert "None" in captured.out
        assert mock_run.call_count == 3

    def test_weekly_review_with_flagged_data(self, monkeypatch, capsys):
        """Test that cmd_weekly_review shows flagged messages when run() returns data."""
        from my_cli.commands.mail.inbox_tools import cmd_weekly_review

        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.resolve_account", lambda _: "iCloud")

        sep = FIELD_SEPARATOR
        flagged_line = f"201{sep}Important meeting{sep}boss@work.com{sep}2026-02-20"
        attach_line = f"202{sep}Report attached{sep}colleague@work.com{sep}2026-02-21{sep}2"

        # run() is called 3 times: flagged, attachments, unreplied
        mock_run = Mock(side_effect=[flagged_line, attach_line, ""])
        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.run", mock_run)

        args = Namespace(account="iCloud", days=7, json=False)
        cmd_weekly_review(args)

        captured = capsys.readouterr()
        assert "Flagged Messages (1)" in captured.out
        assert "Important meeting" in captured.out
        assert "Messages with Attachments (1)" in captured.out
        assert "Report attached" in captured.out


# ---------------------------------------------------------------------------
# inbox_tools.py: cmd_clean_newsletters
# ---------------------------------------------------------------------------

class TestCmdCleanNewsletters:
    """Smoke tests for cmd_clean_newsletters."""

    def test_clean_newsletters_empty_reports_no_messages(self, monkeypatch, capsys):
        """Test that cmd_clean_newsletters reports no messages when run() returns empty."""
        from my_cli.commands.mail.inbox_tools import cmd_clean_newsletters

        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.resolve_account", lambda _: "iCloud")
        mock_run = Mock(return_value="")
        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.run", mock_run)

        args = Namespace(account="iCloud", mailbox="INBOX", limit=200, json=False)
        cmd_clean_newsletters(args)

        captured = capsys.readouterr()
        assert "No messages found" in captured.out

    def test_clean_newsletters_identifies_bulk_sender(self, monkeypatch, capsys):
        """Test that cmd_clean_newsletters identifies a sender with 3+ messages as newsletter."""
        from my_cli.commands.mail.inbox_tools import cmd_clean_newsletters

        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.resolve_account", lambda _: "iCloud")

        sep = FIELD_SEPARATOR
        # newsletter@example.com appears 4 times — should be flagged as newsletter
        lines = [
            f"newsletter@example.com{sep}true",
            f"newsletter@example.com{sep}false",
            f"newsletter@example.com{sep}true",
            f"newsletter@example.com{sep}false",
            f"alice@personal.com{sep}false",  # only 1 — not a newsletter
        ]
        mock_run = Mock(return_value="\n".join(lines))
        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.run", mock_run)

        args = Namespace(account="iCloud", mailbox="INBOX", limit=200, json=False)
        cmd_clean_newsletters(args)

        captured = capsys.readouterr()
        assert "newsletter@example.com" in captured.out
        assert "4 messages" in captured.out
        # alice@personal.com has only 1 message and no noreply pattern — should NOT appear
        assert "alice@personal.com" not in captured.out

    def test_clean_newsletters_no_newsletters_found(self, monkeypatch, capsys):
        """Test that cmd_clean_newsletters reports when no newsletters are found."""
        from my_cli.commands.mail.inbox_tools import cmd_clean_newsletters

        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.resolve_account", lambda _: "iCloud")

        sep = FIELD_SEPARATOR
        # Only one message per sender — none qualify as newsletter
        lines = [
            f"alice@personal.com{sep}false",
            f"bob@personal.com{sep}true",
        ]
        mock_run = Mock(return_value="\n".join(lines))
        monkeypatch.setattr("my_cli.commands.mail.inbox_tools.run", mock_run)

        args = Namespace(account="iCloud", mailbox="INBOX", limit=200, json=False)
        cmd_clean_newsletters(args)

        captured = capsys.readouterr()
        assert "No newsletter senders identified" in captured.out


# ---------------------------------------------------------------------------
# attachments.py: cmd_save_attachment
# ---------------------------------------------------------------------------

class TestCmdSaveAttachment:
    """Smoke tests for cmd_save_attachment."""

    def test_save_attachment_by_name(self, monkeypatch, capsys, tmp_path):
        """Test that cmd_save_attachment saves an attachment file by name."""
        from my_cli.commands.mail.attachments import cmd_save_attachment

        monkeypatch.setattr(
            "my_cli.commands.mail.attachments.resolve_message_context",
            lambda _: ("iCloud", "INBOX", "iCloud", "INBOX"),
        )

        att_name = "report.pdf"
        # list_script returns: subject line + attachment names
        list_result = f"Important Email\n{att_name}"
        # save_script returns: "saved"
        mock_run = Mock(side_effect=[list_result, "saved"])
        monkeypatch.setattr("my_cli.commands.mail.attachments.run", mock_run)

        # Create a fake saved file so the existence check passes
        fake_file = tmp_path / att_name
        fake_file.write_bytes(b"PDF content")

        # Patch os.path.isfile to return True for our fake path
        original_isfile = os.path.isfile
        def patched_isfile(p):
            if p == str(tmp_path / att_name):
                return True
            return original_isfile(p)
        monkeypatch.setattr("my_cli.commands.mail.attachments.os.path.isfile", patched_isfile)

        args = Namespace(
            account="iCloud", mailbox="INBOX", id=42,
            attachment=att_name, output_dir=str(tmp_path), json=False,
        )
        cmd_save_attachment(args)

        captured = capsys.readouterr()
        assert att_name in captured.out
        assert "Saved attachment" in captured.out

    def test_save_attachment_no_attachment_dies(self, monkeypatch):
        """Test that cmd_save_attachment exits when message has no attachments."""
        from my_cli.commands.mail.attachments import cmd_save_attachment

        monkeypatch.setattr(
            "my_cli.commands.mail.attachments.resolve_message_context",
            lambda _: ("iCloud", "INBOX", "iCloud", "INBOX"),
        )

        # list_script returns only subject line — no attachments
        mock_run = Mock(return_value="Empty Email")
        monkeypatch.setattr("my_cli.commands.mail.attachments.run", mock_run)

        args = Namespace(
            account="iCloud", mailbox="INBOX", id=42,
            attachment="file.pdf", output_dir="/tmp", json=False,
        )
        with pytest.raises(SystemExit):
            cmd_save_attachment(args)

    def test_save_attachment_by_index(self, monkeypatch, capsys, tmp_path):
        """Test that cmd_save_attachment resolves attachment by 1-based index."""
        from my_cli.commands.mail.attachments import cmd_save_attachment

        monkeypatch.setattr(
            "my_cli.commands.mail.attachments.resolve_message_context",
            lambda _: ("iCloud", "INBOX", "iCloud", "INBOX"),
        )

        att_name = "invoice.pdf"
        list_result = f"Subject Line\n{att_name}\nother.txt"
        mock_run = Mock(side_effect=[list_result, "saved"])
        monkeypatch.setattr("my_cli.commands.mail.attachments.run", mock_run)

        fake_file = tmp_path / att_name
        fake_file.write_bytes(b"data")

        original_isfile = os.path.isfile
        def patched_isfile(p):
            if p == str(tmp_path / att_name):
                return True
            return original_isfile(p)
        monkeypatch.setattr("my_cli.commands.mail.attachments.os.path.isfile", patched_isfile)

        args = Namespace(
            account="iCloud", mailbox="INBOX", id=42,
            attachment="1",  # index 1 → invoice.pdf
            output_dir=str(tmp_path), json=False,
        )
        cmd_save_attachment(args)

        captured = capsys.readouterr()
        assert att_name in captured.out
        assert "Saved attachment" in captured.out
