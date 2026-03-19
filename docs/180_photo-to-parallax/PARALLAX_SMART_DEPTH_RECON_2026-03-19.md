# Parallax Smart Depth Recon

Дата: `2026-03-19`

## Scope

Цель этого recon-документа: зафиксировать только подтверждённые факты про `smart depth` / `depth-first` path и его расхождение с `plate export / render` path.

В документ не включены:

- предположения о том, что именно пользователь видел визуально `2026-03-15`, если это не зафиксировано в repo;
- гипотезы о качестве рендера;
- реконструкция по памяти без файлового или git-подтверждения.

## Confirmed Timeline

### `2026-03-12`: real depth base документирован

Подтверждено в [REAL_DEPTH_BASELINE_RESULTS_2026-03-12.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/REAL_DEPTH_BASELINE_RESULTS_2026-03-12.md#L1):

- sandbox должен уметь показывать настоящий `B/W depth preview`, а не только proxy-depth;
- в `App.tsx` подключён baked depth preview;
- для `Base` зафиксирована polarity:
  - `white = near`
  - `black = far`
- `buildProxyMaps(...)` строит depth/remap от baked raster, если он доступен;
- `window.vetkaParallaxLab.getState()` расширен полями `previewMode` и `usingRealDepth`;
- `Closer / Farther` strokes уже работают как `depth correction layer`;
- `DaVinci-like Base` в явном виде описан как:
  - `depth map`
  - `B/W preview`
  - `near/far/gamma`
  - `white = closer`
  - `black = farther`

Ключевые строки:

- [REAL_DEPTH_BASELINE_RESULTS_2026-03-12.md:7](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/REAL_DEPTH_BASELINE_RESULTS_2026-03-12.md#L7)
- [REAL_DEPTH_BASELINE_RESULTS_2026-03-12.md:13](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/REAL_DEPTH_BASELINE_RESULTS_2026-03-12.md#L13)
- [REAL_DEPTH_BASELINE_RESULTS_2026-03-12.md:53](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/REAL_DEPTH_BASELINE_RESULTS_2026-03-12.md#L53)
- [REAL_DEPTH_BASELINE_RESULTS_2026-03-12.md:88](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/REAL_DEPTH_BASELINE_RESULTS_2026-03-12.md#L88)

### `2026-03-12`: depth-first UI policy тоже документирован

Подтверждено в [UI_RECON_AND_MONOCHROME_REDESIGN_2026-03-12.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/UI_RECON_AND_MONOCHROME_REDESIGN_2026-03-12.md#L1):

- целевой UI policy назван `depth-first workflow`;
- research tools должны быть hidden behind debug;
- полезные части, которые нужно сохранить:
  - real B/W depth preview
  - DaVinci-like remap controls
  - stage-centered preview
  - debug pane for internal metrics

Ключевые строки:

- [UI_RECON_AND_MONOCHROME_REDESIGN_2026-03-12.md:5](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/UI_RECON_AND_MONOCHROME_REDESIGN_2026-03-12.md#L5)
- [UI_RECON_AND_MONOCHROME_REDESIGN_2026-03-12.md:72](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/UI_RECON_AND_MONOCHROME_REDESIGN_2026-03-12.md#L72)

### `2026-03-13`: preview/export pipeline переходит на plate assets, но сами plate ещё synthetic

Подтверждено в [PLATE_RGBA_COMPOSITION_RESULTS_2026-03-13.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PLATE_RGBA_COMPOSITION_RESULTS_2026-03-13.md#L1):

- preview переведён на `backgroundRgbaUrl + plateRgbaUrls[]`;
- `buildPlateCompositeMaps(...)` собирает RGBA plate assets из `source image + alpha masks`;
- документ прямо фиксирует ограничение:
  - это ещё не `plate-local clean plate`
  - это ещё не `independent plate source file`
  - это ещё не `AE-level authored plate`

Ключевые строки:

- [PLATE_RGBA_COMPOSITION_RESULTS_2026-03-13.md:16](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PLATE_RGBA_COMPOSITION_RESULTS_2026-03-13.md#L16)
- [PLATE_RGBA_COMPOSITION_RESULTS_2026-03-13.md:54](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PLATE_RGBA_COMPOSITION_RESULTS_2026-03-13.md#L54)

Подтверждено в [PLATE_EXPORT_CONTRACT_RESULTS_2026-03-13.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PLATE_EXPORT_CONTRACT_RESULTS_2026-03-13.md#L1):

- `exportPlateAssets()` возвращает `globalDepthUrl`, `backgroundRgbaUrl`, `plates[].rgbaUrl/maskUrl/depthUrl`;
- документ прямо фиксирует ограничение:
  - `rgbaUrl` и `depthUrl` синтезируются внутри sandbox из `source image + plate alpha + global depth`

Ключевые строки:

- [PLATE_EXPORT_CONTRACT_RESULTS_2026-03-13.md:11](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PLATE_EXPORT_CONTRACT_RESULTS_2026-03-13.md#L11)
- [PLATE_EXPORT_CONTRACT_RESULTS_2026-03-13.md:50](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PLATE_EXPORT_CONTRACT_RESULTS_2026-03-13.md#L50)

Подтверждено в [PLATE_EXPORT_FILES_RESULTS_2026-03-13.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PLATE_EXPORT_FILES_RESULTS_2026-03-13.md#L1):

- file/export flow сохраняет `global_depth_bw.png`, `background_rgba.png`, `plate_01_rgba.png`, `plate_01_depth.png`, `plate_stack.json`, `plate_layout.json`, `plate_export_manifest.json`;
- документ прямо фиксирует ограничение:
  - `plate_depth` derived from current global depth + plate alpha
  - не independent local depth solve

Ключевые строки:

- [PLATE_EXPORT_FILES_RESULTS_2026-03-13.md:17](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PLATE_EXPORT_FILES_RESULTS_2026-03-13.md#L17)
- [PLATE_EXPORT_FILES_RESULTS_2026-03-13.md:68](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PLATE_EXPORT_FILES_RESULTS_2026-03-13.md#L68)

### `2026-03-15`: в repo подтверждён только stability update, не отдельный smart-depth milestone doc

Подтверждено в [HANDOFF_PHASE_180_2026-03-14.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/HANDOFF_PHASE_180_2026-03-14.md#L102):

- есть section `Статус обновление (2026-03-15, truck-driver stability check)`;
- там зафиксирован `10/10` success на уровне gated export wrapper;
- там же есть readiness logs path.

Что не подтверждено repo-документами:

- standalone markdown doc от `2026-03-15`, который бы отдельно формализовал новый `smart depth breakthrough`;
- commit, который бы вводил новый независимый upstream `layer-space builder`.

## Confirmed Code State

### Real depth path жив в текущем `App.tsx`

Подтверждено в [App.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L1191):

- `computeResolvedDepth(...)` сначала читает `sampleRealDepth(realDepth, nx, ny)`;
- только при отсутствии real depth он падает назад в `computeBaseDepth(...)`;
- затем применяет `nearLimit`, `farLimit`, `gamma`, `invertDepth`.

Ключевые строки:

- [App.tsx:1191](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L1191)
- [App.tsx:1201](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L1201)

Дополнительно:

- `buildProxyMaps(...)` всё ещё вызывается от `realDepth` и `manual`;
- `getState()`/UI всё ещё отдают `previewMode` и `usingRealDepth`.

Ключевые строки:

- [App.tsx:1631](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L1631)
- [App.tsx:2203](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L2203)
- [App.tsx:3015](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L3015)

### Export/render path использует другой upstream artifact set

Подтверждено в [App.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L988):

- `buildPlateCompositeMaps(...)` строит `backgroundMaskUrl`, `backgroundRgbaUrl`, `plateMaskUrls`, `plateRgbaUrls`, `plateDepthUrls`;
- эти assets генерируются в браузере через:
  - `computeResolvedDepth(...)`
  - `smoothBoxMask(...)`
  - `sampleSourceColor(...)`
- per-plate alpha вычисляется как `roleAlpha * boxMask`;
- `plateDepthUrls` строятся как grayscale `remapped depth` с alpha plate mask;
- background формируется как residual `1 - unionAlpha * 0.94`.

Ключевые строки:

- [App.tsx:988](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L988)
- [App.tsx:1056](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L1056)
- [App.tsx:1084](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L1084)
- [App.tsx:1092](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L1092)
- [App.tsx:1118](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L1118)

Подтверждено в [App.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L1862):

- `buildPlateExportAssetsContract()` передаёт в export contract именно `plateCompositeMaps.backgroundRgbaUrl`, `plateMaskUrls`, `plateRgbaUrls`, `plateDepthUrls`;
- `layout` строится отдельно и не заменяет происхождение самих exported plate assets.

Ключевые строки:

- [App.tsx:1862](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L1862)
- [App.tsx:1870](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx#L1870)

Подтверждено в [parallax_plate_export.spec.ts](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/e2e/parallax_plate_export.spec.ts#L235):

- Playwright берёт `api.exportPlateAssets()`;
- затем пишет на диск `global_depth_bw.png`, `background_rgba.png`, `${baseName}_rgba.png`, `${baseName}_depth.png`, `${baseName}_mask.png`, `${baseName}_clean.png`;
- затем сохраняет `plate_export_manifest.json`.

Ключевые строки:

- [parallax_plate_export.spec.ts:235](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/e2e/parallax_plate_export.spec.ts#L235)
- [parallax_plate_export.spec.ts:266](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/e2e/parallax_plate_export.spec.ts#L266)
- [parallax_plate_export.spec.ts:299](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/e2e/parallax_plate_export.spec.ts#L299)

## Confirmed Git Evidence

Подтверждено git history для [App.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx):

- `76e0cccb4` (`2026-03-13 02:31`) — первое появление `App.tsx` с `buildPlateCompositeMaps(...)` и `computeResolvedDepth(...)`;
- `6f133001f` (`2026-03-15 02:22`) — merge-conflict resolution commit, который touch-нул `App.tsx` и `photo_parallax_plate_export.sh`, но сам по себе не доказывает появление нового upstream depth builder;
- дальнейшие коммиты в основном связаны с recon/layout extraction, а не с заменой depth-first base на новый builder.

Подтверждённые команды:

- `git log --follow -- src/App.tsx`
- `git log -L 988,1140:src/App.tsx`
- `git log -L 1191,1205:src/App.tsx`

Подтверждённый результат:

- `buildPlateCompositeMaps(...)` введён уже в `76e0cccb4`;
- `computeResolvedDepth(...)` введён уже в `76e0cccb4`;
- в подтверждённой git-истории не найден отдельный commit, где существовал бы другой полноценный upstream `layer-space` / `smart depth builder`, который потом удалили.

## Recon Conclusion

Подтверждено:

- `real smart depth` / `depth-first base` в проекте действительно существовал как рабочий path:
  - real B/W depth preview
  - `usingRealDepth`
  - `near/far/gamma`
  - `Closer / Farther` strokes as depth correction
- этот path и сейчас концептуально жив в коде через `computeResolvedDepth(...)`, `buildProxyMaps(...)`, `previewMode=depth`, `usingRealDepth`.

Подтверждено отдельно:

- multi-plate export/render path с `2026-03-13` опирается не на независимые plate-local source/depth solves, а на browser-side synthesized assets:
  - `source image`
  - `plate alpha / smoothBoxMask`
  - `global depth`

Следовательно, подтверждённый architectural split выглядит так:

1. `depth-first preview truth` существует
2. `export/render asset generation` существует
3. эти два пути не эквивалентны по происхождению данных

## What This Recon Does Not Claim

Этот recon-документ не утверждает, что:

- качество `2026-03-15` можно полностью восстановить одним `git checkout`;
- текущий renderer сам по себе плохой или хороший;
- в repo точно отсутствовал любой удачный визуальный state вне markdown/gит-подтверждений.

Он утверждает только более узкое и проверяемое:

- `smart depth` path документирован и частично жив в коде;
- current export path документирован как derived/synthetic;
- между ними есть подтверждённое расхождение, которое и должно быть recovery target.
