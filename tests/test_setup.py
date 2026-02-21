"""Tests for the my mail init setup wizard command."""

import json
import os
from unittest.mock import Mock


from my_cli.config import FIELD_SEPARATOR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_account_line(name, email, enabled=True):
    enabled_str = "true" if enabled else "false"
    return f"{name}{FIELD_SEPARATOR}{email}{FIELD_SEPARATOR}{enabled_str}"


# ---------------------------------------------------------------------------
# test_init_no_accounts
# ---------------------------------------------------------------------------

def test_init_no_accounts(monkeypatch, mock_args, capsys, tmp_path):
    """When run() returns empty, print an error and return early."""
    from my_cli.commands.mail.setup import cmd_init

    # Point config file at a path that genuinely does not exist
    config_dir = str(tmp_path / "cfg")
    config_file = str(tmp_path / "cfg" / "config.json")
    monkeypatch.setattr("my_cli.commands.mail.setup.CONFIG_DIR", config_dir)
    monkeypatch.setattr("my_cli.commands.mail.setup.CONFIG_FILE", config_file)

    mock_run = Mock(return_value="")
    monkeypatch.setattr("my_cli.commands.mail.setup.run", mock_run)

    args = mock_args()
    cmd_init(args)

    captured = capsys.readouterr()
    assert "No mail accounts found" in captured.out


# ---------------------------------------------------------------------------
# test_init_single_account_autoselect
# ---------------------------------------------------------------------------

def test_init_single_account_autoselect(monkeypatch, mock_args, capsys, tmp_path):
    """One enabled account: auto-select it and write config."""
    from my_cli.commands.mail.setup import cmd_init

    config_dir = str(tmp_path / "config")
    config_file = str(tmp_path / "config" / "config.json")
    monkeypatch.setattr("my_cli.commands.mail.setup.CONFIG_DIR", config_dir)
    monkeypatch.setattr("my_cli.commands.mail.setup.CONFIG_FILE", config_file)

    acct_line = _make_account_line("iCloud", "me@icloud.com", enabled=True)
    mock_run = Mock(return_value=acct_line + "\n")
    monkeypatch.setattr("my_cli.commands.mail.setup.run", mock_run)

    # config_file genuinely does not exist (fresh tmp_path) — no patch needed
    # Skip Todoist token
    monkeypatch.setattr("builtins.input", lambda _: "")

    args = mock_args()
    cmd_init(args)

    captured = capsys.readouterr()
    assert "Auto-selected" in captured.out
    assert "iCloud" in captured.out

    assert os.path.isfile(config_file)
    with open(config_file) as f:
        cfg = json.load(f)
    assert cfg["mail"]["default_account"] == "iCloud"


# ---------------------------------------------------------------------------
# test_init_multiple_accounts
# ---------------------------------------------------------------------------

def test_init_multiple_accounts(monkeypatch, mock_args, capsys, tmp_path):
    """Multiple accounts: user picks one by number, config is written."""
    from my_cli.commands.mail.setup import cmd_init

    config_dir = str(tmp_path / "config")
    config_file = str(tmp_path / "config" / "config.json")
    monkeypatch.setattr("my_cli.commands.mail.setup.CONFIG_DIR", config_dir)
    monkeypatch.setattr("my_cli.commands.mail.setup.CONFIG_FILE", config_file)

    lines = "\n".join([
        _make_account_line("iCloud", "me@icloud.com", enabled=True),
        _make_account_line("Gmail", "me@gmail.com", enabled=True),
    ]) + "\n"
    mock_run = Mock(return_value=lines)
    monkeypatch.setattr("my_cli.commands.mail.setup.run", mock_run)

    # config_file genuinely does not exist — no patch needed

    # User picks account 2 (Gmail), skips Todoist token
    inputs = iter(["2", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    args = mock_args()
    cmd_init(args)

    assert os.path.isfile(config_file)
    with open(config_file) as f:
        cfg = json.load(f)
    assert cfg["mail"]["default_account"] == "Gmail"


# ---------------------------------------------------------------------------
# test_init_existing_config
# ---------------------------------------------------------------------------

def test_init_existing_config(monkeypatch, mock_args, capsys, tmp_path):
    """Existing config: user says 'y' to reconfigure, wizard runs."""
    from my_cli.commands.mail.setup import cmd_init

    config_dir = str(tmp_path / "config")
    config_file = str(tmp_path / "config" / "config.json")
    os.makedirs(config_dir, exist_ok=True)

    # Write an existing config so os.path.isfile returns True for real
    existing = {"mail": {"default_account": "OldAccount"}}
    with open(config_file, "w") as f:
        json.dump(existing, f)

    monkeypatch.setattr("my_cli.commands.mail.setup.CONFIG_DIR", config_dir)
    monkeypatch.setattr("my_cli.commands.mail.setup.CONFIG_FILE", config_file)

    acct_line = _make_account_line("iCloud", "me@icloud.com", enabled=True)
    mock_run = Mock(return_value=acct_line + "\n")
    monkeypatch.setattr("my_cli.commands.mail.setup.run", mock_run)
    monkeypatch.setattr("my_cli.commands.mail.setup.get_config", lambda: existing)

    # "y" to reconfigure, then skip Todoist token
    inputs = iter(["y", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    args = mock_args()
    cmd_init(args)

    captured = capsys.readouterr()
    assert "Auto-selected" in captured.out

    with open(config_file) as f:
        cfg = json.load(f)
    assert cfg["mail"]["default_account"] == "iCloud"


# ---------------------------------------------------------------------------
# test_init_json_output
# ---------------------------------------------------------------------------

def test_init_json_output(monkeypatch, mock_args, capsys, tmp_path):
    """--json flag outputs the written config as JSON."""
    from my_cli.commands.mail.setup import cmd_init

    config_dir = str(tmp_path / "config")
    config_file = str(tmp_path / "config" / "config.json")
    monkeypatch.setattr("my_cli.commands.mail.setup.CONFIG_DIR", config_dir)
    monkeypatch.setattr("my_cli.commands.mail.setup.CONFIG_FILE", config_file)

    acct_line = _make_account_line("iCloud", "me@icloud.com", enabled=True)
    mock_run = Mock(return_value=acct_line + "\n")
    monkeypatch.setattr("my_cli.commands.mail.setup.run", mock_run)
    # config_file genuinely does not exist — no patch needed
    monkeypatch.setattr("builtins.input", lambda _: "")

    args = mock_args(json=True)
    cmd_init(args)

    captured = capsys.readouterr()
    assert '"default_account"' in captured.out
    assert "iCloud" in captured.out


# ---------------------------------------------------------------------------
# test_init_creates_config_dir
# ---------------------------------------------------------------------------

def test_init_creates_config_dir(monkeypatch, mock_args, capsys, tmp_path):
    """Config directory is created if it doesn't exist."""
    from my_cli.commands.mail.setup import cmd_init

    config_dir = str(tmp_path / "new_config_dir")
    config_file = str(tmp_path / "new_config_dir" / "config.json")

    # Directory does NOT exist yet
    assert not os.path.isdir(config_dir)

    monkeypatch.setattr("my_cli.commands.mail.setup.CONFIG_DIR", config_dir)
    monkeypatch.setattr("my_cli.commands.mail.setup.CONFIG_FILE", config_file)

    acct_line = _make_account_line("iCloud", "me@icloud.com", enabled=True)
    mock_run = Mock(return_value=acct_line + "\n")
    monkeypatch.setattr("my_cli.commands.mail.setup.run", mock_run)
    # config_file genuinely does not exist — no patch needed
    monkeypatch.setattr("builtins.input", lambda _: "")

    args = mock_args()
    cmd_init(args)

    # Directory and config file should now exist
    assert os.path.isdir(config_dir)
    assert os.path.isfile(config_file)
