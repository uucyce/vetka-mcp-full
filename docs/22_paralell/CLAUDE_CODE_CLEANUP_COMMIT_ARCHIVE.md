# 🧹 VETKA CLEANUP: КОММИТ + АРХИВАЦИЯ

## ⚠️ ШАГ 0: СДЕЛАЙ КОММИТ ПЕРЕД ВСЕМ!

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

git status
git add -A
git commit -m "PRE-CLEANUP SNAPSHOT: Phase 22 state before major refactoring

Changes since last commit:
- Frontend cleanup (ForceGraph3D removed)
- Dead socket listeners removed  
- Knowledge layout 7 bugs fixed

This commit enables easy rollback if cleanup breaks anything."

git tag -a pre-cleanup-snapshot -m "Safe rollback point before cleanup"
git log --oneline -3
```

---

## ШАГ 1: СОЗДАТЬ АРХИВНЫЕ ПАПКИ

```bash
mkdir -p archive/main_backups
mkdir -p archive/patches
mkdir -p archive/old_tests
mkdir -p archive/file_backups
mkdir -p archive/old_scripts
```

---

## ШАГ 2: АРХИВИРОВАТЬ main.py ДУБЛИ

```bash
# Бэкапы main.py
mv main.py.backup_step2 archive/main_backups/
mv main_backup_day1.py archive/main_backups/
mv main_modular.py archive/main_backups/

# Проверить
ls archive/main_backups/
```

---

## ШАГ 3: АРХИВИРОВАТЬ ПАТЧИ

```bash
mv PHASE_F_PATCH_SUMMARY.py archive/patches/
mv patch_tree_renderer.py archive/patches/
mv patch_v3.py archive/patches/

ls archive/patches/
```

---

## ШАГ 4: АРХИВИРОВАТЬ test_ ИЗ КОРНЯ

```bash
mv test_arc_solver.py archive/old_tests/
mv test_classifier_v2.py archive/old_tests/
mv test_eval_agent.py archive/old_tests/
mv test_hostess_agent.py archive/old_tests/
mv test_learner_initializer.py archive/old_tests/
mv test_model_extraction.py archive/old_tests/
mv test_phase54_integration.py archive/old_tests/
mv test_phase_7_2a_patches.py archive/old_tests/
mv test_phase_7_3_integration.py archive/old_tests/
mv test_phase_8_hybrid.py archive/old_tests/
mv test_triple_write.py archive/old_tests/
mv test_workflow_direct.py archive/old_tests/
mv test_results.json archive/old_tests/
mv test_ui_simple.html archive/old_tests/
mv test_api_gateway.sh archive/old_tests/

ls archive/old_tests/
```

---

## ШАГ 5: АРХИВИРОВАТЬ .backup ФАЙЛЫ

```bash
# JS бэкап
mv app/frontend/static/js/kg-tree-renderer.js.backup_20251230_160643 archive/file_backups/

# Python бэкапы
mv elisya_integration/context_manager.py.backup archive/file_backups/ 2>/dev/null || echo "Not found"
mv src/agents/streaming_agent.py.backup archive/file_backups/ 2>/dev/null || echo "Not found"
mv src/orchestration/agent_orchestrator_backup.py archive/file_backups/ 2>/dev/null || echo "Not found"
mv src/visualizer/tree_renderer.py.backup archive/file_backups/ 2>/dev/null || echo "Not found"
mv src/visualizer/tree_renderer.py.backup_20251215_185512 archive/file_backups/ 2>/dev/null || echo "Not found"

# HTML бэкапы
mv frontend/templates/index.html.backup archive/file_backups/ 2>/dev/null || echo "Not found"
mv frontend/templates/index.html.backup.phase17 archive/file_backups/ 2>/dev/null || echo "Not found"

ls archive/file_backups/
```

---

## ШАГ 6: АРХИВИРОВАТЬ СТАРЫЕ СКРИПТЫ

```bash
mv fix_and_run.sh archive/old_scripts/
mv fix_phase_7_9.sh archive/old_scripts/
mv verify_phase_7_9.sh archive/old_scripts/
mv step3_verify.sh archive/old_scripts/
mv deploy_phase54.sh archive/old_scripts/
mv scaleX archive/old_scripts/ 2>/dev/null || echo "Not found"

ls archive/old_scripts/
```

---

## ШАГ 7: АРХИВИРОВАТЬ ЭКСПЕРИМЕНТЫ

```bash
mkdir -p archive/experiments

mv fine_tune_direct.py archive/experiments/
mv fine_tune_local_m4.py archive/experiments/
mv fine_tune_ollama.py archive/experiments/
mv fine_tune_simple.py archive/experiments/
mv train_1hour.py archive/experiments/

ls archive/experiments/
```

---

## ШАГ 8: ПРОВЕРИТЬ РЕЗУЛЬТАТ

```bash
echo "=== КОРЕНЬ ПОСЛЕ УБОРКИ ==="
ls -la | grep -v "^\." | grep -v "^d" | wc -l
ls -la | grep -v "^\."

echo ""
echo "=== АРХИВ ==="
ls -la archive/
du -sh archive/
```

---

## ШАГ 9: КОММИТ УБОРКИ

```bash
git add -A
git status

git commit -m "CLEANUP: Archived 35+ unused files

Moved to archive/:
- 3 main.py backups → archive/main_backups/
- 3 patch files → archive/patches/  
- 15 old test files → archive/old_tests/
- 8 .backup files → archive/file_backups/
- 6 old scripts → archive/old_scripts/
- 5 experiments → archive/experiments/

No code changes. Project structure cleaned.
Files recoverable from archive/ or git history."

git log --oneline -3
```

---

## ШАГ 10: ОТЧЁТ

Покажи:
1. `ls -la` корня (сколько файлов осталось?)
2. `ls -la archive/` (что в архиве?)
3. `git log --oneline -5` (коммиты)
4. Всё ли работает? `python main.py --help` или просто импорт
