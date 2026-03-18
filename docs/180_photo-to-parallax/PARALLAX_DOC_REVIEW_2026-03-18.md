# Parallax Doc Review

Дата ревизии: `2026-03-18`

## 1. Goal

Зафиксировать, какие документы остаются актуальными, какие являются историческими, и какие должны использоваться как source of truth для release-выполнения.

## 2. Keep as Source of Truth

- `PARALLAX_ARCHITECTURE_RELEASE_V1_2026-03-18.md`
  основной operational architecture doc для release work.
- `HANDOFF_PHASE_180_2026-03-14.md`
  краткий continuity/handoff документ.
- `PHOTO_TO_PARALLAX_ROADMAP_CHECKLIST_2026-03-10.md`
  полный research backlog.
- `PHOTO_TO_PARALLAX_ARCHITECTURE_V1_2026-03-10.md`
  historical architecture baseline.
- `photo_parallax_playground/CONTRACTS_V1.md`
  contract freeze.

## 3. Keep as Historical Research Evidence

Следующие документы не являются текущим execution plan, но должны сохраняться как evidence:

- depth/mask/inpaint bakeoff reports;
- manual pro and algorithmic matte reports;
- plate-aware layout/export/render reports;
- qwen planner/gate/multiplate compare reports;
- UI recon and AE reference workflow notes.

Практическое правило:

- эти документы использовать как evidence/reference;
- не использовать их как primary planning document.

## 4. Observed Drift

### Drift A. Architecture vs handoff

`PHOTO_TO_PARALLAX_ARCHITECTURE_V1_2026-03-10.md` был написан до части release-решений:

- anti-flake export diagnostics;
- camera-safe suggestion;
- contract freeze;
- release-track split.

### Drift B. Roadmap vs release-v1

`PHOTO_TO_PARALLAX_ROADMAP_CHECKLIST_2026-03-10.md` шире release-v1 и включает:

- research continuation;
- luxury track;
- long-tail enhancements.

Поэтому roadmap нельзя напрямую считать release backlog.

### Drift C. TaskBoard vs actual code

Предыдущие задачи `parallax` в TaskBoard больше не читаются по `task_id`.
Это значит:

- старый `parallax` backlog нельзя считать надёжным;
- backlog нужно пересобрать как fresh release/recon workset.

## 5. Recommended Planning Rules

- Планирование release-v1 вести от `PARALLAX_ARCHITECTURE_RELEASE_V1_2026-03-18.md`.
- Техническую continuity вести через `HANDOFF_PHASE_180_2026-03-14.md`.
- Полный research scope сверять по `PHOTO_TO_PARALLAX_ROADMAP_CHECKLIST_2026-03-10.md`.
- Contract changes сначала отражать в `CONTRACTS_V1.md`.

## 6. Tasking Recommendation

Новый backlog должен иметь 3 группы:

- `release`
- `refactor`
- `recon`

Рекомендуемые parallel recon tracks:

- recon doc/task drift audit;
- recon `Qwen-Image-Layered` fit for layered decomposition.

## 7. Current Backlog Mapping

Актуальный `parallax` backlog должен читаться так:

- `recon`
  - document/task drift audit
  - `Qwen-Image-Layered` fit review
- `release`
  - contract freeze
  - export anti-flake + QA summary
  - final render presets
  - regression quality pack
  - RC1 packaging/runbook/smoke
- `refactor`
  - extract release-critical services from `App.tsx`

Правило исполнения:

- `recon` идёт параллельно, но не блокирует release-v1;
- `release` определяет ближайший критический путь;
- `refactor` делается так, чтобы не ломать release behavior.

## 8. Final Planning Rule

При любом новом чате по parallax:

- сначала открыть `PARALLAX_ARCHITECTURE_RELEASE_V1_2026-03-18.md`;
- затем `PARALLAX_DOC_REVIEW_2026-03-18.md`;
- после этого брать задачи только из fresh `parallax` backlog, а не из старых `task_id`.
