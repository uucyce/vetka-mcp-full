# Stage 1 Recon – Candidate Prioritization

## Goal
Сравнить предложенные проекты с точки зрения их близости к архитектуре и сценариям VETKA Media Mode (media-edit + AI-driven montage). Рассматриваем стек (Rust/React/Tauri), готовность к Apple Silicon, узловые системы и способность ускорить разработку нового монтажного потока.

## Кандидаты
| Название | Технологический профиль | Узловая композиция (Premiere-style) | Apple Silicon / GPU | Почему подходит для VETKA | Источник |
| --- | --- | --- | --- | --- | --- |
| **Olive Video Editor** | C++ / Qt / FFmpeg (не Rust, но проверенный Linux/macOS NLE) | Нодовый композитор вместо слоёв, высокая гибкость для эффектов и colour workflows | Нативно поддерживает Apple Silicon + GPU (FFmpeg/Metal paths) | Ближе всех к классическому Premiere/Final Cut: сложный timeline, node-based pipelines и высокая производительность — отличный референс UX и структуру сцены | citeturn0search3turn0search8 |
| **SixSevenStudio** | Tauri v2 + React + Rust + Vite + ffmpeg | Нет явного node-редактора, но фокус на storyboard + scripted AI shots | заявлена Apple Silicon поддержка (нативный Mac build) | Полная совпадение по стеку; уже интегрирует AI-процессы (Sora), хранит материалы локально и умеет делать базовые нарезки и переходы, поэтому быстро изучается командой VETKA | citeturn0search0 |
| **NolanForge** | (по описанию) Tauri + Rust + React | Должен быть лёгким редактором с быстрой нарезкой/записью, но публичных ресурсов пока нет | (предположительно) Apple Silicon (по упору на Tauri + lightweight UX) | Может служить минимальным proof-of-concept для UI-модулей (drag‑drop, trim, record) и стимулом для быстрой сборки прототипа на нашем стеке: пригодится, если нужно иллюстрировать Tauri-модель | — |
| **Cap (CapSoftware)** | Tauri + Rust + React / Solid + Next.js | Не монтаж, а окно записи/аннотации, без node-графа | Полностью кроссплатформенный, фокус на Windows/macOS (Rust+Tauri) | Демонстрирует зрелую обработку видео/видео-сообщений на стеке VETKA, плюс пример интеграции записи + редактирования превью; полезен как референс платформенной инфраструктуры | citeturn2search0turn2search7 |

## Приоритеты для VETKA media mode
1. **Olive** – главный шаблон node-based UX и прототип для профессионального интерфейса (соответствует `media_chunks_v1`, `scene_node_id`, `timeline_lane` и CAM/PULSE vision). Несмотря на C++, его архитектуру можно зафиксировать и затем транслировать в Tauri-код, чтобы сохранить терминологию `scene graph` и `timeline alignment` из Stage 1 документа.
2. **SixSevenStudio** – технически наиболее близок к стеку VETKA (Rust/Tauri/React) и уже работает с AI-ассистентом (Sora). Его storyboard+AI pipeline перекликается с `media/startup` (MCP_MEDIA) и `fallback_questions`, поэтому его можно быстро изучить и заимствовать решения для UI + ingest.
3. **Cap** – зрелое Tauri-приложение с доступной архитектурой под запись/превью; можно изучить для стабильных потоков dump → upload, которые нужны для `media_preview` и `media/rhythm-assist` (локальный capture, proxy плейбэк, telemetry). Использовать как reference implementation платформенного слоя (self-hosted, plugin-ready).
4. **NolanForge** – когда понадобится показать быстрый прототип на нашем стеке (drag-drop, trimmer). На данный момент публичных деталей по проекту нет, поэтому сначала лучше собрать подробности от команды, а затем внедрять элементы UI/Shortcuts.

## Как это накладывается на сценарии VETKA
- **Node + Timeline readiness (Olive)**: есть node-based compositing, GPU-ускорение, возможность подключать effects graph → вдохновляет архитектуру `media_edit_mode` (P5.4 lanes, CAM overlays, semantic links). Можно взять идеи drag/drop, connection semantics и apply them to React/Tauri `ArtifactPanel` lanes.
- **AI storyboard / fallback workflow (SixSevenStudio)**: отслеживание AI‑сценариев, Sora-интеграция и local storage позволит быстрее описать `Jarvis guided fallback loop`, `media/startup` quick scan и `missing_inputs` (Sora prompts ~ `fallback_questions`).
- **Capture + UX stability (Cap)**: demonstrates cross-platform telemetry, local recording, and preview pipelines, aligned with budget requirements from `VETKA_MEDIA_PIPELINE_BUDGETS_V1`. Could inform `media_preview` streaming and degrade-safe flows.

## Предложения для next step в Stage 1
1. **Автоматизировать сравнение Olive → VETKA UX**: выделить key screens (node editor, timelines) и сопоставить с `ArtifactPanel`/`media_edit_mode`. Технически можно собрать flowcharts, а затем запланировать node graph translation в React Flow + MCP_DATA.
2. **Изучить SixSevenStudio**: клонировать репо, задеплоить local dev server (Tauri + ffmpeg + AI). Забрать UI/UX паттерны (storyboard cards, fallback modals, local file storage) и оценить, какие компоненты можно reuse.
3. **Знакомство с Cap инфраструктурой**: изучить как устроен capture → editing pipeline, систему хранения, сборку Tauri (monorepo). Может ускорить `media_preview`, `cam_bridge` и `rhythm_assist` (proxy energy tracks) через более устойчивую платформу.
4. **Собрать данные по NolanForge**: запросить URL/код, чтобы подтвердить, насколько проект реализован и закрыт. Если нет репо, попросить команду описать, что он делает, и какие траектории можно вытащить.

## Источники
- Olive node-based compositor, cross-platform performance, Apple Silicon readiness: GitFounders research + recent node system article citeturn0search3turn0search8
- SixSevenStudio (Tauri v2 + React + Rust + Sora AI storyboards): official GitHub README citeturn0search0
- Cap (Rust + React/Next + Tauri Loom alternative) plus project analysis article citeturn2search0turn2search7
