# Дополнение к HAIKU_2: Key Rotation & Cooldown System
## Phase 90.10 - Детальный аудит системы ротации ключей и cooldown механизма

**Автор:** Haiku 4.5
**Дата:** 2026-01-25
**Фокус:** Ротация ключей, 24h cooldown, интеграция с Provider Registry

---

## OVERVIEW
Система управления ключами VETKA использует **UnifiedKeyManager** (Phase 57.12) как единый центральный компонент. Этот отчет дополняет HAIKU_2 конкретными аспектами ротации, cooldown и интеграции с провайдерами.

---

## 1. KEY ROTATION LOGIC

### Файл: `/src/utils/unified_key_manager.py`

#### 1.1 Функция `get_openrouter_key()` (Строки 185-222)

```python
def get_openrouter_key(self, index: Optional[int] = None, rotate: bool = False) -> Optional[str]:
    """
    Get OpenRouter key with rotation control.

    Phase 57.11: Returns PAID key (index 0) by default.
    Use rotate=True or rotate_to_next() when key fails.

    Args:
        index: Specific index (0-based) or None for current key
        rotate: If True, rotate to next key BEFORE returning

    Returns:
        API key string or None
    """
    openrouter_keys = self.keys.get(ProviderType.OPENROUTER, [])
    if not openrouter_keys:
        return None

    # Get available keys (skip rate-limited)
    available_keys = [r for r in openrouter_keys if r.is_available()]
    if not available_keys:
        # All keys in cooldown
        logger.warning("[UnifiedKeyManager] All OpenRouter keys in cooldown!")
        return None

    if index is not None:
        if 0 <= index < len(available_keys):
            return available_keys[index].key
        return None

    # Rotate first if requested
    if rotate:
        self._current_openrouter_index = (self._current_openrouter_index + 1) % len(available_keys)
        logger.info(f"[UnifiedKeyManager] Rotated to key index {self._current_openrouter_index}")

    # Return current key (defaults to index 0 = paid key)
    idx = self._current_openrouter_index % len(available_keys)
    return available_keys[idx].key
```

**Ключевые моменты:**
- **Строка 204:** Фильтрует только доступные ключи через `is_available()` (пропускает ключи в cooldown)
- **Строка 217:** Round-robin ротация через `(index + 1) % len(available_keys)`
- **Строка 221:** По умолчанию возвращает первый доступный ключ (обычно PAID)
- **Инициализация:** `self._current_openrouter_index = 0` (строка 157) - начинает с paid ключа

#### 1.2 Функция `rotate_to_next()` (Строки 224-235)

```python
def rotate_to_next(self) -> None:
    """
    Explicitly rotate to next OpenRouter key.
    Call this when current key fails (402, 401, timeout).
    """
    openrouter_keys = self.keys.get(ProviderType.OPENROUTER, [])
    available_keys = [r for r in openrouter_keys if r.is_available()]

    if available_keys:
        old_index = self._current_openrouter_index
        self._current_openrouter_index = (self._current_openrouter_index + 1) % len(available_keys)
        logger.info(f"[UnifiedKeyManager] Rotated key: {old_index} -> {self._current_openrouter_index}")
```

**Механизм:**
- Вызывается явно когда ключ фейлится
- Скипает ключи в cooldown (только считает `available_keys`)
- Логирует old_index -> new_index для отслеживания

#### 1.3 Функция `reset_to_paid()` (Строки 237-244)

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

**Использование:**
- Сброс на paid ключ после успешных ответов
- Экономит free ключи (используются только при необходимости)

#### 1.4 Функция `get_active_key()` (Строки 288-303)

```python
def get_active_key(self, provider: ProviderKey) -> Optional[str]:
    """
    Get first available key for provider (backwards compatibility).
    Skips rate-limited keys (24h cooldown).
    """
    # For OpenRouter, use rotation logic
    if provider == ProviderType.OPENROUTER:
        return self.get_openrouter_key()

    self._ensure_provider_initialized(provider)
    for record in self.keys.get(provider, []):
        if record.is_available():
            return record.key

    logger.debug(f"[UnifiedKeyManager] No active key for provider: {provider}")
    return None
```

**Механизм для других провайдеров:**
- Возвращает ПЕРВЫЙ доступный ключ
- Не использует round-robin (просто итерирует в порядке добавления)
- Применимо для xAI, OpenAI, Anthropic и т.д.

---

## 2. 24-HOUR COOLDOWN SYSTEM

### 2.1 Класс `APIKeyRecord` (Строки 50-115)

#### Поле `rate_limited_at` (Строка 60)

```python
@dataclass
class APIKeyRecord:
    """Record for a stored API key with cooldown support."""
    provider: ProviderKey
    key: str
    alias: str = ""
    added_at: datetime = field(default_factory=datetime.now)
    last_rotated: Optional[datetime] = None
    active: bool = True
    # Rate limit tracking
    rate_limited_at: Optional[datetime] = None  # <-- TIMESTAMP при mark_rate_limited()
    failure_count: int = 0
    success_count: int = 0
    last_used: Optional[datetime] = None
```

**Хранилище:**
- `rate_limited_at: Optional[datetime]` - текущее время когда ключ заблокирован
- `None` если ключ не в cooldown
- Значение устанавливается в `mark_rate_limited()`

#### Метод `mark_rate_limited()` (Строки 83-87)

```python
def mark_rate_limited(self):
    """Mark key as rate-limited (starts 24h cooldown)."""
    self.rate_limited_at = datetime.now()
    self.failure_count += 1
    logger.info(f"[UnifiedKeyManager] Key {self.mask()} marked rate-limited until {self.rate_limited_at + RATE_LIMIT_COOLDOWN}")
```

**Логика:**
- **Строка 85:** Сохраняет текущее время (начало cooldown)
- **Строка 87:** Логирует когда закончится cooldown (now() + 24 часа)
- Инкрементирует счетчик ошибок

#### Метод `is_available()` (Строки 71-81)

```python
def is_available(self) -> bool:
    """Check if key is available (not in cooldown)."""
    if not self.active:
        return False
    if self.rate_limited_at:
        cooldown_end = self.rate_limited_at + RATE_LIMIT_COOLDOWN
        if datetime.now() < cooldown_end:
            return False
        # Cooldown expired, reset
        self.rate_limited_at = None
    return True
```

**ПРОВЕРКА COOLDOWN:**
- **Строка 75-78:** Если `rate_limited_at` установлен:
  - Вычисляет конец cooldown = `rate_limited_at + 24 часа`
  - Если текущее время < конец -> ключ ЕЩЕ в cooldown -> return False
  - Если текущее время >= конец -> cooldown истек -> сброс на None
- **Строка 81:** Возвращает True если ключ активен и не в cooldown

#### Метод `cooldown_remaining()` (Строки 96-102)

```python
def cooldown_remaining(self) -> Optional[timedelta]:
    """Get remaining cooldown time, or None if not in cooldown."""
    if not self.rate_limited_at:
        return None
    cooldown_end = self.rate_limited_at + RATE_LIMIT_COOLDOWN
    remaining = cooldown_end - datetime.now()
    return remaining if remaining.total_seconds() > 0 else None
```

**Расчет оставшегося времени:**
- Возвращает timedelta или None
- Используется для UI отображения

#### Константа `RATE_LIMIT_COOLDOWN` (Строка 28)

```python
RATE_LIMIT_COOLDOWN = timedelta(hours=24)
```

**Определение:** 24 часа = 86400 секунд

### 2.2 Методы на уровне UnifiedKeyManager

#### `report_failure()` (Строки 309-324)

```python
def report_failure(self, key: str, mark_cooldown: bool = True):
    """
    Report key failure.

    Args:
        key: The failed API key
        mark_cooldown: If True, start 24h cooldown
    """
    for provider_keys in self.keys.values():
        for record in provider_keys:
            if record.key == key:
                if mark_cooldown:
                    record.mark_rate_limited()
                else:
                    record.failure_count += 1
                return
```

**Использование:**
- Вызывается когда провайдер обнаруживает ошибку (403, 402, 429)
- `mark_cooldown=True` -> запускает 24h cooldown
- `mark_cooldown=False` -> только инкрементирует счетчик (для слабых ошибок)

#### `report_success()` (Строки 326-332)

```python
def report_success(self, key: str):
    """Report successful key use."""
    for provider_keys in self.keys.values():
        for record in provider_keys:
            if record.key == key:
                record.mark_success()
                return
```

**Использование:**
- Вызывается при успешном ответе
- Сбрасывает `failure_count` на 0
- Обновляет `last_used` время

---

## 3. PAID vs FREE KEY POOLS (OpenRouter)

### 3.1 Структура Хранения (Строки 551-563)

```python
# Format 3: Dict (OpenRouter style: {paid: key, free: [keys]})
elif isinstance(keys_data, dict):
    if paid_key := keys_data.get('paid'):
        if validator(paid_key):
            record = APIKeyRecord(provider=provider, key=paid_key, alias='paid')
            self.keys[provider].append(record)
            loaded += 1

    for i, key in enumerate(keys_data.get('free', [])):
        if key and validator(key):
            record = APIKeyRecord(provider=provider, key=key, alias=f'free_{i + 1}')
            self.keys[provider].append(record)
            loaded += 1
```

**Формат конфига:**
```json
{
  "api_keys": {
    "openrouter": {
      "paid": "sk-or-PAID_KEY",
      "free": ["sk-or-FREE_1", "sk-or-FREE_2", ...]
    }
  }
}
```

### 3.2 Приоритизация Paid Keys (Строка 468)

```python
def add_openrouter_key(self, key: str, is_paid: bool = False) -> Dict[str, Any]:
    """Add OpenRouter key with paid/free distinction."""
    if not self._validate_openrouter_key(key):
        return {"success": False, "message": "Invalid OpenRouter key format"}

    record = APIKeyRecord(
        provider=ProviderType.OPENROUTER,
        key=key,
        alias='paid' if is_paid else f'free_{len(self.keys[ProviderType.OPENROUTER])}'
    )

    if is_paid:
        self.keys[ProviderType.OPENROUTER].insert(0, record)  # <-- INSERT AT INDEX 0
    else:
        self.keys[ProviderType.OPENROUTER].append(record)     # <-- APPEND AT END
```

**Приоритет:**
- **Paid ключ:** вставляется в начало списка (index 0)
- **Free ключи:** добавляются в конец списка
- **Результат:** `get_openrouter_key()` ВСЕГДА возвращает paid ключ (index 0) по умолчанию

### 3.3 Сохранение Приоритета (Строки 585-589)

```python
if provider_name == 'openrouter':
    config['api_keys']['openrouter'] = {
        'paid': active_keys[0] if active_keys else None,  # <-- FIRST KEY = PAID
        'free': active_keys[1:] if len(active_keys) > 1 else []  # <-- REST = FREE
    }
```

**При сохранении:**
- Первый активный ключ -> `paid` поле
- Остальные -> `free` массив
- Структура переживает перезагрузку приложения

---

## 4. PROVIDER_REGISTRY XAI HANDLING

### 4.1 Exception для XAI (Строки 26-30)

```python
# Phase 80.39: Custom exception for xai key exhaustion
class XaiKeysExhausted(Exception):
    """Raised when all xai keys return 403 - signals to use OpenRouter fallback"""

    pass
```

**Назначение:**
- Специальный exception для сигнализации что все xAI ключи фейлились
- Используется для триггеринга OpenRouter fallback

### 4.2 XaiProvider Implementation (Строки 641-752)

#### Инициализация (Строки 661-668)

```python
api_key = self.config.api_key
if not api_key:
    from src.orchestration.services.api_key_service import APIKeyService

    api_key = APIKeyService().get_key("xai")

if not api_key:
    raise ValueError("x.ai API key not found")
```

**Логика:**
- Сначала проверяет `self.config.api_key`
- Если не установлен -> запрашивает через `APIKeyService.get_key("xai")`
- Если ничего нет -> raises ValueError

#### 403 Handling с Key Rotation (Строки 694-732)

```python
# Phase 80.39: Handle 403 with key rotation + OpenRouter fallback
# Phase 80.40: Fixed bugs - use singleton and correct attribute name
if response.status_code == 403:
    print(
        f"[XAI] ⚠️ 403 Forbidden - 24h timestamp limit, trying rotation..."
    )
    from src.utils.unified_key_manager import get_key_manager, ProviderType

    key_manager = get_key_manager()  # Use singleton, not new instance

    # Mark current key as rate-limited (24h cooldown)
    for record in key_manager.keys.get(
        ProviderType.XAI, []
    ):  # .keys not ._keys
        if record.key == api_key:
            record.mark_rate_limited()
            print(f"[XAI] Key {record.mask()} marked as rate-limited (24h)")
            break

    # Try next key
    next_key = key_manager.get_active_key(ProviderType.XAI)
    if next_key and next_key != api_key:
        print(f"[XAI] 🔄 Retrying with next key...")
        headers["Authorization"] = f"Bearer {next_key}"
        response = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers=headers,
            json=payload,
        )

    # Phase 80.39: If still 403, fallback to OpenRouter
    if response.status_code == 403:
        print(
            f"[XAI] ❌ All xai keys exhausted (403), falling back to OpenRouter..."
        )
        # Raise special exception to trigger OpenRouter fallback
        raise XaiKeysExhausted(
            f"All xai keys returned 403 - use OpenRouter for x-ai/{model}"
        )
```

**ПОТОК ОБРАБОТКИ 403:**

1. **Строка 696:** Обнаруживаем 403 статус
2. **Строка 702:** Получаем singleton `get_key_manager()`
3. **Строка 704-711:** Ищем текущий ключ в списке и вызываем `mark_rate_limited()`
   - Устанавливаем `rate_limited_at = datetime.now()`
   - Запускаем 24h cooldown
4. **Строка 714:** Получаем следующий доступный ключ через `get_active_key()`
5. **Строка 715-722:** Если найден другой ключ:
   - Обновляем Authorization header
   - Переповторяем запрос с новым ключом
6. **Строка 725-732:** Если ВСЕ ключи feyled:
   - Выбрасываем `XaiKeysExhausted` exception
   - Это сигнал для fallback на OpenRouter

### 4.3 Fallback механизм (Строки 903-917)

```python
try:
    result = await provider_instance.call(messages, model, tools, **kwargs)
    return result
except XaiKeysExhausted as e:
    # Phase 80.39: All xai keys got 403, fallback to OpenRouter
    print(
        f"[REGISTRY] XAI keys exhausted (403), using OpenRouter fallback for {model}..."
    )
    openrouter_provider = registry.get(Provider.OPENROUTER)
    if openrouter_provider:
        # Convert model to OpenRouter format: grok-4 -> x-ai/grok-4
        # MARKER-PROVIDER-004-FIX: Remove double x-ai/xai/ prefix
        clean_model = model.replace("xai/", "").replace("x-ai/", "")
        openrouter_model = f"x-ai/{clean_model}"
        result = await openrouter_provider.call(
            messages, openrouter_model, tools, **kwargs
        )
        return result
    raise
```

**Fallback Логика:**
- Ловим `XaiKeysExhausted` exception
- Получаем OpenRouter провайдер из registry
- Конвертируем модель в OpenRouter формат: `grok-4` -> `x-ai/grok-4`
- Повторяем запрос через OpenRouter

---

## 5. API_KEY_SERVICE МЕТОДЫ

### 5.1 `get_key(provider)` (Строки 48-84)

```python
def get_key(self, provider: str) -> Optional[str]:
    """
    Get active key for provider.

    Args:
        provider: Provider name (e.g., 'openrouter', 'gemini', 'ollama')

    Returns:
        API key string or None if not available
    """
    # Phase 80.38: Complete provider map with ALL supported providers
    # Phase 80.41: Added 'google' alias for 'gemini'
    provider_map = {
        'openrouter': ProviderType.OPENROUTER,
        'gemini': ProviderType.GEMINI,
        'google': ProviderType.GEMINI,     # Alias for gemini
        'ollama': ProviderType.OLLAMA,
        'nanogpt': ProviderType.NANOGPT,
        'xai': ProviderType.XAI,           # x.ai (Grok)
        'openai': ProviderType.OPENAI,     # OpenAI
        'anthropic': ProviderType.ANTHROPIC,  # Anthropic
        'tavily': ProviderType.TAVILY,     # Tavily search
    }

    provider_type = provider_map.get(provider.lower())
    if not provider_type:
        print(f"      ⚠️  Unknown provider: {provider}")
        return None

    key = self.key_manager.get_active_key(provider_type)

    if key:
        print(f"      🔑 Key injected for {provider}")
        return key
    else:
        print(f"      ⚠️  No active key for {provider}")
        return None
```

**Механизм:**
- Вход: строка имя провайдера (e.g., "xai", "openrouter")
- Маппирует на `ProviderType` enum
- Делегирует на `key_manager.get_active_key()`
- Возвращает ключ или None

### 5.2 `report_failure()` (Строки 124-132)

```python
def report_failure(self, provider: str, key: str):
    """
    Report key failure for rotation.

    Args:
        provider: Provider name
        key: Failed API key
    """
    self.key_manager.report_failure(key)
```

**Использование:**
- Вызывается при ошибке API
- Делегирует на `UnifiedKeyManager.report_failure()`
- Запускает 24h cooldown (если провайдер отправит 403/429/402)

### 5.3 `add_key()` (Строки 134-170)

```python
def add_key(self, provider: str, key: str) -> Dict[str, Any]:
    """
    Add API key via chat command.
    Phase 57.12: Supports dynamic providers via UnifiedKeyManager.

    Args:
        provider: Provider name
        key: API key to add

    Returns:
        Dict with success status and message
    """
    # Phase 57.12: Use UnifiedKeyManager's dynamic provider support
    # No need for hardcoded map - manager handles any provider
    provider_lower = provider.lower()

    # Try to find in ProviderType enum first
    provider_key = None
    for pt in ProviderType:
        if pt.value == provider_lower:
            provider_key = pt
            break

    # If not in enum, use string key (dynamic provider)
    if provider_key is None:
        provider_key = provider_lower

    success = self.key_manager.add_key_direct(provider_key, key)

    if success:
        return {
            'success': True,
            'message': f'Key added for {provider}',
            'masked_key': self.key_manager.mask_key(key)
        }
    else:
        return {'success': False, 'error': 'Invalid key format'}
```

**Логика Добавления:**
- Попытка найти провайдер в `ProviderType` enum
- Если не найден -> использует строку как провайдер (динамичес7ий)
- Вызывает валидацию (через `add_key_direct`)
- Возвращает masked ключ (для безопасности)

---

## 6. FLOW DIAGRAM

### 6.1 Стандартный Flow Получения Ключа

```
Request для Model X
        ↓
determine_provider() в orchestrator
        ↓
call_model(provider, model, messages)
        ↓
ProviderRegistry.call_model()
        ↓
provider_instance.call()
        ↓
┌─────────────────────────────────┐
│ get_key() или config.api_key    │
│ (зависит от провайдера)         │
└────────────┬────────────────────┘
             ↓
    APIKeyService.get_key(provider)
             ↓
    key_manager.get_active_key(ProviderType)
             ↓
    ┌─────────────────────────────────┐
    │ Для OpenRouter:                 │
    │ get_openrouter_key()            │
    │ (с round-robin ротацией)        │
    │                                 │
    │ Для других:                     │
    │ вернуть первый is_available()    │
    └────────────┬────────────────────┘
                 ↓
      ✅ API Key Successfully Retrieved
```

### 6.2 Flow при 403 Error (xAI)

```
XaiProvider.call()
    ↓
response.status_code == 403
    ↓
get_key_manager() [singleton]
    ↓
для каждого record в ProviderType.XAI:
    если record.key == current_key
        ↓
    record.mark_rate_limited()
        ↓
    rate_limited_at = datetime.now()
    failure_count += 1
    запланировать cooldown до (now + 24h)
    ↓
key_manager.get_active_key(ProviderType.XAI)
    ↓
    ┌─────────────────────────────────────────┐
    │ Если найден next_key:                   │
    │ - Обновить Authorization header         │
    │ - Переповторить запрос (retry)          │
    │ - Если успешно → return result          │
    │ - Если 403 снова → continue             │
    │                                         │
    │ Если нет next_key (все в cooldown):     │
    │ - raise XaiKeysExhausted                │
    └────────────┬────────────────────────────┘
                 ↓
        ProviderRegistry catches XaiKeysExhausted
                 ↓
        Fallback: OpenRouter.call(x-ai/model)
                 ↓
        ✅ Response через OpenRouter
```

### 6.3 Flow проверки Cooldown

```
is_available() called
    ↓
if not self.active:
    return False  # Неактивный ключ
    ↓
if self.rate_limited_at:
    ↓
    cooldown_end = rate_limited_at + timedelta(hours=24)
    ↓
    if datetime.now() < cooldown_end:
        return False  # ЕЩЕ в cooldown
    else:
        rate_limited_at = None  # Cooldown истек
        return True  # Ключ доступен снова
else:
    return True  # Никогда не было в cooldown
```

---

## 7. ОЧЕНЬ ВАЖНЫЕ ДЕТАЛИ

### 7.1 Singleton Pattern (Строки 709-721)

```python
_unified_manager: Optional[UnifiedKeyManager] = None

def get_key_manager() -> UnifiedKeyManager:
    """
    Get global UnifiedKeyManager instance (singleton).
    This is the ONLY key manager you need!
    """
    global _unified_manager
    if _unified_manager is None:
        _unified_manager = UnifiedKeyManager()
    return _unified_manager
```

**КРИТИЧНО:**
- Один глобальный instance на весь процесс
- Все provideры используют ОДИН manager
- Состояние cooldown глобально видимо
- **Phase 80.40:** Специально упоминает "use singleton, not new instance"

### 7.2 Различия между Провайдерами

#### OpenRouter (Строка 269-270)
```python
if provider_key == ProviderType.OPENROUTER:
    return self.get_openrouter_key()
```
- Использует **round-robin rotation** с индексом
- Приоритизирует **paid** ключи (index 0)

#### Остальные провайдеры (Строка 273-275)
```python
for record in self.keys.get(provider_key, []):
    if record.is_available():
        return record.key
```
- Используют **простой поиск первого доступного**
- Применимо для xAI, OpenAI, Anthropic, Gemini

### 7.3 Rate Limiting Decision Tree

```
API вернул ОШИБКУ

├─ 402 (Payment Required)?
│  └─ mark_cooldown = True
│     report_failure(key, mark_cooldown=True)
│     → 24h cooldown
│
├─ 403 (Forbidden)?
│  ├─ (xAI специфичный) → XaiProvider.call() handles
│  │  └─ mark_rate_limited() для текущего ключа
│  │  └─ retry с next_key
│  │  └─ если все failed → raise XaiKeysExhausted
│  │
│  └─ (OpenRouter) → report_failure(mark_cooldown=True)
│     └─ 24h cooldown
│
├─ 429 (Too Many Requests)?
│  └─ mark_cooldown = True
│     → 24h cooldown
│
├─ 401/500/timeout?
│  └─ mark_cooldown = False
│     → только failure_count++
│     → без 24h cooldown
│
└─ 200/success?
   └─ report_success(key)
      → failure_count = 0
      → last_used = now()
```

### 7.4 Config Format

**config.json:**
```json
{
  "api_keys": {
    "openrouter": {
      "paid": "sk-or-PAID",
      "free": ["sk-or-FREE1", "sk-or-FREE2"]
    },
    "xai": ["xai-key1", "xai-key2"],
    "gemini": "AIzaSy...",
    "openai": ["sk-proj-...", "sk-proj-..."]
  }
}
```

**При загрузке:**
- OpenRouter dict → разделяется на paid (index 0) + free (index 1+)
- Остальные провайдеры → списки или одиночные ключи

---

## 8. ИНТЕГРАЦИОННЫЕ ТОЧКИ

### 8.1 Вызовы из XaiProvider

**Файл:** `/src/elisya/provider_registry.py` (строки 700-714)

```python
from src.utils.unified_key_manager import get_key_manager, ProviderType

key_manager = get_key_manager()
# Mark rate-limited
for record in key_manager.keys.get(ProviderType.XAI, []):
    if record.key == api_key:
        record.mark_rate_limited()  # ← Самый критичный метод
        break
# Get next
next_key = key_manager.get_active_key(ProviderType.XAI)
```

### 8.2 Вызовы из APIKeyService

**Файл:** `/src/orchestration/services/api_key_service.py`

```python
# Инициализация (строка 25)
self.key_manager = KeyManager()

# get_key() (строка 77)
key = self.key_manager.get_active_key(provider_type)

# report_failure() (строка 132)
self.key_manager.report_failure(key)

# add_key() (строка 161)
success = self.key_manager.add_key_direct(provider_key, key)
```

---

## 9. СОСТОЯНИЕ КЛЮЧЕЙ (Метод get_status)

**Строки 104-115:**
```python
def get_status(self) -> Dict[str, Any]:
    """Get key status for display."""
    cooldown = self.cooldown_remaining()
    return {
        'masked': self.mask(),
        'alias': self.alias,
        'active': self.active,
        'available': self.is_available(),
        'success_count': self.success_count,
        'failure_count': self.failure_count,
        'cooldown_hours': round(cooldown.total_seconds() / 3600, 1) if cooldown else None
    }
```

**Выводит:**
- Masked версию ключа
- Статус активности
- Доступность (не в cooldown?)
- Счетчики успеха/ошибок
- Оставшееся время cooldown в часах

---

## 10. КЛЮЧЕВЫЕ БАГИ ЧТО БЫЛИ ИСПРАВЛЕНЫ

### Bug 1: Неправильный атрибут (Phase 80.40, строка 707)
```python
# БЫЛО:
for record in key_manager._keys.get(ProviderType.XAI, []):

# ИСПРАВЛЕНО:
for record in key_manager.keys.get(ProviderType.XAI, []):
```
- `_keys` (private) → `keys` (public)

### Bug 2: Новый instance вместо singleton (Phase 80.40, строка 702)
```python
# БЫЛО:
key_manager = UnifiedKeyManager()  # NEW instance!

# ИСПРАВЛЕНО:
key_manager = get_key_manager()  # Singleton!
```

### Bug 3: Double prefix в OpenRouter fallback (строки 911-913)
```python
# БЫЛО: может быть "xai/xai/grok-4" или "x-ai/x-ai/grok-4"

# ИСПРАВЛЕНО:
clean_model = model.replace("xai/", "").replace("x-ai/", "")
openrouter_model = f"x-ai/{clean_model}"
```

---

## SUMMARY

| Компонент | Функция | Строки |
|-----------|---------|--------|
| **Ротация** | `get_openrouter_key()` | 185-222 |
| | `rotate_to_next()` | 224-235 |
| | `reset_to_paid()` | 237-244 |
| **Cooldown** | `mark_rate_limited()` | 83-87 |
| | `is_available()` | 71-81 |
| | `cooldown_remaining()` | 96-102 |
| | `RATE_LIMIT_COOLDOWN` | 28 |
| **Paid/Free** | `add_openrouter_key()` | 456-477 |
| | Config save/load | 551-563, 585-589 |
| **XAI Integration** | `XaiProvider.call()` | 694-732 |
| | Exception | 26-30, 730-732 |
| | Fallback | 903-917 |
| **Singleton** | `get_key_manager()` | 712-721 |

**Все 24-часовые cooldown механизмы используют `datetime.now()` и хранятся в памяти.**
**Состояние НЕ persists между перезагрузками приложения.**
**На перезагрузку - все ключи становятся доступны.**

