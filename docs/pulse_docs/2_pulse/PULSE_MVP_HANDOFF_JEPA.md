# Pulse MVP Handoff (Low-Token Mode)

Date: 2026-02-28

## 1) Что уже готово для MVP
- Stable pipeline: `deterministic -> JEPA rerank -> commit policy`.
- Feedback loop: `Like/Dislike/Skip -> JSONL -> ENGRAM profile`.
- Spectral features for JEPA context: `bpmStability + chroma12 + onset + noteDensity`.
- UI split: performance/dev + UI v3 hand-only + note matrix (fallback v2 сохранен).
- One-shot quality gate: `npm run quality:gate`.

## 2) Команды для самостоятельной работы (без Codex)

From:
`/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/pulse`

```bash
# 1) Build corpus/manifests from local datasets
npm run jepa:prepare
npm run jepa:eval-subset -- --target-size 300

# 2) Verify all JEPA artifacts
npm run jepa:verify

# 3) Build ENGRAM profile from feedback log
npm run jepa:engram:build

# 4) Offline A/B benchmark (deterministic vs deterministic+JEPA)
npm run bench:scale:ab:offline

# 5) Full MVP gate (tests + build + verify + bench + md/csv report)
npm run quality:gate
```

## 3) Как добавить свои любимые треки для дообучения
1. Положи аудио/миди в один из dataset-id каталогов:
   - `pulse/data/datasets/gtzan`
   - `pulse/data/datasets/maestro`
   - или через `--import-local` в `fetch_jepa_datasets.sh`.
2. Рядом добавь labels файл (`.csv`/`.json`/`.jsonl`/`.tsv`/`.txt`) с полями:
   - `path` или `filename` (идентификатор файла),
   - `bpm` (или `tempo`),
   - `key`,
   - `scale` (или `mode`).
3. Пересобери:
```bash
npm run jepa:prepare
npm run jepa:verify
```

## 4) Минимальный CSV формат labels
```csv
path,bpm,key,scale
my_track_01.wav,124,8A,Dorian
my_track_02.wav,140,9B,Mixolydian
```

## 5) Release/консервация MVP
```bash
npm run quality:gate
npm run tauri build
```
Если `quality:gate` = `pass`, можно фиксировать MVP как baseline.

