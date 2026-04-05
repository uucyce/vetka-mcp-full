# Architecture: Video Inspection Tool for AI

**Phase:** 197
**Status:** DRAFT
**Author:** Opus (Architect-Commander)
**Date:** 2026-03-20
**Task:** tb_1773971938_1

---

## 1. Problem Statement

AI-агенты (Claude, GPT-4o, Qwen) **не умеют смотреть видео**. Они принимают изображения. Когда агент получает mp4 — он беспомощен: не может оценить движение, пространство, артефакты рендера.

Человеку тоже неудобно: чтобы найти ghosting, cardboard-эффект или jitter в 10-секундном parallax-рендере, нужно смотреть покадрово.

**Нужен мост: Video -> набор лёгких артефактов, понятных и AI, и человеку.**

---

## 2. Core Insight: Depth Map as Universal Language

Ключевое решение, определяющее архитектуру:

> **Depth map одинаково полезен человеку и AI.**

RGB-кадр содержит текстуры, шум, освещение — AI тратит "внимание" на нерелевантное.
Depth map содержит только структуру: силуэты объектов, их взаимное расположение в пространстве, перспективу.

**Depth map — это "сжатие" видео до пространственной сути.**

| Свойство | RGB кадр | Depth map |
|----------|----------|-----------|
| Вес | ~200-500KB | ~30-80KB (grayscale) |
| Что видит AI | пиксели, текстуры, шум | силуэты, пространство, глубина |
| Объекты | надо "выделять" из фона | чёткие силуэты по контрасту яркости |
| Движение (при сравнении кадров) | смешано с текстурой | чистое смещение силуэтов |
| Окклюзия | неочевидна | явная (кто перед кем) |
| Стоимость | бесплатно (ffmpeg extract) | дорого (inference нейросети ~100ms/frame) |

### Depth estimation cost

Depth Anything V2 Small на Apple Silicon:
- ~10-15 fps inference
- 10 сек видео @ 25fps, каждый 5-й кадр = 50 кадров = **3-5 секунд**
- Приемлемо для инспекции. Progress bar снимает тревогу ожидания.

---

## 3. Two-Layer Architecture

```
                    VIDEO (mp4)
                        |
            +-----------+-----------+
            |                       |
      LAYER 1: RGB            LAYER 2: DEPTH
      (ffmpeg only)           (depth model + ffmpeg)
      ~instant                ~3-5 sec per 10s video
            |                       |
    +-------+-------+      +-------+-------+
    |       |       |      |       |       |
 contact  motion  meta   depth   depth   motion
 sheet    diff    data   contact  diff   energy
  .jpg    .jpg   .json   sheet   .jpg   heatmap
                          .jpg           .png
```

### Layer 1: RGB (быстрый, без зависимостей)

Только ffmpeg + Pillow. Работает мгновенно на любой машине.

| Артефакт | Что показывает | Для кого |
|----------|---------------|----------|
| `contact_sheet.jpg` | N кадров равномерно по таймлайну, с timestamps | AI: обзор сцены. Human: пэйсинг |
| `motion_diff.jpg` | Разница между соседними кадрами (абсолютный diff) | AI: где движение. Human: ghosting, smearing |
| `inspection.json` | Метаданные: fps, duration, resolution, crop, paths | Оба: программный доступ |

### Layer 2: Depth (дорогой, максимум информации)

Требует depth model (Depth Anything V2 / Apple DepthPro). Тяжелее, но даёт пространственное понимание.

| Артефакт | Что показывает | Для кого |
|----------|---------------|----------|
| `depth_contact_sheet.jpg` | Depth maps тех же кадров на одном листе | AI: 3D-структура сцены. Human: силуэты, перспектива |
| `depth_diff.jpg` | Изменение глубины между кадрами | AI+Human: disocclusion, cardboard-эффект, расслоение |
| `motion_energy.png` | Heatmap суммарного движения (mean абс. diff) | AI: одна картинка = "где было движение". Human: quick glance |

---

## 4. Output Structure

```
inspection_output/
  contact_sheet.jpg           # RGB: 8-16 кадров, timestamps         ~300KB
  motion_diff.jpg             # RGB: diff strip между кадрами         ~200KB
  depth_contact_sheet.jpg     # Depth: те же кадры как depth maps     ~150KB
  depth_diff.jpg              # Depth: изменение глубины              ~100KB
  motion_energy.png           # Heatmap суммарного движения            ~50KB
  inspection.json             # Метаданные + paths + settings          ~2KB
                              #                              TOTAL: ~800KB
```

**~800KB за полный анализ любого видео.** Влезает в один промпт к AI.

---

## 5. CLI Interface

```bash
# Минимальный запуск (только Layer 1)
python3 scripts/video_inspection_pack.py \
  --input /path/to/video.mp4 \
  --outdir /path/to/inspection

# Полный запуск (Layer 1 + Layer 2)
python3 scripts/video_inspection_pack.py \
  --input /path/to/video.mp4 \
  --outdir /path/to/inspection \
  --depth

# С параметрами
python3 scripts/video_inspection_pack.py \
  --input /path/to/video.mp4 \
  --outdir /path/to/inspection \
  --depth \
  --frames 12 \
  --columns 4 \
  --width 960 \
  --crop 120,200,640,360 \
  --depth-model depth-anything-v2
```

### CLI параметры

| Параметр | Default | Описание |
|----------|---------|----------|
| `--input` | required | Путь к mp4 |
| `--outdir` | required | Папка для результатов |
| `--depth` | false | Включить Layer 2 (depth analysis) |
| `--frames` | 8 | Количество кадров для contact sheet |
| `--columns` | 4 | Колонки в contact sheet |
| `--width` | 960 | Ширина output в пикселях |
| `--crop` | none | ROI: x,y,w,h — применяется ко всем outputs |
| `--depth-model` | depth-anything-v2 | Модель: `depth-anything-v2`, `depth-pro` |
| `--keyframes` | false | Вместо равномерных кадров — scene change detection |
| `--sample-rate` | 5 | Каждый N-й кадр для depth (1=каждый, 5=каждый пятый) |

---

## 6. Sampling Strategy

### Uniform (default)

Равномерные кадры по длительности. Простой, предсказуемый.

```
Video:  [============================]
Frames:  ^     ^     ^     ^     ^     ^     ^     ^
         0s   1.2s  2.5s  3.7s  5.0s  6.2s  7.5s  8.7s
```

### Keyframe detection (--keyframes)

ffmpeg scene change detection (`select='gt(scene,0.3)'`). Находит реальные переходы, а не равномерные точки. Полезно для CUT (монтажные склейки).

### Depth sample rate (--sample-rate N)

Для depth contact sheet: каждый N-й кадр из исходного видео.
- `--sample-rate 1` = каждый кадр (максимум информации, медленно)
- `--sample-rate 5` = каждый 5-й (5 depth maps в секунду при 25fps — хороший баланс)
- `--sample-rate 25` = 1 кадр/сек (быстро, грубо)

---

## 7. inspection.json Schema

```json
{
  "version": "1.0",
  "tool": "video_inspection_pack",
  "input": {
    "path": "/abs/path/video.mp4",
    "duration_sec": 10.5,
    "fps": 25.0,
    "frame_count": 262,
    "resolution": "1920x1080",
    "codec": "h264"
  },
  "settings": {
    "frames_sampled": 8,
    "columns": 4,
    "output_width": 960,
    "crop": "120,200,640,360",
    "sample_rate": 5,
    "depth_enabled": true,
    "depth_model": "depth-anything-v2",
    "keyframe_mode": false
  },
  "outputs": {
    "contact_sheet": "contact_sheet.jpg",
    "motion_diff": "motion_diff.jpg",
    "depth_contact_sheet": "depth_contact_sheet.jpg",
    "depth_diff": "depth_diff.jpg",
    "motion_energy": "motion_energy.png"
  },
  "timestamps_sampled": [0.0, 1.31, 2.62, 3.94, 5.25, 6.56, 7.87, 9.19],
  "depth_stats": {
    "model": "depth-anything-v2-small",
    "inference_time_sec": 4.2,
    "frames_processed": 50
  }
}
```

---

## 8. Dependencies

### Layer 1 (minimal)
- Python 3.10+
- ffmpeg + ffprobe (CLI, уже в системе)
- Pillow (pip, для sheet assembly + text overlay)

### Layer 2 (depth)
- torch + torchvision (для depth model inference)
- depth-anything-v2 weights (auto-download ~100MB)
- **OR** Apple DepthPro (CoreML, macOS only, faster)

### Никаких внешних API. Всё локально.

### Operational note

- shared depth runtime lives in `photo_parallax_playground/.depth-venv`
- bootstrap command: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_depth_bootstrap.sh`
- `video_inspection_pack.py --depth` now auto-reexecs into that venv, so the user can call plain `python3 ... --depth` without manually picking the interpreter
- if `.depth-venv` is missing or corrupted, rebuild it first instead of adding fallback polarity/runtime hacks into the tool

---

## 9. Integration Points

### 9.1 photo_to_parallax

Pipeline уже имеет 30+ QA-скриптов, но все domain-specific. Video inspection tool даёт:
- **Универсальный** анализ любого mp4 рендера
- **depth_diff** = прямая проверка cardboard-эффекта и disocclusion
- Можно встроить как post-render step в parallax pipeline

### 9.2 CUT (NLE)

- После PULSE auto-montage: contact sheet показывает пэйсинг нарезки
- `--keyframes` mode: проверка scene detection quality
- Depth contact sheet: проверка "рассказа пространством" (как меняется глубина от кадра к кадру)

### 9.3 AI Agent Workflow

Любой агент (Codex, Cursor, Dragon) может:
```
1. Рендер → mp4
2. video_inspection_pack --input render.mp4 --outdir inspection/ --depth
3. Прочитать inspection.json (метаданные)
4. Отправить contact_sheet.jpg + depth_contact_sheet.jpg в vision model
5. Получить структурированный анализ качества
```

**Это замыкает feedback loop: Agent -> Render -> Inspect -> Analyze -> Fix -> Render**

### 9.4 MCP Integration (future)

```
mcp__vetka__vetka_inspect_video
  --input: path
  --depth: bool
  → returns inspection.json + paths to artifacts
```

Агент вызывает одну MCP-команду и получает полный inspection pack.

---

## 10. What This Tool Does NOT Do

- **NOT** web UI (CLI only)
- **NOT** real-time processing (post-render inspection)
- **NOT** video editing or transcoding
- **NOT** cloud/API calls (всё локально)
- **NOT** замена domain-specific QA в photo_to_parallax (дополняет, не заменяет)
- **NOT** GIF generation (убрано как бесполезное для AI)

---

## 11. Implementation Phases

| Phase | Scope | Effort |
|-------|-------|--------|
| **197.2** | Layer 1: contact_sheet + motion_diff + inspection.json (ffmpeg + Pillow only) | ~2h |
| **197.3** | Layer 2: depth_contact_sheet + depth_diff + motion_energy (depth model integration) | ~3h |
| **197.4** | Advanced: --keyframes mode, --crop ROI, progress bar | ~1.5h |
| **197.5** | Integration: MCP tool wrapper, photo_to_parallax hook | ~2h |
| **197.6** | Tests + docs | ~1h |

---

## 12. File Map

```
scripts/
  video_inspection_pack.py        # Main CLI tool (~200 lines)
  video_inspection_depth.py       # Depth model wrapper (~80 lines)

docs/197ph_tool_analize_video_forAI/
  ARCHITECTURE_VIDEO_INSPECTION_TOOL.md   # This file
  ROADMAP_197.md                          # Roadmap (next)

tests/
  test_video_inspection_pack.py   # Contract tests
```

---

## 13. Summary

**Video Inspection Tool** = адаптер "видео -> язык AI".

Двухслойная архитектура:
- **Layer 1** (RGB, быстрый): contact sheet + motion diff — "что происходит?"
- **Layer 2** (Depth, тяжёлый): depth contact sheet + depth diff — "как устроено пространство?"

~800KB на полный анализ любого видео. Работает локально, без API. Полезен и человеку, и AI одинаково. Depth map — единственное представление, которое работает для обоих аудиторий без компромиссов.
