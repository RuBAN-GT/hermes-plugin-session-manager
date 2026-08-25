from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from hermes_session_manager.core import SessionManagerError, SessionResult
from hermes_session_manager.plugin import (
    _archive_command,
    _cli_handler,
    _delete_command,
    _on_cli_session,
    _parse_session_ids,
    _pre_command_handler,
    _set_cli_session,
    _tool_handler,
    register,
)


class FakeManager:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def manage_current_telegram_session(self, session_key, action, *, confirm):
        self.calls.append((session_key, action, confirm))
        if self.error:
            raise self.error
        return self.result

    def manage_session(self, session_id, action, *, confirm=False):
        self.calls.append((session_id, action, confirm))
        if self.error:
            raise self.error
        return self.result


class FakeContext:
    def __init__(self):
        self.hooks = []
        self.commands = []
        self.cli_commands = []
        self.tools = []

    def register_hook(self, *args):
        self.hooks.append(args)

    def register_command(self, *args, **kwargs):
        self.commands.append((args, kwargs))

    def register_cli_command(self, *args, **kwargs):
        self.cli_commands.append((args, kwargs))

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)


class PluginTests(unittest.TestCase):
    def test_telegram_commands_archive_or_delete_only_current_session(self):
        manager = FakeManager(SessionResult("archive", "s-1", "Topic", "17"))
        hook = _pre_command_handler(manager)

        hook(
            surface="gateway",
            command="archive",
            args_raw="",
            session_key="route",
            platform="telegram",
        )

        self.assertEqual(manager.calls, [("route", "archive", False)])
        self.assertIn("s-1", _archive_command(""))
        manager.result = SessionResult("delete", "s-1", "Topic", "17")
        hook(
            surface="gateway",
            command="delete",
            args_raw="confirm",
            session_key="route",
            platform="telegram",
        )
        self.assertEqual(manager.calls[-1], ("route", "delete", True))
        self.assertIn("Deleted session", _delete_command("confirm"))

    def test_cli_commands_archive_or_delete_tracked_session(self):
        manager = FakeManager(SessionResult("archive", "cli-1", "CLI work", None))
        hook = _pre_command_handler(manager)
        _set_cli_session(None)
        _on_cli_session(session_id="cli-1", platform="cli")

        hook(surface="cli", command="archive", args_raw="")

        self.assertEqual(manager.calls, [("cli-1", "archive", False)])
        self.assertIn("cli-1", _archive_command(""))
        manager.result = SessionResult("delete", "cli-1", "CLI work", None)
        hook(surface="cli", command="delete", args_raw="confirm")
        self.assertEqual(manager.calls[-1], ("cli-1", "delete", True))
        self.assertIn("Deleted session", _delete_command("confirm"))
        _set_cli_session(None)

    def test_cli_commands_use_explicit_session_id_when_provided(self):
        manager = FakeManager(SessionResult("archive", "cli-2", None, None))
        hook = _pre_command_handler(manager)
        _set_cli_session(None)

        hook(surface="cli", command="archive", args_raw="", session_id="cli-2")

        self.assertEqual(manager.calls, [("cli-2", "archive", False)])
        self.assertIn("cli-2", _archive_command(""))
        _set_cli_session(None)

    def test_commands_reject_invalid_arguments_and_missing_cli_context(self):
        manager = FakeManager(SessionResult("archive", "s-1", None, None))
        hook = _pre_command_handler(manager)
        _set_cli_session(None)

        hook(surface="cli", command="archive", args_raw="")
        hook(
            surface="gateway",
            command="delete",
            args_raw="",
            session_key="route",
            platform="telegram",
        )

        self.assertEqual(manager.calls, [])
        self.assertIn("unavailable", _archive_command(""))
        self.assertEqual(_archive_command("all"), "Usage: /archive")
        self.assertEqual(_delete_command(""), "Usage: /delete confirm")

    def test_cli_archives_comma_separated_session_ids(self):
        manager = FakeManager(SessionResult("archive", "s-1", None, None))
        _cli_handler(
            manager,
            SimpleNamespace(
                session_id="s-1, s-2,,s-1", action="archive", confirm=False
            ),
        )
        self.assertEqual(
            manager.calls,
            [("s-1", "archive", False), ("s-2", "archive", False)],
        )
        self.assertEqual(_parse_session_ids("s-1, s-2,,s-3"), ["s-1", "s-2", "s-3"])

    def test_cli_continues_after_one_failed_session_id(self):
        class MixedManager(FakeManager):
            def manage_session(self, session_id, action, *, confirm=False):
                self.calls.append((session_id, action, confirm))
                if session_id == "missing":
                    raise SessionManagerError("Session not found.")
                return SessionResult(action, session_id, None, None)

        manager = MixedManager()
        with self.assertRaisesRegex(SystemExit, "1 of 2"):
            _cli_handler(
                manager,
                SimpleNamespace(
                    session_id="ok,missing", action="archive", confirm=False
                ),
            )
        self.assertEqual(
            manager.calls,
            [("ok", "archive", False), ("missing", "archive", False)],
        )

    def test_cli_and_ai_tool_pass_explicit_session_id_and_confirmation(self):
        manager = FakeManager(SessionResult("delete", "s-1", None, None))
        _cli_handler(
            manager, SimpleNamespace(session_id="s-1", action="delete", confirm=True)
        )
        self.assertEqual(manager.calls, [("s-1", "delete", True)])
        handler = _tool_handler(manager)

        response = json.loads(handler({"action": "delete", "session_id": "s-1"}))

        self.assertEqual(manager.calls[-1], ("s-1", "delete", False))
        self.assertTrue(response["ok"])

    def test_failures_are_returned_to_telegram_cli_and_ai(self):
        manager = FakeManager(
            error=SessionManagerError("Deletion requires confirm=true.")
        )
        hook = _pre_command_handler(manager)
        hook(
            surface="gateway",
            command="delete",
            args_raw="confirm",
            session_key="route",
            platform="telegram",
        )
        self.assertEqual(_delete_command("confirm"), "Deletion requires confirm=true.")
        with self.assertRaisesRegex(SystemExit, "confirm"):
            _cli_handler(
                manager,
                SimpleNamespace(session_id="s-1", action="delete", confirm=False),
            )
        self.assertFalse(json.loads(_tool_handler(manager)({}))["ok"])

    def test_registers_all_interfaces(self):
        context = FakeContext()

        register(context)

        self.assertEqual(
            [hook[0] for hook in context.hooks],
            ["pre_command", "on_session_start", "on_session_reset"],
        )
        self.assertEqual(
            [entry[0][0] for entry in context.commands], ["archive", "delete"]
        )
        self.assertEqual(context.cli_commands[0][0][0], "session-manager")
        self.assertEqual(context.tools[0]["name"], "manage_telegram_session")


if __name__ == "__main__":
    unittest.main()
