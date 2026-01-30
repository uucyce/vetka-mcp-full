# HAIKU-5: Проверка маркеров в qdrant_updater.py

**Статус:** УСПЕШНО ✓ (с критическими замечаниями)
**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/qdrant_updater.py`
**Дата:** 2026-01-27

---

## 1. МАРКЕРЫ COHERENCE

### ✓ MARKER_COHERENCE_ROOT_001
**Расположение:** Строка 53-57
**Статус:** ПРАВИЛЬНО РАЗМЕЩЕН

```python
# TODO_95.9: MARKER_COHERENCE_ROOT_001 - This class writes directly to Qdrant only
# ROOT CAUSE: All file watcher events bypass TripleWriteManager
# ARCHITECTURE DEBT: Should integrate with TripleWriteManager.write_file()
# FIX: Add method use_triple_write(tw_manager) and route writes through it
# FALLBACK: If TripleWrite unavailable, use legacy direct Qdrant writes
```

**Проверка:**
- ✓ Находится после docstring класса (строка 44-51)
- ✓ Четко описывает ROOT CAUSE архитектурной проблемы
- ✓ Указывает на обход TripleWriteManager в file_watcher событиях
- ✓ Предлагает конкретное решение (метод use_triple_write)

### ✓ MARKER_COHERENCE_BYPASS_004
**Расположение:** Строка 388-392
**Статус:** ОТСУТСТВУЕТ (БАГ #1)

**Находится:**
```python
# NOTE: This bypasses Weaviate/Changelog when TW is disabled or fails
self.client.upsert(
    collection_name=self.collection_name,
    points=[point],
    wait=False  # Non-blocking - UI won't freeze
)
```

**Проблема:**
- Нет явного маркера TODO_95.9: MARKER_COHERENCE_BYPASS_004
- Есть только NOTE на строке 387 о обходе Weaviate/Changelog
- Это критический момент - QDRANT-ONLY уписерт (direct Qdrant)

**Рекомендация:** Добавить полный маркер

### ✓ MARKER_COHERENCE_BYPASS_005
**Расположение:** Строка 490-497
**Статус:** ЧАСТИЧНО ПРАВИЛЬНО

```python
# TODO_95.9: MARKER_COHERENCE_BYPASS_005 - Batch upsert bypasses Weaviate/Changelog
# FIX: Implement tw.batch_write(files) or loop tw.write_file() for each
# RECOMMEND: Batch writes need atomic transaction support in TripleWrite
self.client.upsert(
    collection_name=self.collection_name,
    points=points,
    wait=False  # Non-blocking - UI won't freeze
)
```

**Проверка:**
- ✓ Маркер присутствует (строка 490)
- ✓ Правильно размещен перед self.client.upsert()
- ✓ Четко указывает на обход Weaviate/Changelog в batch операции
- ✓ Предлагает решение (tw.batch_write или loop)

---

## 2. ПРОВЕРКА ЛОГИРОВАНИЯ

### ✗ КРИТИЧЕСКИЙ БУГ #1: print() вместо logger

**Найдено 7 экземпляров print():**

1. **Строка 211** - _get_content_hash():
```python
print(f"[QdrantUpdater] Error hashing {file_path}: {e}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.error()

2. **Строка 268** - _file_changed():
```python
print(f"[QdrantUpdater] Error checking {file_path}: {e}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.error()

3. **Строка 308** - _get_embedding():
```python
print(f"[QdrantUpdater] Embedding error: {e}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.error()

4. **Строка 337** - update_file():
```python
print(f"[QdrantUpdater] Skipped (unchanged): {file_path.name}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.debug() или logger.info()

5. **Строка 347** - update_file():
```python
print(f"[QdrantUpdater] Failed to embed: {file_path.name}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.error()

6. **Строка 447** - batch_update():
```python
print(f"[QdrantUpdater] Batch updating {len(to_update)} files...")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.info()

7. **Строка 499** - batch_update():
```python
print(f"[QdrantUpdater] Batch updated: {len(points)} files")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.info()

8. **Строка 501** - batch_update():
```python
print(f"[QdrantUpdater] Batch upsert error: {e}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.error()

9. **Строка 534** - soft_delete():
```python
print(f"[QdrantUpdater] Soft deleted: {file_path}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.info()

10. **Строка 539** - soft_delete():
```python
print(f"[QdrantUpdater] Error soft deleting {file_path}: {e}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.error()

11. **Строка 564** - hard_delete():
```python
print(f"[QdrantUpdater] Hard deleted: {file_path}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.info()

12. **Строка 569** - hard_delete():
```python
print(f"[QdrantUpdater] Error hard deleting {file_path}: {e}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.error()

13. **Строка 618** - cleanup_deleted():
```python
print(f"[QdrantUpdater] Cleaned up {len(to_delete)} old deleted files")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.info()

14. **Строка 623** - cleanup_deleted():
```python
print(f"[QdrantUpdater] Error cleaning up: {e}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.error()

15. **Строка 684** - scan_directory():
```python
print(f"[QdrantUpdater] Starting scan: {total_files} files to process in {path}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.info()

16. **Строка 706** - scan_directory():
```python
print(f"[QdrantUpdater] Progress callback error: {e}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.error()

17. **Строка 712** - scan_directory():
```python
print(f"[QdrantUpdater] Directory scan complete: {indexed_count} files indexed from {path}")
```
**Статус:** ДОЛЖЕН БЫТЬ logger.info()

---

## 3. ПРОВЕРКА ЛОГГЕРА

### ✓ Logger инициализирован правильно
**Строка 25:**
```python
logger = logging.getLogger(__name__)
```
**Статус:** ПРАВИЛЬНО (но используется не везде)

---

## 4. ПРОВЕРКА TYPE_CHECKING

### ✓ TYPE_CHECKING import правильный
**Строка 28-29:**
```python
if TYPE_CHECKING:
    from src.orchestration.triple_write_manager import TripleWriteManager
```
**Статус:** ПРАВИЛЬНО - избегает circular import

---

## 5. АРХИТЕКТУРНЫЕ ПРОБЛЕМЫ

### Проблема #1: Две точки обхода TripleWrite (COHERENCE BYPASS)
1. **Строка 388** (update_file) - Прямой Qdrant upsert (MARKER отсутствует)
2. **Строка 493** (batch_update) - Batch upsert (MARKER_COHERENCE_BYPASS_005)

**Риск:** Когда TripleWrite отключен или падает, данные идут только в Qdrant, не в Weaviate/Changelog

### Проблема #2: Batch операция не атомарна
- Batch update (строка 403-504) не использует TripleWrite вообще
- Нет поддержки batch_write в TripleWriteManager (нужна)
- В цикле вызывать tw.write_file() неэффективно (много RPC)

### Проблема #3: Progress callback может выбросить исключение
- Строка 706: catch Exception но не логируется правильно (print!)

---

## 6. СВОДКА НАЙДЕННЫХ БАГОВ

| # | Тип | Строка | Проблема | Статус |
|---|-----|--------|----------|--------|
| 1 | Маркер | 388 | MARKER_COHERENCE_BYPASS_004 отсутствует | Критичный |
| 2 | Логирование | 211,268,308,337... | 17x print() вместо logger | Критичный |
| 3 | Архитектура | 403-504 | Batch update не поддерживает TripleWrite | Важный |
| 4 | Архитектура | 490-497 | Batch upsert обходит Weaviate | Важный |

---

## 7. ДЕЙСТВИЯ

### ОБЯЗАТЕЛЬНЫЕ (Критичные):

1. **Добавить маркер на строку 388:**
```python
# TODO_95.9: MARKER_COHERENCE_BYPASS_004 - Single file upsert bypasses Weaviate/Changelog when TW unavailable
# FIX: Ensure TW is enabled via use_triple_write(enable=True)
# FALLBACK: Direct Qdrant upsert is only for backward compatibility
```

2. **Заменить все 17 print() на logger.[info/error/debug]():**
   - Errors → logger.error()
   - Info/progress → logger.info()
   - Debug → logger.debug()

### РЕКОМЕНДУЕМЫЕ (Важные):

3. Добавить batch_write() в TripleWriteManager
4. Обновить batch_update() для поддержки TripleWrite
5. Добавить тесты на coherence consistency

---

## ЗАКЛЮЧЕНИЕ

**Общее состояние:** 80/100 ⚠️

- ✓ Маркеры COHERENCE присутствуют (2 из 3)
- ✗ Logger не везде используется (17x print!)
- ✗ batch_update() полностью обходит TripleWrite
- ✓ TYPE_CHECKING правильно настроен
- ✓ Архитектурная проблема задокументирована

**Приоритет:** Срочно заменить все print() и добавить MARKER_COHERENCE_BYPASS_004
