# Experience Report: Beta (Media/Color Pipeline Architect)
**Date:** 2026-03-29
**Agent:** SONNET-BETA | Branch: claude/cut-media
**Tasks closed:** tb_1774689673_97753_1 (generation routes), tb_1774755549_97753_1 (mixer backend)

---

## Q6: Идеи не по теме

**1. MixerStateStore → timeline state разрыв (критический).**
`set_track_volume/pan/mute/solo` timeline ops синкают в `MixerStateStore` при записи. Но при загрузке проекта из JSON — обратного пути нет. `GET /project-state` возвращает `state["mixer"]`, но `MixerStateStore` остаётся пустым до первого PATCH/POST запроса. Нужен `_hydrate_mixer_from_timeline(project_id, timeline_state)` — вызов при каждом `GET /project-state` и при bootstrap. Без этого WebSocket metering после рестарта сервера даёт неверные effective levels.

**2. mixer_levels_request — FFmpeg per-lane per-frame.**
Текущая реализация: каждый `mixer_levels_request` запускает FFmpeg для каждого source в `sources[]`. На 24-track timeline при 30fps polling = 720 FFmpeg вызовов/сек. Решение: audio_scope_request уже имеет per-source RMS ring buffer в памяти — mixer_levels_request должен читать из него, а не запускать новые процессы. Mixer state (volume/mute) применяется математически поверх кешированных значений. Latency: 5ms → 0.1ms.

**3. Task ID dispatch проблема.**
Командир дал ID `tb_1773996025_9` — он оказался `done_main` (фронтенд задача от 23 марта). Правильный таск `tb_1774755549_97753_1` нашёлся через overlap warning при попытке создать дублирующий. Правило для Командира: перед dispatch всегда `action=get task_id=X` чтобы подтвердить `status=pending`.

**4. Rebase doc-drop паттерн.**
Два rebase подряд удалили `RECON_FCP7_DELTA2_CH41_115_2026-03-20.md` и `RECON_CLAUDE_MD_GIT_TRACKING_ROOT_CAUSE_2026-03-28.md`. DOC_GUARD ловит это, но требует ручного `git checkout main -- <file>`. Идея: pre-rebase hook который автоматически делает `git stash` для файлов из `docs/` перед rebase и `git stash pop` после — docs никогда не дропаются при rebase конфликтах.
