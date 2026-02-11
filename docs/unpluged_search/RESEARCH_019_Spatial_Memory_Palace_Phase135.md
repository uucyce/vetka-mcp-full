# Spatial Memory Palace (Метод Локусов)
**Рекомендуемая фаза:** 135
**Статус:** Research + code example (300+ lines JS)
**Приоритет:** СРЕДНИЙ
**Источник:** docs_00-8phases Spatial_Memory_Palace_Implementation_2025

## Описание
Адаптация древнего метода локусов для 3D цифровых интерфейсов. Spatial memory улучшает recall на 30-40%.

## Текущее состояние
- 3D viewport работает
- Spatial memory features НЕ интегрированы
- Research с code examples готов
- Feasibility: 8/10

## Технические детали
- Hippocampus-based navigation metaphor
- Pin important nodes → create custom clusters
- Temporal navigation: timeline slider
- Collective intelligence: 5 users at 50 FPS
- 10k loci at 60 FPS (M4 + WebGPU)
- <100ms contextual unfolding
- 300+ lines JavaScript implementation in research doc

## Шаги имплементации
1. Адаптировать JS implementation из research doc
2. Интегрировать с Three.js viewport
3. Добавить pinning → custom spatial clusters
4. Реализовать temporal navigation
5. Тестировать с реальными VETKA knowledge graphs

## Ожидаемый результат
+30-40% улучшение recall при навигации по knowledge base
