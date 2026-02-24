"""Tests for formatting module."""

import json
from argparse import Namespace

import pytest

from mxctl.util.formatting import die, format_output, output, truncate


class TestTruncate:
    """Test string truncation."""

    def test_normal_truncation(self):
        assert truncate("hello world", 8) == "hello..."

    def test_exact_length(self):
        assert truncate("hello", 5) == "hello"

    def test_shorter_than_max(self):
        assert truncate("hi", 10) == "hi"

    def test_empty_string(self):
        assert truncate("", 10) == ""

    def test_none_returns_empty(self):
        assert truncate(None, 10) == ""


class TestOutput:
    """Test output formatting."""

    def test_text_mode(self, capsys):
        output("hello world", use_json=False)
        captured = capsys.readouterr()
        assert captured.out == "hello world\n"

    def test_json_mode(self, capsys):
        data = {"key": "value"}
        output("ignored", json_data=data, use_json=True)
        captured = capsys.readouterr()
        assert json.loads(captured.out) == data

    def test_json_mode_without_data(self, capsys):
        output("fallback text", use_json=True)
        captured = capsys.readouterr()
        assert captured.out == "fallback text\n"

    def test_json_converts_dates(self, capsys):
        data = {
            "date_received": "Tuesday, January 14, 2026 at 2:30:00 PM",
            "subject": "Test",
            "sender": "test@example.com",
        }
        output("ignored", json_data=data, use_json=True)
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["date_received"] == "2026-01-14T14:30:00"
        assert result["subject"] == "Test"  # Non-date fields unchanged

    def test_json_converts_nested_dates(self, capsys):
        data = {
            "messages": [
                {"date_sent": "January 14, 2026 at 9:00:00 AM", "subject": "Test 1"},
                {"date_sent": "January 15, 2026 at 3:30:00 PM", "subject": "Test 2"},
            ]
        }
        output("ignored", json_data=data, use_json=True)
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["messages"][0]["date_sent"] == "2026-01-14T09:00:00"
        assert result["messages"][1]["date_sent"] == "2026-01-15T15:30:00"


class TestFormatOutput:
    """Test args-based output routing."""

    def test_routes_to_text(self, capsys):
        args = Namespace(json=False)
        format_output(args, "hello")
        captured = capsys.readouterr()
        assert captured.out == "hello\n"

    def test_routes_to_json(self, capsys):
        args = Namespace(json=True)
        data = {"test": "data"}
        format_output(args, "ignored", json_data=data)
        captured = capsys.readouterr()
        assert json.loads(captured.out) == data

    def test_missing_json_attribute_defaults_false(self, capsys):
        args = Namespace()
        format_output(args, "hello")
        captured = capsys.readouterr()
        assert captured.out == "hello\n"


class TestDie:
    """Test error exit."""

    def test_prints_to_stderr_and_exits(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            die("test error")
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert captured.err == "Error: test error\n"

    def test_custom_exit_code(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            die("custom error", code=42)
        assert exc_info.value.code == 42
