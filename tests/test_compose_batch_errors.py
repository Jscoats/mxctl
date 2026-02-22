"""Tests for compose.py error paths and batch.py dry-run edge cases."""

import json
from argparse import Namespace
from unittest.mock import Mock, patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_args(**kwargs):
    defaults = {"json": False, "account": "iCloud", "mailbox": "INBOX"}
    defaults.update(kwargs)
    return Namespace(**defaults)


# ---------------------------------------------------------------------------
# compose.py: cmd_draft error paths
# ---------------------------------------------------------------------------

class TestDraftErrors:
    def test_draft_no_account_dies(self, monkeypatch):
        from my_cli.commands.mail.compose import cmd_draft

        monkeypatch.setattr("my_cli.commands.mail.compose.resolve_account", lambda _: None)

        with pytest.raises(SystemExit):
            cmd_draft(_make_args(account=None, to="x@y.com", subject="S", body="B",
                                 template=None, cc=None, bcc=None))

    def test_draft_no_subject_no_template_dies(self, monkeypatch):
        from my_cli.commands.mail.compose import cmd_draft

        monkeypatch.setattr("my_cli.commands.mail.compose.resolve_account", lambda _: "iCloud")

        with pytest.raises(SystemExit):
            cmd_draft(_make_args(to="x@y.com", subject=None, body="hello",
                                 template=None, cc=None, bcc=None))

    def test_draft_no_body_no_template_dies(self, monkeypatch):
        from my_cli.commands.mail.compose import cmd_draft

        monkeypatch.setattr("my_cli.commands.mail.compose.resolve_account", lambda _: "iCloud")

        with pytest.raises(SystemExit):
            cmd_draft(_make_args(to="x@y.com", subject="hello", body=None,
                                 template=None, cc=None, bcc=None))

    def test_draft_template_not_found_dies(self, monkeypatch, tmp_path):
        from my_cli.commands.mail.compose import cmd_draft

        monkeypatch.setattr("my_cli.commands.mail.compose.resolve_account", lambda _: "iCloud")

        # Create a valid templates file without the requested template
        tpl_file = str(tmp_path / "templates.json")
        with open(tpl_file, "w") as f:
            json.dump({"other": {"subject": "S", "body": "B"}}, f)

        monkeypatch.setattr("my_cli.commands.mail.compose.TEMPLATES_FILE", tpl_file)

        with pytest.raises(SystemExit):
            cmd_draft(_make_args(to="x@y.com", subject=None, body=None,
                                 template="missing", cc=None, bcc=None))

    def test_draft_corrupt_template_file_dies(self, monkeypatch, tmp_path):
        from my_cli.commands.mail.compose import cmd_draft

        monkeypatch.setattr("my_cli.commands.mail.compose.resolve_account", lambda _: "iCloud")

        tpl_file = str(tmp_path / "templates.json")
        with open(tpl_file, "w") as f:
            f.write("{corrupt json")

        monkeypatch.setattr("my_cli.commands.mail.compose.TEMPLATES_FILE", tpl_file)

        with pytest.raises(SystemExit):
            cmd_draft(_make_args(to="x@y.com", subject=None, body=None,
                                 template="any", cc=None, bcc=None))

    def test_draft_no_templates_file_dies(self, monkeypatch, tmp_path):
        from my_cli.commands.mail.compose import cmd_draft

        monkeypatch.setattr("my_cli.commands.mail.compose.resolve_account", lambda _: "iCloud")
        monkeypatch.setattr("my_cli.commands.mail.compose.TEMPLATES_FILE",
                            str(tmp_path / "nonexistent.json"))

        with pytest.raises(SystemExit):
            cmd_draft(_make_args(to="x@y.com", subject=None, body=None,
                                 template="any", cc=None, bcc=None))


# ---------------------------------------------------------------------------
# batch.py: dry-run effective_count edge cases
# ---------------------------------------------------------------------------

class TestBatchMoveEffectiveCount:
    def test_dry_run_with_limit_caps_count(self, monkeypatch, capsys):
        from my_cli.commands.mail.batch import cmd_batch_move

        monkeypatch.setattr("my_cli.commands.mail.batch.resolve_account", lambda _: "iCloud")
        mock_run = Mock(return_value="50")
        monkeypatch.setattr("my_cli.commands.mail.batch.run", mock_run)

        args = _make_args(from_sender="test@x.com", to_mailbox="Archive",
                          dry_run=True, limit=10)
        cmd_batch_move(args)

        out = capsys.readouterr().out
        assert "10" in out  # effective_count = min(50, 10) = 10

    def test_dry_run_without_limit_uses_total(self, monkeypatch, capsys):
        from my_cli.commands.mail.batch import cmd_batch_move

        monkeypatch.setattr("my_cli.commands.mail.batch.resolve_account", lambda _: "iCloud")
        mock_run = Mock(return_value="25")
        monkeypatch.setattr("my_cli.commands.mail.batch.run", mock_run)

        args = _make_args(from_sender="test@x.com", to_mailbox="Archive",
                          dry_run=True, limit=None)
        cmd_batch_move(args)

        out = capsys.readouterr().out
        assert "25" in out  # effective_count = total = 25


class TestBatchDeleteEffectiveCount:
    def test_dry_run_with_limit_caps_count(self, monkeypatch, capsys):
        from my_cli.commands.mail.batch import cmd_batch_delete

        monkeypatch.setattr("my_cli.commands.mail.batch.resolve_account", lambda _: "iCloud")
        mock_run = Mock(return_value="100")
        monkeypatch.setattr("my_cli.commands.mail.batch.run", mock_run)

        args = _make_args(from_sender="spam@x.com", older_than=None,
                          dry_run=True, limit=20, force=False)
        cmd_batch_delete(args)

        out = capsys.readouterr().out
        assert "20" in out  # effective_count = min(100, 20) = 20

    def test_dry_run_without_limit_uses_total(self, monkeypatch, capsys):
        from my_cli.commands.mail.batch import cmd_batch_delete

        monkeypatch.setattr("my_cli.commands.mail.batch.resolve_account", lambda _: "iCloud")
        mock_run = Mock(return_value="42")
        monkeypatch.setattr("my_cli.commands.mail.batch.run", mock_run)

        args = _make_args(from_sender="spam@x.com", older_than=None,
                          dry_run=True, limit=None, force=False)
        cmd_batch_delete(args)

        out = capsys.readouterr().out
        assert "42" in out  # effective_count = total = 42


# ---------------------------------------------------------------------------
# todoist_integration.py: cmd_to_todoist
# ---------------------------------------------------------------------------

class TestCmdToTodoist:
    def test_to_todoist_missing_token_dies(self, monkeypatch):
        """Test that missing Todoist API token causes SystemExit."""
        from my_cli.commands.mail.todoist_integration import cmd_to_todoist

        monkeypatch.setattr(
            "my_cli.commands.mail.todoist_integration.resolve_message_context",
            lambda _: ("iCloud", "INBOX", "iCloud", "INBOX"),
        )
        monkeypatch.setattr(
            "my_cli.commands.mail.todoist_integration.get_config",
            lambda: {},  # no todoist_api_token
        )

        args = _make_args(id=42, project=None, priority=1, due=None)
        with pytest.raises(SystemExit):
            cmd_to_todoist(args)

    def test_to_todoist_happy_path(self, monkeypatch, capsys):
        """Test that cmd_to_todoist creates a task via the API."""
        from my_cli.commands.mail.todoist_integration import cmd_to_todoist
        from my_cli.config import FIELD_SEPARATOR

        monkeypatch.setattr(
            "my_cli.commands.mail.todoist_integration.resolve_message_context",
            lambda _: ("iCloud", "INBOX", "iCloud", "INBOX"),
        )
        monkeypatch.setattr(
            "my_cli.commands.mail.todoist_integration.get_config",
            lambda: {"todoist_api_token": "test-token-123"},
        )

        # Mock AppleScript run to return message data
        mock_run = Mock(
            return_value=f"Test Subject{FIELD_SEPARATOR}sender@example.com{FIELD_SEPARATOR}2026-01-15"
        )
        monkeypatch.setattr("my_cli.commands.mail.todoist_integration.run", mock_run)

        # Mock the urllib HTTP call
        fake_response_data = {"id": "task-999", "content": "Test Subject", "url": "https://todoist.com/tasks/999"}
        fake_response = MagicMock()
        fake_response.__enter__ = lambda s: s
        fake_response.__exit__ = Mock(return_value=False)
        fake_response.read.return_value = json.dumps(fake_response_data).encode("utf-8")

        with patch("my_cli.commands.mail.todoist_integration.urllib.request.urlopen", return_value=fake_response):
            args = _make_args(id=42, project=None, priority=1, due=None)
            cmd_to_todoist(args)

        out = capsys.readouterr().out
        assert "Test Subject" in out
        assert "Created Todoist task" in out


# ---------------------------------------------------------------------------
# actions.py: cmd_unsubscribe
# ---------------------------------------------------------------------------

class TestCmdUnsubscribe:
    def test_unsubscribe_dry_run_shows_list_unsubscribe_url(self, monkeypatch, capsys):
        """Test that --dry-run shows the List-Unsubscribe URL from headers."""
        from my_cli.commands.mail.actions import cmd_unsubscribe
        from my_cli.config import FIELD_SEPARATOR

        monkeypatch.setattr(
            "my_cli.commands.mail.actions.resolve_message_context",
            lambda _: ("iCloud", "INBOX", "iCloud", "INBOX"),
        )

        # AppleScript returns subject + raw headers containing List-Unsubscribe
        unsub_url = "https://example.com/unsubscribe?token=abc123"
        raw_headers = (
            f"List-Unsubscribe: <{unsub_url}>\n"
            "From: newsletter@example.com\n"
        )
        mock_run = Mock(
            return_value=f"Newsletter Subject{FIELD_SEPARATOR}HEADER_SPLIT{FIELD_SEPARATOR}{raw_headers}"
        )
        monkeypatch.setattr("my_cli.commands.mail.actions.run", mock_run)

        args = _make_args(id=99, dry_run=True, open=False)
        cmd_unsubscribe(args)

        out = capsys.readouterr().out
        assert unsub_url in out
        assert "HTTPS" in out or "https" in out.lower()
