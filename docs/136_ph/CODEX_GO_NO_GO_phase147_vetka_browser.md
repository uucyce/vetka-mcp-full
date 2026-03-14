# CODEX GO/NO-GO: VETKA Browser Wave (Phase 147)

Date: 2026-02-13  
Scope: `browser_GROK.txt` + текущая реализация VETKA Web Shell (Tauri + React + FastAPI)

## TL;DR
- GO: `single reusable Tauri web shell`, `viewport-aware save`, `contextual retrieval`, `fast web preview + save HTML/MD`.
- CONDITIONAL GO: `Mycelium-driven fetch/parse/enrich` как async pipeline за браузером.
- NO-GO (на этом этапе): `full browser clone` (extensions/password vault/cookies migration/2FA import) без отдельной security-архитектуры.

---

## MARKER_147.GO_NOW
## GO NOW (делаем в ближайших итерациях)

1. Single-window browser shell (already in progress)
- Открывать всегда одно окно `vetka-web-shell`, при новом результате выполнять navigate.
- Запретить авто-дубли окон и авто-fallback в отдельные external окна.

2. Save flow 2-step + viewport default path
- Step 1: имя + формат (HTML/MD).
- Step 2: путь сохранения с автоприоритетом ближайшего viewport node.
- Сохранение в VETKA + на диск в directed mode (единый артефактный контракт).

3. Контекстный поиск всегда с viewport
- Для `web/file` всегда передавать `viewport_context`, делать rerank по proximity + semantic relevance.
- При отсутствии части сигналов graceful fallback без поломки поиска.

4. UX скорость и читаемость
- Убрать лишние кнопки/бейджи, сохранить Nolan/Batman black style.
- Сделать надёжный address navigation (domain/url/query normalization + suggestions/history).

---

## MARKER_147.GO_CONDITIONAL
## CONDITIONAL GO (после короткого исследования и прототипа)

1. Mycelium Parse/Fetch Pipeline for Web
- Идея: browser shell отвечает за просмотр/навигацию, Mycelium-воркеры за асинхронный fetch, extraction, dedupe, chunking, embeddings, graph-anchoring.
- Почему: убираем тяжёлую логику из UI и получаем масштабируемый ingestion.
- Условие запуска: определить SLA и лимиты (таймауты, размер HTML, частота, quota).

2. Multi-provider web retrieval (Tavily + fallback providers)
- Не завязывать качество только на Tavily.
- Ввести provider adapter + health + RRF merge.
- Условие запуска: минимальный контракт нормализации полей и scoring.

3. Smart Save Suggestions
- Помимо viewport-path, предлагать semantic-nearest node + recent workspace node.
- Условие запуска: не ломать deterministic default (первый всегда viewport-nearest).

---

## MARKER_147.NO_GO_NOW
## NO-GO NOW (не делаем сейчас, слишком риск/сложно/неокупаемо)

1. Полный импорт паролей/cookies/2FA в VETKA
- Высокие security/compliance риски.
- Большая вероятность platform-specific нестабильности и регрессий UX.

2. Поддержка “extensions как у Chrome”
- WebView не равно полноценному Chromium-browser runtime.
- Огромная цена поддержки, мало пользы для core ценности VETKA.

3. “Full browser replacement” в одном релизе
- Сломает фокус: нужно сначала добить стабильность universal search + shell + save + context pipeline.

---

## MARKER_147.ARCH_DECISIONS
## Архитектурные решения (предлагаемый target)

1. Разделить роли
- Shell (Tauri + React): UI/навигация/ручные действия пользователя.
- Retrieval (FastAPI): search providers, ranking, capabilities.
- Mycelium (async): heavy parsing/enrichment/indexing.

2. Единый Web Artifact Contract
- `url`, `title`, `captured_at`, `format(md|html)`, `raw_html_path`, `markdown_path`, `summary`, `source_provider`, `viewport_anchor_path`, `semantic_anchor_path`, `hash`.

3. Event-first orchestration
- UI action -> emit event (`web.opened`, `web.saved`, `web.index.requested`).
- Mycelium consumers подписываются и обрабатывают без блокировки UI.

4. Deterministic default + smart assist
- Default всегда понятен пользователю (nearest viewport node).
- Smart suggestions добавляются как вторичные, а не подменяют default.

---

## MARKER_147.QUESTIONS_CRITICAL
## Критичные вопросы, которые нужно решить (до крупной перестройки)

1. Что является source of truth для web-страницы?
- Raw HTML, sanitized HTML, markdown, или комбинация?

2. Какая политика перезаписи?
- Повторный save той же URL: новая версия, merge в существующий артефакт или dedupe по hash?

3. Какой SLA у preview и save?
- Максимальный таймаут, размер документа, лимит редиректов, JS-heavy сайтов.

4. Где граница между shell и backend?
- Что делается синхронно в UI, а что всегда уходит в async Mycelium job.

5. Как считаем “nearest viewport node” формально?
- Только расстояние камеры, или pinned + center + semantic score c весами?

6. Нужен ли multi-tab в shell сейчас?
- Если да, то минимальный вариант: tab-strip с 3-5 вкладками без усложнения session manager.

7. Как валидируем качество web search?
- Набор gold queries + offline regression suite (precision@k, latency, save success rate).

8. Security boundary
- Какие данные из web допускается хранить постоянно.
- Нужно ли шифрование отдельных артефактов/метаданных на диске.

---

## MARKER_147.RESEARCH_BACKLOG
## Исследования (параллельно можно запускать)

1. WebView capability matrix (macOS/Windows/Linux)
- Ограничения iframe/srcdoc/navigation/find/cookies/storage.

2. Provider benchmark
- Tavily vs fallback providers на вашем query-set + стоимость + latency + failure modes.

3. Mycelium web-ingestion prototype
- POC пайплайн: fetch -> extract -> summarize -> embed -> anchor.
- Метрики: end-to-end latency и hit quality в последующем поиске.

4. Save destination ranking study
- Сравнить текущий viewport-nearest с гибридной моделью (viewport + semantic + recency).

---

## MARKER_147.IMPLEMENTATION_SEQUENCE
## Рекомендуемая последовательность внедрения

1. Stabilize shell (window reuse, find, save path reset, no dup windows).
2. Harden save contract (VETKA + disk consistency, versioning rules).
3. Enable Mycelium async enrichment behind save/index events.
4. Add multi-provider retrieval + health/routing.
5. Add benchmark harness + regression gates.

---

## MARKER_147.SUCCESS_CRITERIA
## Критерии успеха

1. Один клик по web-result => одно окно shell, без дублей.
2. Переход на новый result переиспользует текущее окно < 300ms UI reaction.
3. Save step2 всегда имеет валидный default path из viewport.
4. Save success rate > 95% на тестовом наборе URL.
5. Контекстный поиск web/file показывает измеримый прирост релевантности vs baseline.

