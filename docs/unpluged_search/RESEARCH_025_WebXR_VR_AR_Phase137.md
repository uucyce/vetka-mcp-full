# Cross-Platform WebXR (VR/AR Support)
**Рекомендуемая фаза:** 137
**Статус:** Research only
**Приоритет:** НИЗКИЙ (future)
**Источник:** docs_00-8phases Cross_Platform_3D_Spatial_Interface_2025

## Описание
WebXR support для Apple Vision Pro, Meta Quest Pro. Gesture-based navigation, immersive graph exploration.

## Текущее состояние
- 3D viewport работает в browser
- WebXR НЕ реализован
- VR/AR support НЕ существует
- Cross-platform: desktop + mobile only

## Технические детали
- WebXR API для VR/AR consistency
- Vision Pro + Quest Pro targets
- Gesture controls: pinch-to-zoom, two-finger rotate
- Hand-tracking support
- Spatial anchoring для real-world overlays
- Tauri 2.5+ WGPU bindings для native VR

## Шаги имплементации
1. Добавить WebXR session setup
2. Реализовать VR controller/hand-tracking input
3. Адаптировать 3D viewport для immersive mode
4. Добавить spatial anchoring
5. Тестировать на Quest Pro (first target)

## Ожидаемый результат
Immersive exploration knowledge graphs в VR/AR
