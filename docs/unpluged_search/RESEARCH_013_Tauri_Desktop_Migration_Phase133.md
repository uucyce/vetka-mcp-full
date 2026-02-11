# Tauri Desktop Migration
**Рекомендуемая фаза:** 133
**Статус:** Research complete
**Приоритет:** ВЫСОКИЙ (стратегический)
**Источник:** Беседы агентов, dual-stack architecture

## Описание
Переход с web-only на Tauri для десктопной версии. -80% размер приложения, -50% RAM, +30-50% 3D производительность.

## Текущее состояние
- FastAPI + React web app работает
- Electron НЕ используется
- Tauri research завершён
- Dual-stack (SaaS + Desktop) архитектура задокументирована

## Технические детали
- Tauri 2.5+: system WebView + Rust backend
- WGPU для 3D рендеринга (вместо WebGL)
- 95% React кода сохраняется
- Trunk-based development
- Feature detection вместо branching
- VR/AR potential через WGPU bindings

## Шаги имплементации
1. Инициализировать Tauri проект в monorepo
2. Адаптировать API layer (FastAPI → Tauri commands)
3. Настроить WGPU rendering pipeline
4. Тестировать на macOS (M4 Pro target)
5. CI/CD: dual build (web + desktop)

## Ожидаемый результат
Нативное десктоп-приложение с лучшей производительностью

---
