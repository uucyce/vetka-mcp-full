# Pavel AE Reference Workflow

Дата фиксации: `2026-03-13`

## Что было разобрано

Пакет:

- `/Users/danilagulin/Downloads/camera motion folder/camera motion.aep`
- `/Users/danilagulin/Downloads/camera motion folder/camera motionReport.txt`
- `/Users/danilagulin/Downloads/camera motion folder/renders/*`
- `/Users/danilagulin/Downloads/camera motion folder/screen timeline/*`

## Ключевой вывод

Референсный workflow Паши это не:

- `single depth map -> одна маска -> foreground/background`

А это:

- `single source -> осознанная декомпозиция сцены на plate-ы -> отдельные clean plates -> depth-aware camera layout -> AE camera move`

То есть основная сила результата не в одной глубинной карте, а в ручной смысловой раскладке сцены.

## Что видно по проекту

### Scene 3

- исходник `3-2x.png`
- отдельные plate-ы:
  - `3_layer 1.png`
  - `3_layer 2.png`
  - `3_layer 3.png`
  - `3_layer 4.png`
  - `3_layer 5.png`
  - `3_layer 6.png`

### Scene 54

- исходник `54-2x.png`
- отдельные plate-ы:
  - `54_layer 1.png`
  - `54_layer 2.png`
  - `54_layer 3.png`

### Scene 96

- исходник `96.jpg`
- отдельный background plate:
  - `96_bckgrnd.jpg`
- depth map:
  - `96_depth_map.png`
- отдельные plate-ы:
  - `96_layer 2.png`
  - `96_layer 3.png`
  - `96_layer 4.png`
  - `96_layer 5.png`

### Scene 97

- исходник `97.jpg`
- full image / upscale:
  - `97-2x.png`
- global depth:
  - `97-2x_depth_map.png`
- object plates:
  - `97_layer 1.png`
  - `97_layer 2.png`
  - `97_layer 3.png`
- special clean plates:
  - `97_layer no people.png`
  - `97_layer no trees.png`
- отдельные depth maps для специальных plate-ов:
  - `97_layer no people_depth_map.png`
  - `97_layer no trees_depth_map.png`

## Что это значит для нашего продукта

### 1. Текущий base workflow не отменяется

Он уже годится для:

- portrait
- simple object
- mild parallax

Canonical base path:

- `source -> depth -> B/W depth preview -> remap -> isolate -> clean plate -> overscan -> render`

### 2. Но multi-part scene требует другой модели

Для сложных сцен depth не должен пытаться магически заменить layout artist.

Нужна следующая сущность продукта:

- `plate`

`plate` это не просто маска, а самостоятельный объект сцены:

- `rgba`
- `clean plate` behind it
- `local depth map` или depth priority
- `z position`
- optional semantic label

### 3. Рабочая модель следующего этапа

Новый pipeline для сложных сцен:

1. `source`
2. `global depth`
3. `plate decomposition`
4. `plate-local cleanup`
5. `plate-local depth / z assignment`
6. `camera motion`
7. `export`

## Новый продуктовый тезис

`Depth map` остаётся главным входом в систему.

Но для сложной сцены итоговая структура должна быть:

- не `1 global mask`,
- а `N semantically meaningful plates`.

Практическое правило:

- `portrait mode` может жить на `1-2 layer baseline`;
- `complex scene mode` должен жить на `multi-plate authoring`.

## Что автоматизируем дальше

Не “идеальную универсальную одну depth map”, а:

- автоматический старт с global depth;
- semi-automatic decomposition в plate-ы;
- plate-specific background repair;
- plate-specific z/depth placement;
- deterministic camera/render поверх этой сцены.
