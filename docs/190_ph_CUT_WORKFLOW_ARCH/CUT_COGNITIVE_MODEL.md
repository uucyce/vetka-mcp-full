# CUT Cognitive Model
# Как редактор мыслит внутри системы

**Date:** 2026-03-18
**Basis:** CUT_TARGET_ARCHITECTURE.md
**Audience:** UX/product design, инвесторы, новые разработчики

---

## Главная идея

Хороший инструмент совпадает с когнитивной моделью пользователя.
CUT построен вокруг 5 типов мышления монтажёра.

---

## 5 когнитивных слоёв

```
                    CUT COGNITIVE MODEL

              ┌──────────────────────────┐
              │         SCRIPT           │
              │                          │
              │  Narrative intent        │
              │  Characters              │
              │  Dramatic beats          │
              │                          │
              │  "What should happen?"   │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │       DAG PROJECT        │
              │     (Film Ontology)      │
              │                          │
              │  Scenes + Media variants │
              │  Characters + Lore       │
              │  Semantic links          │
              │                          │
              │  "What material exists?" │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │        TIMELINE          │
              │                          │
              │  Linear narrative path   │
              │  Rhythm / pacing         │
              │  Transitions             │
              │                          │
              │  "What version works?"   │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │        PULSE AI          │
              │                          │
              │  Suggest alternatives    │
              │  Evaluate rhythm         │
              │  Explore DAG branches    │
              │                          │
              │  "What else is possible?"│
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │        EDITOR            │
              │                          │
              │  Accept / reject         │
              │  Replace scenes          │
              │  Adjust rhythm           │
              │                          │
              │  "What feels right?"     │
              └──────────────────────────┘
```

| Слой | Когнитивный вопрос | Пространство |
|------|-------------------|-------------|
| Script | Что должно происходить? | Narrative Space |
| DAG | Какие варианты вообще существуют? | Media Space |
| Timeline | Какая версия работает? | Temporal Space |
| PULSE | Какие ещё варианты попробовать? | Exploration Space |
| Editor | Какое решение верное? | Decision Space |

---

## Когнитивный цикл монтажа

Редактор не идёт линейно сверху вниз. Это итерационный цикл:

```
Script idea
    ↓
Explore material (DAG)
    ↓
Build timeline
    ↓
AI suggests variants
    ↓
Editor chooses / modifies
    ↓
Back to DAG → repeat
```

Каждая итерация уточняет фильм. PULSE расширяет пространство поиска,
редактор сужает его до финальной версии.

---

## Три пространства внимания

Редактор постоянно переключается между тремя пространствами:

```
NARRATIVE SPACE (script)     — что рассказывать
MEDIA SPACE (DAG)            — из чего рассказывать
TEMPORAL SPACE (timeline)    — как рассказывать
```

В обычных NLE (Premiere, DaVinci, FCP) это три разных мира.
В CUT — одна система координат:

```
script  ≠ project bin  ≠ timeline    (обычный NLE)
script  = spine of DAG = projected to timeline    (CUT)
```

---

## Роль AI в когнитивной модели

AI не заменяет редактора. AI расширяет пространство вариантов.

```
Human: selects narrative path    (decision)
AI:    explores graph            (search)
```

Без AI: редактор перебирает варианты вручную (медленно, пропускает ветки).
С AI: PULSE обходит весь DAG и предлагает альтернативы, которые человек мог не увидеть.

---

## Формулы

> **CUT is not a timeline editor. CUT is a narrative graph navigator.**

> **The editor navigates narrative intent through the DAG of possibilities.**

> **PULSE explores the graph. The editor chooses the path.**

---

## Почему эта модель работает

1. **Почему нужен DAG** — потому что монтаж = поиск среди вариантов
2. **Почему нужен Script Spine** — потому что монтаж = драматургия
3. **Почему нужен AI** — потому что человек не может перебрать все ветки графа
4. **Почему нужен Timeline** — потому что финальный фильм = линейная проекция

CUT — это не video editor. Это **narrative exploration system**.
