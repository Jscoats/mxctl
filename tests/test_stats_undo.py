"""Tests for enhanced stats and undo functionality."""

from unittest.mock import Mock, patch
import pytest
from my_cli.commands.mail.analytics import cmd_stats


@pytest.fixture
def mock_args():
    """Create mock args object."""
    def _create(**kwargs):
        args = Mock()
        for k, v in kwargs.items():
            setattr(args, k, v)
        return args
    return _create


class TestEnhancedStats:
    """Test enhanced stats with --all flag."""

    @patch("my_cli.commands.mail.analytics.run")
    def test_stats_all_flag_shows_all_mailboxes(self, mock_run, mock_args, capsys):
        """Test that --all flag shows account-wide stats."""
        # Mock AppleScript output: grand totals on first line, then per-mailbox
        mock_run.return_value = (
            "150\x1F25\n"  # Grand totals: 150 total, 25 unread
            "INBOX\x1F100\x1F20\n"
            "Sent Messages\x1F30\x1F0\n"
            "Archive\x1F20\x1F5"
        )
        args = mock_args(account="iCloud", all=True, json=False, mailbox=None)

        cmd_stats(args)

        captured = capsys.readouterr()
        assert "Account: iCloud" in captured.out
        assert "Total: 150 messages, 25 unread" in captured.out
        assert "INBOX: 100 messages, 20 unread" in captured.out
        assert "Sent Messages: 30 messages, 0 unread" in captured.out
        assert "Archive: 20 messages, 5 unread" in captured.out

    @patch("my_cli.commands.mail.analytics.run")
    def test_stats_without_all_flag_single_mailbox(self, mock_run, mock_args, capsys):
        """Test that without --all flag, shows single mailbox stats."""
        mock_run.return_value = "100\x1F20"  # 100 total, 20 unread
        args = mock_args(account="iCloud", all=False, json=False, mailbox="INBOX")

        cmd_stats(args)

        captured = capsys.readouterr()
        assert "INBOX [iCloud]: 100 messages, 20 unread" in captured.out


class TestUndoLogging:
    """Test undo operation logging."""

    def test_log_batch_operation_creates_entry(self, tmp_path, monkeypatch):
        """Test that logging a batch operation creates a proper entry."""
        import my_cli.commands.mail.undo as undo_module
        test_log = tmp_path / "mail-undo.json"
        monkeypatch.setattr(undo_module, "UNDO_LOG_FILE", str(test_log))

        undo_module.log_batch_operation(
            operation_type="batch-move",
            account="iCloud",
            message_ids=[123, 456, 789],
            source_mailbox=None,
            dest_mailbox="Archive",
            sender="test@example.com",
        )

        # Reload and check
        operations = undo_module._load_undo_log()
        assert len(operations) == 1
        assert operations[0]["operation"] == "batch-move"
        assert operations[0]["account"] == "iCloud"
        assert operations[0]["message_ids"] == [123, 456, 789]
        assert operations[0]["dest_mailbox"] == "Archive"
        assert operations[0]["sender"] == "test@example.com"

    def test_undo_log_keeps_only_last_10_operations(self, tmp_path, monkeypatch):
        """Test that undo log is trimmed to MAX_UNDO_OPERATIONS."""
        import my_cli.commands.mail.undo as undo_module
        test_log = tmp_path / "mail-undo.json"
        monkeypatch.setattr(undo_module, "UNDO_LOG_FILE", str(test_log))

        # Add 15 operations
        for i in range(15):
            undo_module.log_batch_operation(
                operation_type="batch-delete",
                account="iCloud",
                message_ids=[i],
                source_mailbox="Trash",
            )

        operations = undo_module._load_undo_log()
        assert len(operations) == 10  # Should keep only last 10

    def test_undo_list_shows_recent_operations(self, tmp_path, monkeypatch, mock_args, capsys):
        """Test that undo --list shows recent operations."""
        import my_cli.commands.mail.undo as undo_module
        test_log = tmp_path / "mail-undo.json"
        monkeypatch.setattr(undo_module, "UNDO_LOG_FILE", str(test_log))

        undo_module.log_batch_operation(
            operation_type="batch-move",
            account="iCloud",
            message_ids=[100, 200],
            dest_mailbox="Archive",
            sender="test@example.com",
        )

        args = mock_args(json=False)
        undo_module.cmd_undo_list(args)

        captured = capsys.readouterr()
        assert "Recent batch operations" in captured.out
        assert "batch-move" in captured.out
        assert "2 messages" in captured.out

    def test_undo_list_empty_when_no_operations(self, tmp_path, monkeypatch, mock_args, capsys):
        """Test that undo --list shows appropriate message when empty."""
        import my_cli.commands.mail.undo as undo_module
        test_log = tmp_path / "mail-undo-empty.json"
        monkeypatch.setattr(undo_module, "UNDO_LOG_FILE", str(test_log))

        args = mock_args(json=False)
        undo_module.cmd_undo_list(args)

        captured = capsys.readouterr()
        assert "No recent batch operations to undo" in captured.out
