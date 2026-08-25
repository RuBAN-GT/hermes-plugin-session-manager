"""Hermes hooks, commands, CLI, and AI-tool adapter."""

from __future__ import annotations

import json
from contextvars import ContextVar
from typing import Any

from .core import SessionManager, SessionManagerError, SessionResult
from .i18n import t

_command_result: ContextVar[SessionResult | None] = ContextVar(
    "command_result", default=None
)
_command_error: ContextVar[str | None] = ContextVar("command_error", default=None)
_active_cli_session_id: str | None = None


def _set_cli_session(session_id: str | None) -> None:
    global _active_cli_session_id
    _active_cli_session_id = (session_id or "").strip() or None


def _on_cli_session(
    *,
    session_id: str | None = None,
    platform: str | None = None,
    **_kwargs: Any,
) -> None:
    if (platform or "").lower() == "cli":
        _set_cli_session(session_id)


def _pre_command_handler(manager: SessionManager):
    def handle(
        *,
        surface: str,
        command: str,
        args_raw: str,
        session_key: str | None = None,
        platform: str | None = None,
        session_id: str | None = None,
        **_kwargs: Any,
    ) -> None:
        if command not in {"archive", "delete"}:
            return
        if surface not in {"gateway", "cli"}:
            return
        valid_arguments = (
            not args_raw.strip()
            if command == "archive"
            else args_raw.strip() == "confirm"
        )
        if not valid_arguments:
            return
        _command_result.set(None)
        _command_error.set(None)
        try:
            if surface == "gateway":
                if (platform or "").lower() != "telegram":
                    _command_error.set(t("telegram_only", command=command))
                    return
                _command_result.set(
                    manager.manage_current_telegram_session(
                        session_key or "", command, confirm=command == "delete"
                    )
                )
                return
            current_session_id = (session_id or "").strip() or _active_cli_session_id
            if not current_session_id:
                _command_error.set(t("current_context_unavailable"))
                return
            _command_result.set(
                manager.manage_session(
                    current_session_id, command, confirm=command == "delete"
                )
            )
        except SessionManagerError as error:
            _command_error.set(str(error))
        except Exception:
            _command_error.set(t(f"current_action_failed_{command}"))

    return handle


def _command_handler(action: str, raw_args: str) -> str:
    valid_arguments = (
        not raw_args.strip() if action == "archive" else raw_args.strip() == "confirm"
    )
    if not valid_arguments:
        return t("usage_archive") if action == "archive" else t("usage_delete")
    result = _command_result.get()
    error = _command_error.get()
    _command_result.set(None)
    _command_error.set(None)
    if result:
        return result.message()
    if error:
        return error
    return t(f"nothing_changed_{action}")


def _archive_command(raw_args: str) -> str:
    return _command_handler("archive", raw_args)


def _delete_command(raw_args: str) -> str:
    return _command_handler("delete", raw_args)


def _parse_session_ids(raw: str) -> list[str]:
    session_ids: list[str] = []
    seen: set[str] = set()
    for part in str(raw or "").split(","):
        session_id = part.strip()
        if not session_id or session_id in seen:
            continue
        seen.add(session_id)
        session_ids.append(session_id)
    return session_ids


def _cli_setup(parser: Any) -> None:
    parser.add_argument("action", choices=("archive", "delete"))
    parser.add_argument(
        "--session-id",
        required=True,
        help="One session ID, or several separated by commas.",
    )
    parser.add_argument("--confirm", action="store_true")


def _cli_handler(manager: SessionManager, args: Any) -> None:
    session_ids = _parse_session_ids(args.session_id)
    if not session_ids:
        raise SystemExit(t("session_id_required"))
    errors: list[str] = []
    for session_id in session_ids:
        try:
            result = manager.manage_session(
                session_id, args.action, confirm=args.confirm
            )
        except SessionManagerError as error:
            errors.append(str(error))
            if len(session_ids) > 1:
                print(str(error))
            continue
        print(result.message())
    if not errors:
        return
    if len(session_ids) == 1:
        raise SystemExit(errors[0])
    raise SystemExit(
        t("cli_partial_failure", failed=len(errors), total=len(session_ids))
    )


def _tool_handler(manager: SessionManager):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        try:
            result = manager.manage_session(
                str(args.get("session_id") or ""),
                str(args.get("action") or ""),
                confirm=args.get("confirm") is True,
            )
        except SessionManagerError as error:
            return json.dumps({"ok": False, "error": str(error)})
        return json.dumps({"ok": True, "result": result.__dict__})

    return handle


def register(ctx: Any) -> None:
    """Register Telegram, CLI, and AI session-management interfaces."""
    manager = SessionManager()
    ctx.register_hook("pre_command", _pre_command_handler(manager))
    ctx.register_hook("on_session_start", _on_cli_session)
    ctx.register_hook("on_session_reset", _on_cli_session)
    ctx.register_command(
        "archive",
        _archive_command,
        description="Archive the current Telegram or CLI session without deleting history",
    )
    ctx.register_command(
        "delete",
        _delete_command,
        description="Delete the current Telegram or CLI session",
    )
    ctx.register_cli_command(
        "session-manager",
        "Archive or delete one Telegram or CLI Hermes session.",
        _cli_setup,
        lambda args: _cli_handler(manager, args),
    )
    ctx.register_tool(
        name="manage_telegram_session",
        toolset="session-manager",
        schema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["archive", "delete"]},
                "session_id": {"type": "string"},
                "confirm": {"type": "boolean", "default": False},
            },
            "required": ["action", "session_id"],
            "additionalProperties": False,
        },
        handler=_tool_handler(manager),
        description=(
            "Archive or delete one explicit Telegram or CLI session. "
            "Delete requires confirm=true."
        ),
    )
