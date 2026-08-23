"""Plugin messages aligned with Hermes' active language selection."""

from __future__ import annotations

from typing import Any

_MESSAGES = {
    "en": {
        "result_archive": "Archived session {session_id} (title: {title}; thread_id: {thread_id}).",
        "result_delete": "Deleted session {session_id} (title: {title}; thread_id: {thread_id}).",
        "storage_unavailable": "Hermes session storage is unavailable.",
        "current_context_unavailable": "Current Telegram session context is unavailable.",
        "session_id_required": "session_id is required.",
        "invalid_action": "action must be archive or delete.",
        "session_not_found": "No active Telegram session was found for this chat.",
        "non_telegram": "Refusing to manage a non-Telegram session.",
        "missing_session_id": "Current Telegram session has no session ID.",
        "session_gone": "Current Telegram session no longer exists.",
        "delete_confirmation": "Deletion requires confirm=true.",
        "delegate_children": "Refusing deletion because the session has delegate children.",
        "telegram_only": "/{command} is available only in a Telegram chat.",
        "current_action_failed_archive": "Could not archive the current Telegram session.",
        "current_action_failed_delete": "Could not delete the current Telegram session.",
        "usage_archive": "Usage: /archive",
        "usage_delete": "Usage: /delete confirm",
        "nothing_changed_archive": "Current Telegram session context is unavailable; nothing was archived.",
        "nothing_changed_delete": "Current Telegram session context is unavailable; nothing was deleted.",
        "untitled": "untitled",
        "no_thread": "none",
    },
    "ru": {
        "result_archive": "Сессия {session_id} архивирована (название: {title}; thread_id: {thread_id}).",
        "result_delete": "Сессия {session_id} удалена (название: {title}; thread_id: {thread_id}).",
        "storage_unavailable": "Хранилище сессий Hermes недоступно.",
        "current_context_unavailable": "Контекст текущей Telegram-сессии недоступен.",
        "session_id_required": "Нужен session_id.",
        "invalid_action": "action должен быть archive или delete.",
        "session_not_found": "Для этого чата не найдена активная Telegram-сессия.",
        "non_telegram": "Управление не-Telegram сессией запрещено.",
        "missing_session_id": "У текущей Telegram-сессии нет session ID.",
        "session_gone": "Текущая Telegram-сессия больше не существует.",
        "delete_confirmation": "Для удаления требуется confirm=true.",
        "delegate_children": "Удаление отклонено: у сессии есть delegate-потомки.",
        "telegram_only": "/{command} доступна только в Telegram-чате.",
        "current_action_failed_archive": "Не удалось архивировать текущую Telegram-сессию.",
        "current_action_failed_delete": "Не удалось удалить текущую Telegram-сессию.",
        "usage_archive": "Использование: /archive",
        "usage_delete": "Использование: /delete confirm",
        "nothing_changed_archive": "Контекст текущей Telegram-сессии недоступен; архивирование не выполнено.",
        "nothing_changed_delete": "Контекст текущей Telegram-сессии недоступен; удаление не выполнено.",
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
