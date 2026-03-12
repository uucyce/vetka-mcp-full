# PHASE 168 — MYCO Motion Asset Pipeline Recon

Date: 2026-03-09
Protocol stage: RECON+markers -> REPORT -> WAIT GO
Scope: MYCO role motion assets, MP4 -> APNG pipeline, MCC-specific UI review path

Related docs:
- `docs/168_ph_videoplayer/MARKER_168_VIDEO_PLAYER_LAB_PLAN_2026-03-08.md`
- `docs/168_ph_videoplayer/MARKER_168_VIDEO_PLAYER_LAB_RECON_2026-03-08.md`
- `docs/167_MCC_workflow/PHASE_167_EXTENDED_STATS_WORKFLOW_PANEL_ROADMAP_2026-03-08.md`

## 1. Goal

Build a repeatable MYCO role-asset pipeline that:

- converts role MP4 assets into transparent APNG safely,
- proves geometry/fit before MCC integration,
- introduces a separate MCC-specific probe for compact runtime surfaces,
- can later be reused as a general `dev UI` tool for Codex, VETKA, and MCC.

## 2. Source Inventory

Motion asset source directory:
- `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4`

Static role icon directory:
- `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A`

Current files:
- `arch1.mp4`
- `arch1-2.mp4`
- `coder1.mp4`
- `coder2.mp4`
- `researcher1.mp4`
- `scout.mp4`
- `scout2.mp4`
- `scout3.mp4`
- `verif1.mp4`

## 3. Proven Media Facts

`ffprobe` baseline:

- all files run at `24fps`
- all files are about `5.041667s`
- all files have `121` frames
- most files are `828x1108`
- `researcher1.mp4` is `960x960`

This is a strong baseline because:
- animation duration is already normalized,
- frame rate is already normalized,
- `architect` parts are concat-friendly,
- one role family (`researcher`) clearly needs a square handling branch.

## 4. Alpha Extraction Decision

Decision: use `luma`, not `chroma`, as the default extraction mode.

Reason:
- MYCO assets are white-on-black,
- background is effectively dark enough that brightness thresholding is the correct semantic split,
- `chroma` against black is possible but less robust than luminance-based separation for this asset family.

Baseline preset confirmed from first successful run:
- `mode = luma`
- `fps = 8`
- `luma-threshold = 52`
- `alpha-blur = 0.8`

Example successful conversion already proven on:
- `coder2.mp4`

Example command:
```bash
python /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/media/mp4_to_apng_alpha.py \
  /Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4/coder2.mp4 \
  --output-dir /tmp/myco_coder2_build \
  --output-apng /tmp/myco_coder2.apng \
  --fps 8 \
  --mode luma \
  --luma-threshold 52 \
  --alpha-blur 0.8
```

## 5. Architect Assembly

Architect consists of two source clips:
- `arch1.mp4`
- `arch1-2.mp4`

Working assumption:
- these are sequential phases of one architect motion, not parallel overlays.

Recommended assembly order:
1. concatenate into one master MP4,
2. then convert that master into APNG,
3. then run geometry probe,
4. then run MCC-specific probe later.

Safe ffmpeg recipe (re-encode path, not stream-copy):

Create concat list:
```bash
cat > /tmp/myco_arch_concat.txt <<'TXT'
file '/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4/arch1.mp4'
file '/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4/arch1-2.mp4'
TXT
```

Assemble master clip:
```bash
ffmpeg -y -f concat -safe 0 -i /tmp/myco_arch_concat.txt \
  -vf fps=24 \
  -c:v libx264 -pix_fmt yuv420p \
  /tmp/myco_arch_master.mp4
```

Then convert assembled master:
```bash
python /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/media/mp4_to_apng_alpha.py \
  /tmp/myco_arch_master.mp4 \
  --output-dir /tmp/myco_arch_build \
  --output-apng /tmp/myco_arch.apng \
  --fps 8 \
  --mode luma \
  --luma-threshold 52 \
  --alpha-blur 0.8
```

## 6. Existing Review Tool: What It Proves

Existing probe:
- `scripts/player_lab_review.sh`
- `player_playground/e2e/dream_player_probe.spec.ts`

What it already proves well:
- rendered media fits into container,
- aspect ratio is preserved,
- letterbox is measured,
- chrome ratio is measured,
- a reproducible screenshot + JSON snapshot are produced.

What it does **not** prove yet:
- behavior inside MCC compact panels,
- visual noise near DAG,
- animation dominance inside `MiniChat` or role-selector surfaces,
- trigger correctness for role-state changes.

Conclusion:
- current probe is valid as `Stage 1: asset geometry QA`,
- it must not be treated as final MCC runtime verification.

## 7. MCC-Specific Probe: Required Next Tool

Need a second probe layer dedicated to MYCO role assets inside MCC surfaces.

Target surfaces:
- top MYCO helper bubble/icon
- `MiniChat`
- compact task/workflow context surfaces
- possible future role picker / workflow roster view

Probe questions:
- does APNG fit the assigned role slot without clipping?
- does the animation dominate the panel too much?
- is text still readable next to the asset?
- does trigger switching create layout jitter?
- do multiple simultaneous roles (`coder`, `scout`) remain visually separable?

Recommended outputs:
- screenshot set by surface,
- JSON metrics per surface,
- trigger-state matrix,
- pass/fail notes for readability and motion intensity.

## 8. Proposed Marker Set

Add later during implementation:
- `MARKER_168.MYCO.MOTION.PIPELINE.RECON.V1`
- `MARKER_168.MYCO.MOTION.LUMA_PRESET.V1`
- `MARKER_168.MYCO.MOTION.ARCHITECT_CONCAT.V1`
- `MARKER_168.MYCO.MOTION.ASSET_PROBE.V1`
- `MARKER_168.MYCO.MOTION.MCC_PROBE.V1`
- `MARKER_168.MYCO.MOTION.DEV_UI_TOOL.V1`

## 9. Delivery Order

1. Freeze baseline luma preset.
2. Build architect master clip.
3. Batch-convert all role MP4 assets to APNG.
4. Keep player-lab probe as asset QA gate.
5. Build separate MCC-specific MYCO probe.
6. Wire trigger matrix only after both QA gates pass.
7. Promote the probe stack into shared `dev UI` tooling.

## 10. Risk Notes

- `researcher1.mp4` is square and must not be forced into portrait assumptions.
- two coders and multiple scouts need trigger arbitration rules before runtime wiring.
- APNG size can become expensive if fps is too high or alpha cleanup is noisy.
- direct integration into MCC before the second probe exists would be premature.
