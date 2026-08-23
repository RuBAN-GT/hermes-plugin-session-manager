"""Transport-independent Telegram session management."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol

from .i18n import t


class SessionStore(Protocol):
    """Subset of Hermes SessionDB required by this plugin."""

    def find_latest_gateway_session_for_peer(
        self, *, source: str, session_key: str
    ) -> dict[str, Any] | None: ...

    def set_session_archived(self, session_id: str, archived: bool) -> bool: ...

    def set_session_title(self, session_id: str, title: str) -> bool: ...

    def get_session(self, session_id: str) -> dict[str, Any] | None: ...

    def get_session_delete_targets(self, session_id: str) -> list[str]: ...

    def delete_session(
        self,
        session_id: str,
        *,
        sessions_dir: Path | None = None,
        expected_delete_ids: list[str],
    ) -> bool: ...

    def close(self) -> None: ...


class SessionManagerError(ValueError):
    """A short error message that is safe to show to the user."""


@dataclass(frozen=True)
class SessionResult:
    action: str
    session_id: str
    title: str | None
    thread_id: str | None

    def message(self) -> str:
        title = self.title or t("untitled")
        thread_id = self.thread_id or t("no_thread")
        return t(
            f"result_{self.action}",
            session_id=self.session_id,
            title=title,
            thread_id=thread_id,
        )


def default_store_factory() -> SessionStore:
    """Open Hermes' own state API only when an action is invoked."""
    try:
        from hermes_state import SessionDB
    except ImportError as error:
        raise SessionManagerError(t("storage_unavailable")) from error
    return SessionDB()


class SessionManager:
    """Manage one Telegram session resolved by routing key or explicit ID."""

    def __init__(
        self, store_factory: Callable[[], SessionStore] = default_store_factory
    ):
        self._store_factory = store_factory

    def manage_current_telegram_session(
        self, session_key: str, action: str, *, confirm: bool = False
    ) -> SessionResult:
        if not session_key:
            raise SessionManagerError(t("current_context_unavailable"))
        store = self._store_factory()
        try:
            session = store.find_latest_gateway_session_for_peer(
                source="telegram", session_key=session_key
            )
            return self._manage(store, session, action, confirm=confirm)
        finally:
            store.close()

    def manage_session(
        self, session_id: str, action: str, *, confirm: bool = False
    ) -> SessionResult:
        if not session_id:
            raise SessionManagerError(t("session_id_required"))
        store = self._store_factory()
        try:
            return self._manage(
                store, store.get_session(session_id), action, confirm=confirm
            )
        finally:
            store.close()

    @staticmethod
    def _manage(
        store: SessionStore,
        session: dict[str, Any] | None,
        action: str,
        *,
        confirm: bool,
    ) -> SessionResult:
        if action not in {"archive", "delete"}:
            raise SessionManagerError(t("invalid_action"))
        if not session:
            raise SessionManagerError(t("session_not_found"))
        if str(session.get("source", "")).lower() != "telegram":
            raise SessionManagerError(t("non_telegram"))
        session_id = str(session.get("id") or "")
        if not session_id:
            raise SessionManagerError(t("missing_session_id"))
        if action == "archive":
            title = _optional_text(session.get("title"))
            if title and not session.get("archived"):
                archived_title = _archived_title(store, title)
                if not store.set_session_title(session_id, archived_title):
                    raise SessionManagerError(t("session_gone"))
                title = archived_title
            if not store.set_session_archived(session_id, True):
                raise SessionManagerError(t("session_gone"))
        else:
            if not confirm:
                raise SessionManagerError(t("delete_confirmation"))
            delete_targets = store.get_session_delete_targets(session_id)
            if delete_targets != [session_id]:
                raise SessionManagerError(t("delegate_children"))
            if not store.delete_session(
                session_id,
                sessions_dir=_sessions_dir(store),
                expected_delete_ids=delete_targets,
            ):
                raise SessionManagerError(t("session_gone"))
        return SessionResult(
            action=action,
            session_id=session_id,
            title=(
                title
                if action == "archive"
                else _optional_text(session.get("title"))
            ),
            thread_id=_optional_text(session.get("thread_id")),
        )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _archived_title(store: SessionStore, title: str) -> str:
    suffix = t("archive_title_suffix", date=date.today().isoformat())
    max_length = int(getattr(store, "MAX_TITLE_LENGTH", 100))
    return f"{title[: max_length - len(suffix)].rstrip()}{suffix}"


def _sessions_dir(store: SessionStore) -> Path | None:
    db_path = getattr(store, "db_path", None)
    if not db_path:
        return None
    return Path(db_path).parent / "sessions"
