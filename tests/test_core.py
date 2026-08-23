from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

from hermes_session_manager.core import SessionManager, SessionManagerError
from hermes_session_manager.i18n import t


class FakeStore:
    def __init__(self, session, archive_result=True, delete_result=True, targets=None):
        self.session = session
        self.archive_result = archive_result
        self.delete_result = delete_result
        self.targets = (
            targets if targets is not None else [session["id"]] if session else []
        )
        self.archived = []
        self.titles = []
        self.deleted = []
        self.closed = False

    def find_latest_gateway_session_for_peer(self, *, source, session_key):
        self.source = source
        self.session_key = session_key
        return self.session

    def get_session(self, session_id):
        self.requested_session_id = session_id
        return self.session

    def set_session_archived(self, session_id, archived):
        self.archived.append((session_id, archived))
        return self.archive_result

    def set_session_title(self, session_id, title):
        self.titles.append((session_id, title))
        return True

    def get_session_delete_targets(self, session_id):
        self.delete_target_request = session_id
        return self.targets

    def delete_session(self, session_id, *, sessions_dir=None, expected_delete_ids):
        self.deleted.append((session_id, sessions_dir, expected_delete_ids))
        return self.delete_result

    def close(self):
        self.closed = True


class SessionManagerTests(unittest.TestCase):
    @patch("hermes_session_manager.core.date")
    def test_archives_exact_telegram_session_and_renames_it(self, mock_date):
        mock_date.today.return_value = date(2026, 8, 23)
        store = FakeStore(
            {
                "id": "session-1",
                "source": "telegram",
                "title": "Topic",
                "thread_id": "42",
            }
        )

        result = SessionManager(lambda: store).manage_current_telegram_session(
            "key-1", "archive"
        )

        self.assertEqual(store.source, "telegram")
        self.assertEqual(store.session_key, "key-1")
        self.assertEqual(
            store.titles, [("session-1", "Topic - archived 2026-08-23")]
        )
        self.assertEqual(store.archived, [("session-1", True)])
        self.assertTrue(store.closed)
        self.assertEqual(
            result.message(),
            "Archived session session-1 "
            "(title: Topic - archived 2026-08-23; thread_id: 42).",
        )

    @patch("hermes_session_manager.core.date")
    def test_archive_keeps_titles_within_hermes_limit(self, mock_date):
        mock_date.today.return_value = date(2026, 8, 23)
        title = "x" * 100
        store = FakeStore(
            {"id": "session-1", "source": "telegram", "title": title}
        )

        SessionManager(lambda: store).manage_session("session-1", "archive")

        self.assertEqual(
            store.titles,
            [("session-1", "x" * 78 + " - archived 2026-08-23")],
        )

    def test_repeated_archive_does_not_rename_an_archived_session(self):
        store = FakeStore(
            {
                "id": "session-1",
                "source": "telegram",
                "title": "Topic - archived 2026-08-23",
                "archived": True,
            }
        )

        SessionManager(lambda: store).manage_session("session-1", "archive")

        self.assertEqual(store.titles, [])

    @patch("hermes_session_manager.i18n._language", return_value="ru")
    def test_messages_use_the_hermes_language(self, _language):
        self.assertEqual(t("usage_archive"), "Использование: /archive")
        self.assertEqual(
            t("result_delete", session_id="s-1", title="Тема", thread_id="42"),
            "Сессия s-1 удалена (название: Тема; thread_id: 42).",
        )

    def test_deletion_requires_confirmation_and_never_cascades_to_delegates(self):
        session = {"id": "session-1", "source": "telegram"}
        with self.assertRaisesRegex(SessionManagerError, "confirm"):
            SessionManager(lambda: FakeStore(session)).manage_session(
                "session-1", "delete"
            )
        store = FakeStore(session, targets=["session-1", "delegate-1"])

        with self.assertRaisesRegex(SessionManagerError, "delegate children"):
            SessionManager(lambda: store).manage_session(
                "session-1", "delete", confirm=True
            )

        self.assertEqual(store.deleted, [])
        self.assertTrue(store.closed)

    def test_deletes_one_explicit_telegram_session(self):
        store = FakeStore({"id": "session-1", "source": "telegram"})

        result = SessionManager(lambda: store).manage_session(
            "session-1", "delete", confirm=True
        )

        self.assertEqual(store.requested_session_id, "session-1")
        self.assertEqual(store.deleted, [("session-1", None, ["session-1"])])
        self.assertEqual(result.action, "delete")

    def test_rejects_empty_context_and_non_telegram_session(self):
        with self.assertRaisesRegex(SessionManagerError, "context"):
            SessionManager(lambda: FakeStore(None)).manage_current_telegram_session(
                "", "archive"
            )
        store = FakeStore({"id": "cli-1", "source": "cli"})
        with self.assertRaisesRegex(SessionManagerError, "non-Telegram"):
            SessionManager(lambda: store).manage_session("cli-1", "archive")
        self.assertEqual(store.archived, [])


if __name__ == "__main__":
    unittest.main()
