# Matryoshka: Иерархическая Кластеризация
**Рекомендуемая фаза:** 133
**Статус:** Research complete, no code
**Приоритет:** ВЫСОКИЙ
**Источник:** Spatial Memory Palace Research 2025

## Описание
Hierarchical clustering с progressive unfolding (<100ms latency). Collapse/expand кластеры с плавными переходами. Matryoshka-effect.

## Текущее состояние
- LOD система существует (10 levels)
- HDBSCAN clustering НЕ реализован
- Progressive unfolding НЕ реализован
- Semantic zoom НЕ реализован

## Технические детали
- HDBSCAN для автоматической кластеризации
- Progressive unfolding: click cluster → expand children
- Temporal navigation: slider для визуализации изменений во времени
- 10k loci at 60 FPS (M4, WebGPU)
- <100ms contextual unfolding target
- UMAP для 1D позиционирования

## Шаги имплементации
1. Интегрировать HDBSCAN clustering library
2. Реализовать cluster collapse/expand с анимацией
3. Добавить semantic zoom (high-level → detail on focus)
4. Создать temporal navigation slider
5. Интегрировать с CAM surprise для auto-clustering

## Ожидаемый результат
Интуитивная навигация по большим графам, снижение cognitive load на 15-20%

---
