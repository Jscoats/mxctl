"""Mail command registration — wires all mail subcommands into argparse."""

from my_cli.commands.mail.accounts import register as register_accounts
from my_cli.commands.mail.messages import register as register_messages
from my_cli.commands.mail.actions import register as register_actions
from my_cli.commands.mail.compose import register as register_compose
from my_cli.commands.mail.attachments import register as register_attachments
from my_cli.commands.mail.manage import register as register_manage
from my_cli.commands.mail.batch import register as register_batch
from my_cli.commands.mail.analytics import register as register_analytics
from my_cli.commands.mail.system import register as register_system
from my_cli.commands.mail.composite import register as register_composite
from my_cli.commands.mail.ai import register as register_ai
from my_cli.commands.mail.todoist_integration import register as register_todoist
from my_cli.commands.mail.inbox_tools import register as register_inbox_tools
from my_cli.commands.mail.templates import register as register_templates
from my_cli.commands.mail.undo import register as register_undo


def register_mail_subcommand(parent_subparsers) -> None:
    """Register mail subcommands into the argparse tree."""
    mail_parser = parent_subparsers.add_parser("mail", help="Apple Mail operations")
    mail_sub = mail_parser.add_subparsers(dest="mail_command")

    register_accounts(mail_sub)
    register_messages(mail_sub)
    register_actions(mail_sub)
    register_compose(mail_sub)
    register_attachments(mail_sub)
    register_manage(mail_sub)
    register_batch(mail_sub)
    register_analytics(mail_sub)
    register_system(mail_sub)
    register_composite(mail_sub)
    register_ai(mail_sub)
    register_todoist(mail_sub)
    register_inbox_tools(mail_sub)
    register_templates(mail_sub)
    register_undo(mail_sub)

    # If `my mail` is run with no subcommand, show help
    mail_parser.set_defaults(func=lambda _: mail_parser.print_help())
