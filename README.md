# Hermes Session Manager

`hermes-plugin-session-manager` archives or deletes Telegram Hermes sessions. It
is designed for Hermes running in Docker or another managed runtime; the plugin
uses Hermes' in-process state API and does not require Hermes locally on the
development machine.

## Language

The plugin follows Hermes' process-wide language setting. Set
`display.language` in Hermes configuration, or use `HERMES_LANGUAGE` for a
process-level override. English and Russian plugin messages are bundled now;
unknown languages safely fall back to English. Command names and API fields
remain stable English identifiers: `/archive`, `/delete`, `session_id`, and
`confirm`.

## Behavior

In an idle Telegram chat or forum topic, send:

```text
/archive
```

The plugin resolves the exact active Telegram session for the gateway routing
key, appends ` - archived YYYY-MM-DD` to its title, and calls Hermes
`SessionDB.set_session_archived(session_id, True)`. Hermes performs a soft
archive: messages remain in `state.db`; no prune, delete, cron, subagent, or
routing mutation occurs. Repeating `/archive` is safe.

The response contains the `session_id`, title, and `thread_id`. `/archive` has
no arguments and never performs bulk archival.

To permanently delete only the current Telegram session:

```text
/delete confirm
```

Deletion removes the session, its messages, and the matching session transcript
files using Hermes' `SessionDB.delete_session()`. It requires the literal
confirmation argument and refuses to delete when Hermes reports delegate/subagent
children, so the plugin never deletes those sessions.

## CLI And AI

The CLI and AI tool require an explicit `session_id`; neither can infer a
"current" CLI, cron, or subagent session.

```bash
hermes session-manager archive --session-id <telegram-session-id>
hermes session-manager delete --session-id <telegram-session-id> --confirm
```

The agent receives the `manage_telegram_session` tool with `action`,
`session_id`, and optional `confirm`. For deletion it must pass
`confirm: true`. The tool accepts only persisted Telegram sessions.

## Safety Boundaries

- Telegram commands run only when Hermes reports `surface="gateway"` and
  `platform="telegram"`.
- It resolves by the gateway's exact `session_key`, never by topic title.
- It refuses a row whose persisted source is not `telegram`.
- If Hermes cannot provide command context, no session is modified.
- CLI and AI actions require an explicit session ID and refuse any non-Telegram
  row, including CLI, cron, and subagent sessions.
- Deletion requires explicit confirmation and refuses a delegate cascade.
- The current Hermes hook contract does not expose `chat_id` and `thread_id` to
  a slash-command handler. The plugin therefore uses the exact gateway routing
  key exposed by `pre_command`; this is the narrowest available identifier.

`pre_command` is not fired for a command intercepted while an agent is already
running. In that case `/archive` fails closed and reports that nothing was
archived. Stop the active run first, then send `/archive` again.

## Install

Publish the repository, then install it from inside the Hermes environment:

```bash
hermes plugins install <owner>/hermes-plugin-session-manager --enable --force
```

For local plugin development:

```bash
python3 -m pip install .
python3 -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

Restart the Hermes gateway after installation. In Docker, run the install and
restart commands in the same container/profile that runs the Telegram gateway.
Do not mount or edit `state.db` from a second container.

## Compatibility

The plugin targets Hermes versions that provide all of:

- `PluginContext.register_command()` with `fn(raw_args: str)`;
- the `pre_command` hook with `surface`, `platform`, and `session_key`;
- `hermes_state.SessionDB.find_latest_gateway_session_for_peer()`;
- `hermes_state.SessionDB.set_session_title()`;
- `hermes_state.SessionDB.set_session_archived()`.
- `hermes_state.SessionDB.get_session()`, `get_session_delete_targets()`, and
  `delete_session()`.

Those APIs are present in the Hermes Agent `main` branch inspected on 2026-08-23.
Pin and test against the Hermes image version used in production before rollout.

## License

[MIT](LICENSE)
