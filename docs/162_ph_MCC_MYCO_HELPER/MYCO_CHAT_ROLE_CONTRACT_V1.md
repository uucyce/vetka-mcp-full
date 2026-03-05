# MYCO Chat Role Contract V1

Status: `P0 CONTRACT`
Date: `2026-03-06`

Marker: `MARKER_162.MYCO.CHAT_ROLE_INJECTION.V1`

## Purpose
Встроить helper в текущий чат MCC без ломки architect role.

## Role ids
1. `architect` — как есть.
2. `helper_myco` — новый role id для гида.

## Injection rules
1. Mode `off`: MYCO messages forbidden.
2. Mode `passive`: MYCO отвечает только на явный триггер (`?`, help button, slash-command).
3. Mode `active`: MYCO может публиковать короткий hint при context change (rate-limited).

## Message shape
```json
{
  "role": "helper_myco",
  "type": "hint|explain|next_step|warning",
  "title": "string",
  "body": "string",
  "actions": [
    { "id": "open_context", "label": "open context" },
    { "id": "ask_architect", "label": "ask architect" }
  ],
  "source": "rules|llm"
}
```

## UX rules
1. MYCO max 3 short bullets per message.
2. Без красного тревожного тона в обычном guidance.
3. MYCO не перехватывает пользовательский prompt архитектору.

## Safety
1. MYCO cannot dispatch tasks.
2. MYCO cannot mutate workflow graph.
3. MYCO can only suggest actions.
