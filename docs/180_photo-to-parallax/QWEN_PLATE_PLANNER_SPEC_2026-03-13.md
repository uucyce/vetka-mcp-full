# Qwen Plate Planner Spec

Дата фиксации: `2026-03-13`

## Product Role

`Qwen2.5-VL` вводится не как:

- depth backend
- mask cutter
- inpaint engine

А как:

- `scene decomposition planner`
- `plate naming assistant`
- `near/far ordering assistant`
- `special clean plate suggester`

## Why This Layer Exists

Алгоритмический базис уже умеет:

- строить global depth
- строить B/W depth preview
- делать remap / isolate
- собирать base clean plate / overscan

Но complex scenes ломаются там, где нужна не просто глубина, а осмысленная композиционная раскладка:

- какие объекты должны жить в одном plate;
- сколько plate-ов вообще нужно;
- где нужен `no people`, `no trees` или другой special clean plate;
- какой порядок `near -> far` у plate-ов.

Это и есть роль `Qwen Plate Planner`.

## Input

- `source image`
- `depth_preview_bw.png`
- optional:
  - existing `plate_stack.json`
  - current layer exports
  - special clean plates
  - user note / intent

## Output

`Qwen` должен возвращать не prose, а JSON plan.

```json
{
  "sample_id": "97",
  "recommended_plate_count": 4,
  "plates": [
    {
      "id": "plate_01",
      "name": "fg_soldiers",
      "role": "foreground-subject",
      "depth_order": 1,
      "objects": ["two soldiers", "foreground debris"],
      "reason": "Strong foreground figures should travel together.",
      "needs_clean_plate": false,
      "suggested_clean_variant": null
    }
  ],
  "special_clean_plates": [
    {
      "name": "no_people",
      "reason": "Background architecture and ground need a clean reconstruction behind foreground soldiers."
    }
  ],
  "notes": [
    "Temple base and ruins should stay separate from far palms.",
    "Do not force all architecture into one background plate."
  ]
}
```

## Rules

`Qwen Plate Planner`:

- prefers `3-5` plates unless scene clearly needs more;
- groups semantically like a compositor, not like a segmentation model;
- describes meaningful parallax layers, not pixel masks;
- can suggest special clean plates;
- never directly edits final mask or final render.

## How It Sits In The Pipeline

Canonical layered flow:

1. `source`
2. `global depth`
3. `initial isolate / base mask`
4. `Qwen Plate Planner`
5. `plate stack proposal`
6. `plate extraction / cleanup`
7. `plate-local depth / z`
8. `camera layout`
9. `render`

## Safety Rule

`Qwen` suggestions are advisory.

They must pass through:

- planner JSON validation
- optional sanitizing gate
- user review or deterministic compare gate

`Qwen` must not directly overwrite:

- final mask
- final clean plate
- final layout

## Immediate Next Use

The first integration target is:

- build `qwen_plate_plan.json`
- show it in sandbox debug
- map proposed items to `plate_stack`

This keeps the current algorithmic basis intact while adding semantic planning on top.
