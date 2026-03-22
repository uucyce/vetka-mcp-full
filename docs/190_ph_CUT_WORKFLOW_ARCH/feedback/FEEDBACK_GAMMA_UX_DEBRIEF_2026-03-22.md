# Gamma UX Debrief — 2026-03-22
**30 commits | 3 waves | claude/cut-ux**

---

**Q1: Что сломано?**
Dockview inline styles непобедимы — библиотека инжектит `style="border-bottom-color: rgb(0, 12, 24)"` на DOM элементы при каждом фокусе группы. CSS `!important` побеждает, но `[style*=]` селектор — хрупкий хак. При обновлении dockview v6 это может сломаться. Нужен форк или патч dockview, убирающий синий на уровне JS.

**Q2: Что неожиданно сработало?**
Двойной класс `.dockview-theme-dark.dockview-theme-dark` — убил 53 из 63 `!important` без единого визуального изменения. Паттерн стоит документировать как стандарт для любых CSS-библиотечных оверрайдов в проекте. Также: параллельные 3 Explore-агента для аудита дали полную картину домена за 2 минуты — предотвратили 3 ненужных таска.

**Q3: Одна нереализованная идея?**
Status bar (нижняя полоса окна): текущий инструмент, zoom level, fps, размер проекта, статус сохранения, workspace name. Как в Premiere/FCP7. Сейчас эта информация размазана по toolbar'ам. Одна 18px полоска внизу = professional feel. Файл: `StatusBar.tsx`, mount в CutEditorLayoutV2 после DockviewLayout.
