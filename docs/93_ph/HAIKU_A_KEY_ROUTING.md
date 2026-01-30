# Key Routing Markers Report

## 1. Текущий порядок ключей

### Структура в config.json (data/config.json)
```
OpenRouter format:
{
  "paid": "sk-or-v1-04d4e5a4cc...",    ← index 0 при загрузке
  "free": [
    "sk-or-v1-08b39403...",             ← index 1
    "sk-or-v1-2335b023...",             ← index 2
    ... и так далее
  ]
}
```

### Порядок загрузки ключей
**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/utils/unified_key_manager.py` (строки 551-563)

1. **Сначала** загружается `paid` ключ → добавляется в список (строка 556)
2. **Потом** загружаются все ключи из массива `free` → добавляются в список (строки 559-562)

**Результат:** `index 0 = PAID` ключ (обозначен как `alias='paid'`)

---

## 2. Функции и маркеры для изменения

| Функция | Файл:Строка | Текущее поведение | Что менять |
|---------|------------|-----------------|-----------|
| `get_openrouter_key()` | unified_key_manager.py:185-222 | Returns PAID key (index 0) по умолчанию | Phase 57.11: "Returns PAID key (index 0) by default" |
| `reset_to_paid()` | unified_key_manager.py:237-244 | Сбрасывает index на 0 (paid) | **ПЕРЕИМЕНОВАТЬ** в `reset_to_free()` + изменить логику |
| `_load_provider_keys()` | unified_key_manager.py:532-565 | Загружает paid ПЕРВЫМ | Поменять порядок: free ПЕРВЫМИ, paid ПОСЛЕДНИМ |
| `add_openrouter_key()` | unified_key_manager.py:456-477 | `is_paid=True` → insert(0), иначе append() | Поменять: `is_paid=True` → append(), иначе insert(0) |
| `save_to_config()` | unified_key_manager.py:585-589 | Сохраняет [0] как 'paid', остаток как 'free' | Поменять: [0] как 'free', остаток как 'paid' |

---

## 3. Ключевые строки кода

### Маркер 1: Phase 57.11 - Текущий приоритет
**Файл:** `src/utils/unified_key_manager.py:189`
```
Phase 57.11: Returns PAID key (index 0) by default.
```
Это комментарий в `get_openrouter_key()` - нужно будет обновить на "Returns FREE key".

### Маркер 2: reset_to_paid() функция
**Файл:** `src/utils/unified_key_manager.py:237-244`
```python
def reset_to_paid(self) -> None:
    """
    Reset to paid key (index 0).
    Call at start of new conversation or after successful responses.
    """
    if self._current_openrouter_index != 0:
        logger.info(f"[UnifiedKeyManager] Reset to paid key (was index {self._current_openrouter_index})")
        self._current_openrouter_index = 0
```
**Действие:** Переименовать в `reset_to_free()` и обновить комментарий.

### Маркер 3: add_openrouter_key() логика
**Файл:** `src/utils/unified_key_manager.py:456-477`
```python
if is_paid:
    self.keys[ProviderType.OPENROUTER].insert(0, record)  # ← PAID в начало
else:
    self.keys[ProviderType.OPENROUTER].append(record)     # ← FREE в конец
```
**Действие:** Инвертировать логику.

### Маркер 4: Загрузка из config.json
**Файл:** `src/utils/unified_key_manager.py:551-563`
```python
elif isinstance(keys_data, dict):
    if paid_key := keys_data.get('paid'):
        if validator(paid_key):
            record = APIKeyRecord(provider=provider, key=paid_key, alias='paid')
            self.keys[provider].append(record)    # ← PAID добавляется первым
            loaded += 1

    for i, key in enumerate(keys_data.get('free', [])):
        if key and validator(key):
            record = APIKeyRecord(provider=provider, key=key, alias=f'free_{i + 1}')
            self.keys[provider].append(record)    # ← FREE добавляются вторыми
            loaded += 1
```
**Действие:** Поменять местами эти два блока.

### Маркер 5: Сохранение в config.json
**Файл:** `src/utils/unified_key_manager.py:585-589`
```python
if provider_name == 'openrouter':
    config['api_keys']['openrouter'] = {
        'paid': active_keys[0] if active_keys else None,  # ← index 0 сохраняется как 'paid'
        'free': active_keys[1:] if len(active_keys) > 1 else []
    }
```
**Действие:** Поменять местами логику.

### Маркер 6: Comment на строке 220
**Файл:** `src/utils/unified_key_manager.py:220`
```
# Return current key (defaults to index 0 = paid key)
```
**Действие:** Обновить на "defaults to index 0 = free key".

---

## 4. Дополнительные файлы для проверки

**Файл:** `src/orchestration/services/api_key_service.py` (строки 1-10)
- Использует `UnifiedKeyManager` как alias `KeyManager`
- Метод `get_key()` вызывает `self.key_manager.get_active_key(provider_type)` - этот вызов не нужно менять

---

## 5. Порядок изменений (рекомендация)

1. **Переименовать** `reset_to_paid()` → `reset_to_free()` (строка 237)
2. **Поменять логику** в `_load_provider_keys()` - FREE ПЕРВЫМИ (строки 551-563)
3. **Поменять логику** в `add_openrouter_key()` - FREE insert(0), PAID append (строки 467-470)
4. **Поменять логику** в `save_to_config()` - активные[0] как 'free' (строка 587)
5. **Обновить комментарии**:
   - Строка 189: Phase 57.11 update
   - Строка 220: index 0 = free key
   - Строка 239: Reset to free key

---

## 6. Текущее состояние в config.json

Дата: 2026-01-20T22:32:08

**OpenRouter:**
- index 0: sk-or-v1-04d4e5a4cc... (marked as 'paid' - PAID KEY)
- index 1-9: 9 free ключей

**Другие провайдеры:**
- Gemini: 3 ключей в массиве
- XAI: 3 ключей в массиве
- OpenAI: 2 ключей в массиве
- Остальные: одиночные или пусто

**Важно:** После изменений структура config.json останется той же, но СМЫСЛ поменяется (FREE станет приоритетом).
