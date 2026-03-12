MARKER_171A.MYCO.FIRST_AID.ERROR_INDEX.MATRIX.V1
LAYER: L3
DOMAIN: UI|SEARCH|SCANNER|ARTIFACT|VOICE|AGENTS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_171A_MYCO_FIRST_AID_ERROR_INDEX_AND_SCENARIO_MATRIX_2026-03-11.md
LAST_VERIFIED: 2026-03-11

# Phase 171.A MYCO First Aid Error Index And Scenario Matrix

## Synopsis
This document proposes the normalized MYCO first-aid index for VETKA.

Goal:
- one shared language for scenario writers;
- one error taxonomy for backend, UI, MYCO, and tests;
- concrete recovery hints that help the user get unstuck.

## Table of Contents
1. Index rules
2. Taxonomy
3. Scenario matrix
4. Escalation policy
5. Silence policy
6. Cross-links
7. Status matrix

## Treatment
The taxonomy is intentionally deterministic.
Every entry should answer:
1. what the user sees
2. what signal exists today
3. what MYCO should say
4. when to escalate

## Short Narrative
Users do not need raw stack traces. They need a short, accurate diagnosis and the next viable move. The index below keeps those moves concrete: add a key, retry with a better query, reload the backend, open chat, pin the file, reconnect the provider, or call `@doctor` when the problem is beyond ordinary UI recovery.

## Full Spec
### Index Rules
1. Prefer normalized codes over raw text.
2. Separate user-fixable from operator-fixable states.
3. Keep advice proportional to certainty.
4. Suggest `@doctor` only after one useful local recovery path.
5. If the signal does not exist yet in code, mark the row as `Planned`.

### Taxonomy
#### Core/product
- `CORE.COLD_START.NO_KEYS`
- `CORE.SOCKET.DISCONNECTED`
- `CORE.SOCKET.CONNECT_ERROR`
- `CORE.STREAM.ERROR`

#### Search/web
- `SEARCH.QUERY.TOO_SHORT`
- `WEB.PROVIDER.KEY_MISSING`
- `WEB.PROVIDER.AUTH_ERROR`
- `WEB.PROVIDER.BILLING_OR_QUOTA`
- `WEB.PROVIDER.RATE_LIMITED`
- `WEB.PROVIDER.TIMEOUT`
- `WEB.PROVIDER.DOWN_OR_EMPTY`
- `WEB.RESULT.CAP_REACHED`
- `WEB.PAGINATION.NOT_AVAILABLE`

#### Keys
- `KEY.INPUT.EMPTY`
- `KEY.TYPE.UNKNOWN`
- `KEY.SAVE.ERROR`

#### Connectors/scanner
- `CONNECTOR.OAUTH_CLIENT.MISSING`
- `CONNECTOR.AUTH.REQUIRED`
- `CONNECTOR.TOKEN.EXPIRED_OR_MISSING`
- `CONNECTOR.TREE.UNAVAILABLE`
- `CONNECTOR.SCAN.FAILED`
- `CONNECTOR.SOURCE.PLACEHOLDER`

#### Files/artifacts/media
- `FILE.NOT_FOUND`
- `FILE.PERMISSION_DENIED`
- `FILE.PATH_IS_DIRECTORY`
- `ARTIFACT.PATH.MISSING`
- `ARTIFACT.WEB_SAVE.FAILED`
- `MEDIA.PATH.MISSING`
- `MEDIA.TYPE.UNSUPPORTED`
- `MEDIA.PLAYBACK.DEGRADED`
- `MEDIA.METADATA.UNAVAILABLE`

#### Voice
- `VOICE.NO_AUDIO`
- `VOICE.TRANSCRIPTION.TIMEOUT`
- `VOICE.APIKEY_OR_STT.EMPTY`

#### Collaboration/escalation
- `GROUP.NOT_FOUND`
- `DOCTOR.ESCALATION.AVAILABLE`

### Scenario Matrix
| TAG | Normalized code | User-visible symptom | Existing signal today | MYCO short first aid | Next best steps | Escalation | Status |
|---|---|---|---|---|---|---|---|
| `TAG:MYCO.FIRST_AID.COLD_START.NO_KEYS` | `CORE.COLD_START.NO_KEYS` | user opened VETKA and nothing useful runs yet | key inventory bridge in MYCO docs and runtime corpus | `Сначала оживим VETKA. Открой phonebook и добавь LLM key. Для web/ потом понадобится Tavily.` | open phonebook, add model key, then add Tavily if web search is needed | no | Implemented in MYCO rules |
| `TAG:MYCO.FIRST_AID.SEARCH.QUERY_SHORT` | `SEARCH.QUERY.TOO_SHORT` | search returns too short | `src/api/handlers/unified_search.py:251`-`259` | `Запрос слишком короткий. Добавь еще одно слово.` | expand query, keep typing, MYCO stays quiet while typing | no | Implemented |
| `TAG:MYCO.FIRST_AID.WEB.KEY_MISSING` | `WEB.PROVIDER.KEY_MISSING` | `web/` has no provider | `src/mcp/tools/web_search_tool.py:67`-`73` | `У web/ нет Tavily key. В едином окне выбери web/ и вбей "tavily api key free". Я всегда рад помочь.` | stay inside VETKA, find key, add it in keys flow | no | Implemented in MYCO copy, backend still string-based |
| `TAG:MYCO.FIRST_AID.WEB.AUTH` | `WEB.PROVIDER.AUTH_ERROR` | invalid provider key | MYCO search error category already classifies auth in current frontend layer | `Ключ web/ не принят провайдером. Нужен новый рабочий key.` | replace key, check provider account | if repeated after key replacement, `@doctor` | Partial |
| `TAG:MYCO.FIRST_AID.WEB.BILLING` | `WEB.PROVIDER.BILLING_OR_QUOTA` | provider says quota/billing exhausted | current MYCO error category supports billing/quota | `У web/ закончился лимит или баланс. Пополни ключ или временно перейди в vetka/file.` | top up provider, swap key, use non-web search temporarily | `@doctor` only if business owner needs routing advice | Partial |
| `TAG:MYCO.FIRST_AID.WEB.RATE_LIMIT` | `WEB.PROVIDER.RATE_LIMITED` | provider throttles requests | current MYCO error category supports rate-limit | `Провайдер web/ временно ограничил запросы. Подожди и повтори или уточни запрос позже.` | cooldown, retry later, switch source | no | Partial |
| `TAG:MYCO.FIRST_AID.WEB.TIMEOUT` | `WEB.PROVIDER.TIMEOUT` | web search hangs or times out | current MYCO error category supports timeout; provider code still stringly | `Web provider не ответил вовремя.` | retry once, narrow query, if internet is unstable check connection, VPN, or router | if repeated across sources, `@doctor` | Partial |
| `TAG:MYCO.FIRST_AID.WEB.CAP` | `WEB.RESULT.CAP_REACHED` | user sees only top part of web results | [PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md](./PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md) | `Сейчас web/ показывает только верхний блок результатов.` | refine query, browse narrower topic, wait for real pagination | no | Planned |
| `TAG:MYCO.FIRST_AID.CORE.SOCKET_DISCONNECT` | `CORE.SOCKET.DISCONNECTED` | tree/chat stops updating | `client/src/hooks/useSocket.ts:822`-`825` | `Связь с VETKA backend прервалась.` | reload once, check backend on `:5001`, then check local network if other sources also fail | `@doctor` if reconnect fails | Planned for MYCO |
| `TAG:MYCO.FIRST_AID.CORE.CONNECT_ERROR` | `CORE.SOCKET.CONNECT_ERROR` | app opens but does not connect | `client/src/hooks/useSocket.ts:827`-`830` | `Не удалось подключиться к runtime.` | check backend process, reload app, then check VPN/network only if provider paths also fail | `@doctor` if startup path is unclear | Planned |
| `TAG:MYCO.FIRST_AID.KEY.EMPTY` | `KEY.INPUT.EMPTY` | user tried to save blank key | `src/api/handlers/key_handlers.py:51`-`55` | `Ключ пустой. Вставь полный ключ целиком.` | paste full key, avoid spaces or line breaks | no | Planned |
| `TAG:MYCO.FIRST_AID.KEY.UNKNOWN` | `KEY.TYPE.UNKNOWN` | key not recognized automatically | `src/api/handlers/key_handlers.py:93`-`108` | `Я не узнал этот ключ. Укажи, к какому сервису он относится.` | learn provider manually, then save | `@doctor` only if provider is exotic and flow is broken | Planned |
| `TAG:MYCO.FIRST_AID.CONNECTOR.OAUTH_CLIENT` | `CONNECTOR.OAUTH_CLIENT.MISSING` | user clicks Auth and gets missing OAuth credentials | `src/api/routes/connectors_routes.py:149`-`157` | `У этого коннектора не заведены client id и secret на стороне VETKA.` | ask operator to add OAuth app credentials, then repeat Auth | yes, operator or `@doctor` | Partial, runtime-proven |
| `TAG:MYCO.FIRST_AID.CONNECTOR.AUTH_REQUIRED` | `CONNECTOR.AUTH.REQUIRED` | connector exists but is not authorized | `src/api/routes/connectors_routes.py:194`-`201`, `client/src/components/scanner/ScanPanel.tsx:1487`-`1495` | `Сначала авторизуй источник, потом запускай scan.` | click Auth, complete provider flow | no | Partial |
| `TAG:MYCO.FIRST_AID.CONNECTOR.EXPIRED` | `CONNECTOR.TOKEN.EXPIRED_OR_MISSING` | connector card shows expired or token missing | `client/src/components/scanner/ScanPanel.tsx:1463`-`1469` | `Токен источника просрочен или отсутствует.` | reconnect provider, then retry scan | `@doctor` if token keeps disappearing | Partial |
| `TAG:MYCO.FIRST_AID.CONNECTOR.TREE` | `CONNECTOR.TREE.UNAVAILABLE` | Browse or tree preview fails | `client/src/components/scanner/ScanPanel.tsx:547`-`560` | `Предпросмотр дерева сейчас недоступен.` | retry browse, use scan without tree if allowed, reconnect provider | `@doctor` if provider should support tree but never does | Partial |
| `TAG:MYCO.FIRST_AID.CONNECTOR.SCAN` | `CONNECTOR.SCAN.FAILED` | scan or disconnect action fails | `client/src/components/scanner/ScanPanel.tsx:522`-`538` | `Scan не завершился.` | retry once, check auth status, narrow selection | `@doctor` if repeated after reconnect | Partial |
| `TAG:MYCO.FIRST_AID.CONNECTOR.PLACEHOLDER` | `CONNECTOR.SOURCE.PLACEHOLDER` | browser or social pane looks present but source is not fully live | prior 163.A+ recon docs | `Этот источник еще не доведен как полноценный ingest path.` | switch to `web/`, `file/`, or live connector | no | Partial |
| `TAG:MYCO.FIRST_AID.FILE.NOT_FOUND` | `FILE.NOT_FOUND` | opened file path no longer exists | `src/api/routes/files_routes.py:199`-`200`, `241`-`245` | `Файл не найден по этому пути.` | reselect node, search file again, verify file still exists | `@doctor` if tree points to dead paths repeatedly | Planned |
| `TAG:MYCO.FIRST_AID.FILE.PERMISSION` | `FILE.PERMISSION_DENIED` | file opens or saves with permission denied | `src/api/routes/files_routes.py:169`-`172`, `216`-`219` | `У VETKA нет прав на этот файл.` | change file permissions, move file into accessible area, try artifact copy path | `@doctor` if permission model is unclear | Planned |
| `TAG:MYCO.FIRST_AID.ARTIFACT.PATH` | `ARTIFACT.PATH.MISSING` | detached artifact opens with empty path | `client/src/ArtifactStandalone.tsx:61` | `Артефакт открыт без пути.` | reopen artifact from tree or chat, do not trust stale detached link | no | Planned |
| `TAG:MYCO.FIRST_AID.ARTIFACT.WEB_SAVE` | `ARTIFACT.WEB_SAVE.FAILED` | Save to VETKA fails from web artifact | `client/src/WebShellStandalone.tsx:430`-`450`, `client/src/components/artifact/ArtifactPanel.tsx:1008`-`1027` | `Сохранение страницы не завершилось.` | retry once, check URL validity, if repeated wait for artifact runtime stabilization | `@doctor` after repeated failure | Partial |
| `TAG:MYCO.FIRST_AID.MEDIA.PATH` | `MEDIA.PATH.MISSING` | detached media window opens empty | `client/src/ArtifactMediaStandalone.tsx:73` | `Медиа открыто без пути.` | reopen media from artifact or tree | no | Planned |
| `TAG:MYCO.FIRST_AID.MEDIA.TYPE` | `MEDIA.TYPE.UNSUPPORTED` | media route rejects file type | `src/api/routes/artifact_routes.py:1290`-`1294` | `Этот тип медиа сейчас не поддержан.` | convert file, open as raw file, or inspect outside media player | `@doctor` if support is expected by product contract | Planned |
| `TAG:MYCO.FIRST_AID.MEDIA.PLAYBACK` | `MEDIA.PLAYBACK.DEGRADED` | video player falls back or metadata unavailable | `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:615`-`620`, `client/src/utils/detachedMediaDebug.ts:130`-`140` | `Плеер не смог стабильно открыть текущий вариант медиа.` | retry embedded mode, switch to full quality, reopen window | `@doctor` if repeated across files | Partial |
| `TAG:MYCO.FIRST_AID.VOICE.NO_AUDIO` | `VOICE.NO_AUDIO` | microphone flow started but no audio delivered | `src/api/handlers/voice_socket_handler.py:120`-`159` | `Я не получил аудио.` | check mic permission, retry capture, confirm microphone device | no | Planned |
| `TAG:MYCO.FIRST_AID.VOICE.TIMEOUT` | `VOICE.TRANSCRIPTION.TIMEOUT` | voice transcription times out | `client/src/hooks/useSocket.ts:2517`-`2525` | `Распознавание голоса заняло слишком долго.` | retry shorter utterance, check provider keys, check connection | `@doctor` if voice is consistently broken | Partial |
| `TAG:MYCO.FIRST_AID.DOCTOR` | `DOCTOR.ESCALATION.AVAILABLE` | user is stuck after one or two failed local remedies | `src/agents/agentic_tools.py:135`-`167`, `src/api/handlers/group_message_handler.py:597`-`739` | `Если хочешь, позови @doctor. Он разберет тупик и предложит маршрут.` | send `@doctor` with symptom and what already failed | yes | Implemented |

### Escalation Policy
Use `@doctor` when:
1. more than one surface fails at once
2. the problem is likely operator-side, not user-side
3. the same recovery was already tried once
4. the user is blocked from progressing

Do not escalate first when:
1. a key is simply missing
2. a query is too short
3. the user has not tried the obvious local control yet

### Silence Policy
MYCO should stay quiet when:
1. user is still typing the recovery input
2. the same first-aid code already fired for the same state signature
3. a retry is already in progress
4. the surface is healthy again

## Cross-links
See also:
- [PHASE_171A_MYCO_FIRST_AID_RECON_REPORT_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_RECON_REPORT_2026-03-11.md)
- [PHASE_171A_MYCO_FIRST_AID_ROADMAP_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_ROADMAP_2026-03-11.md)
- [PHASE_171A_MYCO_FIRST_AID_SCENARIO_WRITER_LOG_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_SCENARIO_WRITER_LOG_2026-03-11.md)
- [PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md](./PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md)

## Status Matrix
| Slice | Status | Evidence |
|---|---|---|
| Web first-aid rows | Partial | `src/api/handlers/unified_search.py:182`; `src/mcp/tools/web_search_tool.py:55` |
| Socket/product rows | Planned | `client/src/hooks/useSocket.ts:815`; `client/src/hooks/useSocket.ts:1938` |
| Connector rows | Partial | `src/api/routes/connectors_routes.py:126`; `client/src/components/scanner/ScanPanel.tsx:508` |
| Artifact/media rows | Partial | `src/api/handlers/artifact_routes.py:156`; `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:615` |
| Voice rows | Partial | `src/api/handlers/voice_socket_handler.py:120`; `client/src/hooks/useSocket.ts:2517` |
| `@doctor` escalation row | Implemented | `src/agents/agentic_tools.py:135`; `src/api/handlers/group_message_handler.py:597` |
