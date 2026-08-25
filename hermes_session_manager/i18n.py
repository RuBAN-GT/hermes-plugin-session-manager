"""Plugin messages aligned with Hermes' active language selection."""

from __future__ import annotations

from typing import Any

_MESSAGES = {
    "en": {
        "result_archive": "Archived session {session_id} (title: {title}; thread_id: {thread_id}).",
        "archive_title_suffix": " - archived {date}",
        "result_delete": "Deleted session {session_id} (title: {title}; thread_id: {thread_id}).",
        "storage_unavailable": "Hermes session storage is unavailable.",
        "current_context_unavailable": "Current session context is unavailable.",
        "session_id_required": "session_id is required.",
        "cli_partial_failure": "Failed to process {failed} of {total} sessions.",
        "invalid_action": "action must be archive or delete.",
        "session_not_found": "Session not found.",
        "unsupported_source": "Refusing to manage a session from an unsupported source.",
        "missing_session_id": "Current session has no session ID.",
        "session_gone": "Current session no longer exists.",
        "delete_confirmation": "Deletion requires confirm=true.",
        "delegate_children": "Refusing deletion because the session has delegate children.",
        "telegram_only": "/{command} is available only in a Telegram chat or the Hermes CLI.",
        "current_action_failed_archive": "Could not archive the current session.",
        "current_action_failed_delete": "Could not delete the current session.",
        "usage_archive": "Usage: /archive",
        "usage_delete": "Usage: /delete confirm",
        "nothing_changed_archive": "Current session context is unavailable; nothing was archived.",
        "nothing_changed_delete": "Current session context is unavailable; nothing was deleted.",
        "untitled": "untitled",
        "no_thread": "none",
    },
    "ru": {
        "result_archive": "Сессия {session_id} архивирована (название: {title}; thread_id: {thread_id}).",
        "archive_title_suffix": " - архив {date}",
        "result_delete": "Сессия {session_id} удалена (название: {title}; thread_id: {thread_id}).",
        "storage_unavailable": "Хранилище сессий Hermes недоступно.",
        "current_context_unavailable": "Контекст текущей сессии недоступен.",
        "session_id_required": "Нужен session_id.",
        "cli_partial_failure": "Не удалось обработать {failed} из {total} сессий.",
        "invalid_action": "action должен быть archive или delete.",
        "session_not_found": "Сессия не найдена.",
        "unsupported_source": "Управление сессией с этим источником запрещено.",
        "missing_session_id": "У текущей сессии нет session ID.",
        "session_gone": "Текущая сессия больше не существует.",
        "delete_confirmation": "Для удаления требуется confirm=true.",
        "delegate_children": "Удаление отклонено: у сессии есть delegate-потомки.",
        "telegram_only": "/{command} доступна только в Telegram-чате или в Hermes CLI.",
        "current_action_failed_archive": "Не удалось архивировать текущую сессию.",
        "current_action_failed_delete": "Не удалось удалить текущую сессию.",
        "usage_archive": "Использование: /archive",
        "usage_delete": "Использование: /delete confirm",
        "nothing_changed_archive": "Контекст текущей сессии недоступен; архивирование не выполнено.",
        "nothing_changed_delete": "Контекст текущей сессии недоступен; удаление не выполнено.",
        "untitled": "без названия",
        "no_thread": "нет",
    },
}


def t(key: str, **values: Any) -> str:
    """Translate a plugin message using Hermes' process-wide language setting."""
    language = _language()
    template = _MESSAGES.get(language, _MESSAGES["en"]).get(key)
    if template is None:
        template = _MESSAGES["en"][key]
    return template.format(**values)


def _language() -> str:
    try:
        from agent.i18n import get_language

        return get_language()
    except Exception:
        return "en"
