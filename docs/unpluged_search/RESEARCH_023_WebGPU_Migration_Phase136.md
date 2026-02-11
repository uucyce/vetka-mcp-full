# WebGPU Migration (от WebGL)
**Рекомендуемая фаза:** 136
**Статус:** Research complete
**Приоритет:** ВЫСОКИЙ (performance)
**Источник:** docs_00-8phases WebGPU_Graph_Visualization_2025

## Описание
Миграция Three.js renderer с WebGL на WebGPU. 2x производительность: 60 FPS vs 40 FPS для 50k nodes.

## Текущее состояние
- Three.js WebGL renderer работает
- WebGPU experimental support в Three.js
- Safari 19 (60 FPS), Chrome 130 (55 FPS), Firefox 132 (50 FPS) в benchmarks

## Технические детали
- WebGPU compute shaders для GPU-accelerated graph layout
- Force-directed layout: 100ms (WebGPU) vs 200ms (WebGL)
- -30% memory footprint
- WGSL compute shader examples в research
- Fallback chain: WebGPU → WebGL → Canvas

## Шаги имплементации
1. Обновить Three.js до версии с WebGPU support
2. Создать WebGPU renderer path
3. Реализовать compute shaders для layout calculation
4. Feature detection + fallback chain
5. Benchmark на M4 Pro: target 60 FPS 100k nodes

## Ожидаемый результат
2x рост производительности 3D визуализации
