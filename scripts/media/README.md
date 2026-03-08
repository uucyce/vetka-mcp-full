# Media Tools

## mp4_to_apng_alpha

Path:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/media/mp4_to_apng_alpha.py`

Purpose:
- Convert MP4 to RGBA PNG sequence with alpha generation (`chroma` / `luma` / `depth`)
- Build APNG for MYCO/media-mode animation assets

Dependencies:
- Required: `ffmpeg`, `pillow`, `numpy`
- Optional (`--mode depth`): `torch`, `transformers`

Quick run (Codex / Claude Code / VETKA terminal):
```bash
python /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/media/mp4_to_apng_alpha.py \
  /path/input.mp4 \
  --output-dir /tmp/myco_anim_build \
  --output-apng /tmp/myco_anim.apng \
  --fps 8 \
  --mode chroma \
  --chroma-color 00ff00 \
  --chroma-threshold 60 \
  --chroma-softness 20
```

Depth run (alpha from depth map):
```bash
python /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/media/mp4_to_apng_alpha.py \
  /path/input.mp4 \
  --output-dir /tmp/myco_anim_build \
  --output-apng /tmp/myco_anim.apng \
  --fps 8 \
  --mode depth \
  --depth-model depth-anything/Depth-Anything-V2-Small-hf \
  --depth-threshold 128 \
  --depth-invert
```
