# Parallax Hover-Politsia Layer Order Recon

Дата: `2026-03-20`

## 1. Why This Recon Exists

После ручного просмотра актуального `hover-politsia` render стало ясно, что проблема не выглядит как частичный visual drift.

По пользовательскому verdict:

- результат визуально совпадает с плохим состоянием до недавних правок `white = near`;
- ощущение layered parallax по большинству сцены не появилось;
- единственный явно движущийся материал — туман / steam;
- туман наезжает на голову человека, хотя по semantic layer logic должен быть ниже или как минимум не иметь такого occlusion authority;
- остаются две главные гипотезы:
  - перепутан layer order / Z order / compositing priority;
  - смотрим не новый render, а старый export / stale artifact.

Этот документ нужен, чтобы зафиксировать именно это состояние как новую canonical problem statement для следующего цикла работ.

## 2. Current Visual Verdict

По ручному просмотру текущего video artifact:

- туман движется;
- остальная сцена в основном воспринимается как статичная;
- человек и основные объекты не читаются как убедительно разведённые по глубине;
- fog/steam получает визуальную власть над объектом, который должен читаться ближе или иначе композиться;
- итог выглядит не как recovered spatial parallax, а как broken atmospheric overlay over mostly static scene.

Практический вывод:

- текущий result нельзя считать успешным ни по plate semantics, ни по depth-aware compositing;
- предыдущие fixes не доказали, что final viewed mp4 соответствует intended new code path.

## 3. Primary Hypotheses

### Hypothesis A. Layer order / Z order mismatch

Возможный сценарий:

- plate ordering в `plate_stack` / `plate_layout` / renderer filter graph не соответствует intended near/far semantics;
- atmospheric plate или `environment-mid` получает compositor precedence, которая визуально делает его перед человеком;
- `z`, `depthPriority`, `role`, actual render order и alpha compositing authority не совпадают друг с другом.

Что должно подтвердить или опровергнуть гипотезу:

- сопоставление `plate_stack.json`, `plate_layout.json`, render graph order и фактического occlusion результата в mp4;
- отдельный разбор plate, содержащего fog/steam;
- ответ на вопрос: fog это hard plate, soft participation layer или derived background material.

### Hypothesis B. Stale export / stale render artifact

Возможный сценарий:

- текущий просматриваемый mp4 был собран не из последнего code path;
- export assets и render outputs не были реально пересобраны после последних fixes;
- user и agent смотрят artifact с историческим drift, а не свежий end-to-end result.

Что должно подтвердить или опровергнуть гипотезу:

- provenance check для render artifact:
  - timestamp;
  - manifest/report рядом с mp4;
  - source export folder;
  - commit/date correlation;
  - whether preview was regenerated after the last relevant commits.

## 4. What This Recon Does Not Claim

Этот recon не утверждает, что:

- `white = near` fix был ложным;
- camera model fix не работает;
- smart depth отсутствует;
- корень проблемы уже точно найден.

Он утверждает более узкое:

- observed final video still fails the intended visual goal;
- fog/head occlusion is a strong deterministic symptom;
- next work must explicitly separate:
  - stale artifact verification;
  - layer order / compositing authority verification.

## 5. Required Next Checks

### Check 1. Artifact provenance

Нужно проверить:

- какой именно mp4 просмотрен;
- когда он был собран;
- из какого export root;
- после каких commits;
- есть ли более свежий render рядом, который user фактически не смотрел.

### Check 2. Plate semantics for fog/steam

Нужно проверить:

- какой plate содержит steam/fog;
- какой у него `role`;
- какие у него `z` и `depthPriority`;
- где он стоит в real render order;
- должен ли он вообще окклюдить голову человека.

### Check 3. Render order vs layout order

Нужно проверить:

- совпадает ли порядок plate-ов в `plate_layout.json` с compositor order в renderer;
- не происходит ли inverse compositing относительно expected near/far order;
- не превращается ли `environment-mid` в visually dominant front overlay.

## 6. Decision For Next Agents

Следующий цикл работ должен идти так:

1. Сначала доказать, что смотрим свежий artifact, а не stale render.
2. Затем разобрать exact fog/head occlusion chain.
3. Только после этого править renderer / layout / plate semantics.

Иначе есть риск снова чинить код, не тот artifact или не тот слой.

