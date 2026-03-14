# Dragon Team — Build Infrastructure + APNG Optimization

> **Agent:** Dragon Pipeline (Silver tier)
> **Territory:** Build scripts, APNG optimization, dist-mcc/
> **Phase:** 175.5-175.6
> **Trigger:** Opus dispatches via @dragon or mycelium_pipeline

---

## MISSION

Optimize the MCC build pipeline: reduce 110MB APNG avatar bundle to <20MB,
create lazy-loading infrastructure, verify build_mycelium.sh works end-to-end.

---

## TASK 1: APNG Optimization Script

**File:** `scripts/optimize_apng.sh` (NEW)

Current problem: 8 agent APNG avatars = 110MB total in dist-mcc/.
Target: <20MB with acceptable quality.

**Strategy:**
1. Convert APNG → WebP animated (saves ~60-70%)
2. Reduce frame count (many have 100+ frames, trim to 30-60)
3. Reduce resolution (many are 512x512, MCC shows at ~64x64 max)
4. Generate static PNG fallbacks for first-frame preview

**Commands:**
```bash
# For each APNG in client/src/assets/myco_motion/
ffmpeg -i input.apng -vf "scale=128:128" -loop 0 -quality 80 output.webp

# Static fallback
ffmpeg -i input.apng -frames:v 1 output_thumb.png
```

**Output:** `client/src/assets/myco_motion_optimized/` with both WebP and PNG fallbacks.

## TASK 2: Lazy-Loading Component

**File:** `client/src/components/mcc/LazyAvatar.tsx` (NEW — Dragon writes, Opus reviews)

```tsx
// Lazy-loads APNG/WebP avatar with static PNG placeholder
export function LazyAvatar({ role, size = 64 }: { role: string; size?: number }) {
  const [loaded, setLoaded] = useState(false);
  const staticSrc = `/assets/myco_motion/${role}_thumb.png`;
  const animatedSrc = `/assets/myco_motion_optimized/${role}.webp`;

  return (
    <img
      src={loaded ? animatedSrc : staticSrc}
      onLoad={() => setLoaded(true)}
      width={size} height={size}
      style={{ borderRadius: '50%' }}
    />
  );
}
```

## TASK 3: Build Script Verification

**File:** `scripts/build_mycelium.sh` (VERIFY — already exists)

Test all 3 modes:
```bash
./scripts/build_mycelium.sh frontend   # Browser-only on :3002
./scripts/build_mycelium.sh build      # Vite production build
# (Tauri build deferred — needs Rust toolchain)
```

Verify:
- dist-mcc/ created with correct files
- mycelium.html is the entry point
- No Three.js in JS bundle (grep)
- APNG assets are optimized versions

## TASK 4: Bundle Size Report

Generate report: `docs/175_MCC_APP/BUNDLE_REPORT.md`
```
JS bundle: X KB (gzip: Y KB)
CSS: X KB
Avatars (optimized): X MB
Total: X MB
Three.js references: 0
```

---

## SUCCESS CRITERIA

1. APNG avatars reduced from 110MB to <20MB
2. Static PNG fallbacks exist for all roles
3. LazyAvatar component created
4. build_mycelium.sh frontend mode works
5. Bundle report generated
