# Гайд по настройке Elysia: Пошаговая инструкция (с интеграцией EmbeddingGemma)

Elysia — это open-source фреймворк от Weaviate для создания agentic RAG-систем (агентных Retrieval-Augmented Generation). Он позволяет строить ИИ-агентов с деревьями решений, динамическим чанкингом данных, фидбеком от пользователей и интеграцией с векторными базами. Актуально на сентябрь 2025 года (данные из официальных источников: GitHub и Weaviate blog).

Elysia не является моделью, как EmbeddingGemma, а фреймворком, который может использовать Gemma как embedding-модель через Weaviate. Интеграция с Gemma **рекомендуется**, если тебе нужны лёгкие, on-device эмбеддинги для семантического поиска в твоём Clade (монтаж на базе ИИ). Weaviate уже поддерживает EmbeddingGemma напрямую (см. notebook от Weaviate: https://github.com/weaviate/weaviate-examples/blob/main/notebooks/embeddinggemma.ipynb). Это позволит Elysia использовать Gemma для векторизации данных в коллекциях.

Гайд разделён на: **установку Elysia**, **настройку Weaviate**, **интеграцию с EmbeddingGemma** и **тестирование**. Всё на Python (рекомендуется 3.12).

## Системные требования
- **ОС**: Windows 10/11, Linux (Ubuntu 20.04+), macOS (12.0+).
- **Python**: 3.10–3.12 (рекомендуется 3.12 для PyPi).
- **RAM**: Минимум 8 ГБ (для локального Weaviate + моделей).
- **Дополнительно**: Docker для локального Weaviate; API-ключи для моделей (OpenAI/OpenRouter для LLM, Hugging Face для embedders).
- **Для Gemma**: Установи её отдельно (см. предыдущий гайд), но Weaviate интегрирует через Hugging Face.

## Зависимости
- Python 3.12: [python.org/downloads](https://www.python.org/downloads/).
- pip: Устанавливается с Python.
- Weaviate: Локально (Docker) или облако (Weaviate Cloud).
- Для интеграции: Hugging Face Transformers (pip install transformers).
- Опционально: Ollama для локальных моделей.

## Шаг 1: Установка Elysia
1. Создай виртуальное окружение:
   ```bash
   python3.12 -m venv elysia_env
   source elysia_env/bin/activate  # Linux/macOS
   elysia_env\Scripts\activate  # Windows
   ```
2. Установи Elysia:
   ```bash
   pip install elysia-ai
   ```
   (Альтернатива: Клонируй GitHub `git clone https://github.com/weaviate/elysia` и `pip install -e .` для dev-версии).

## Шаг 2: Настройка Weaviate (база для Elysia)
Elysia работает с Weaviate для хранения данных и retrieval.

### Вариант 1: Облачный Weaviate (рекомендуется для старта)
1. Создай бесплатный sandbox-кластер: [console.weaviate.cloud](https://console.weaviate.cloud/).
2. Получи URL кластера (WCD_URL) и API-ключ (WCD_API_KEY).

### Вариант 2: Локальный Weaviate (Docker)
1. Установи Docker: [docker.com](https://www.docker.com/).
2. Запусти Weaviate:
   ```bash
   docker run -d -p 8080:8080 -p 50051:50051 --name weaviate -v weaviate_data:/var/lib/weaviate cr.weaviate.io/semitechnologies/weaviate:1.26.2
   ```
3. URL: http://localhost:8080, без API-ключа (для локалки).

Добавь данные в Weaviate (пример: через quickstart на [weaviate.io/developers/weaviate/quickstart](https://weaviate.io/developers/weaviate/quickstart)).

## Шаг 3: Конфигурация Elysia
1. Создай файл `.env` в корне проекта:
   ```
   WCD_URL=your_weaviate_url  # e.g., https://your-cluster.weaviate.network
   WCD_API_KEY=your_api_key
   WEAVIATE_IS_LOCAL=False  # True для локального
   OPENAI_API_KEY=your_openai_key  # Или OPENROUTER_API_KEY для других моделей
   ```
   (Для локальных моделей: Установи Ollama и укажи в настройках).

2. В Python: Импортируй и настрой:
   ```python
   from elysia.preprocessing.collection import preprocess
   preprocess(collection_names=["YourCollectionName"])  # Подготовь коллекции для агентов
   ```

3. Запусти веб-апп:
   ```bash
   elysia start
   ```
   - Открой браузер: http://localhost:8080 (или порт по умолчанию).
   - В Settings: Добавь API-ключи, Weaviate детали, модели (e.g., Gemini для теста, но мы добавим Gemma).
   - В Data tab: Analyze коллекции (LLM-генерация описаний, примеров запросов).

## Шаг 4: Интеграция с EmbeddingGemma
Weaviate использует модули для embedders. EmbeddingGemma (google/embeddinggemma-300m) интегрируется через `text2vec-huggingface` модуль.

1. Включи модуль в Weaviate (для облака: Автоматически; для Docker: Добавь в docker-compose.yml):
   ```yaml
   environment:
     ENABLE_MODULES: text2vec-huggingface
     TRANSFORMERS_INFERENCE_API_URL: http://localhost:8081  # Или Hugging Face Inference API
   ```

2. Создай коллекцию в Weaviate с Gemma-embedder (Python-клиент):
   ```python
   import weaviate
   from weaviate.classes.config import Configure, Property, DataType

   client = weaviate.connect_to_local()  # Или connect_to_wcs для облака

   client.collections.create(
       name="YourCollection",
       vectorizer_config=Configure.Vectorizer.text2vec_huggingface(
           model="google/embeddinggemma-300m"  # Укажи модель из HF
       ),
       properties=[
           Property(name="text", data_type=DataType.TEXT),
       ]
   )
   ```
   (Для HF Inference: Укажи API-ключ в env: HUGGINGFACE_API_TOKEN).

3. В Elysia: Используй эту коллекцию в агентах. Elysia автоматически retrieval из Weaviate, где эмбеддинги от Gemma.
   - Пример: В Tree() добавь tool для Gemma-based поиска.

(Подробный notebook: https://github.com/weaviate/weaviate-examples/blob/main/notebooks/embeddinggemma.ipynb — там тесты на MTEB бенчмарках).

## Шаг 5: Тестирование и использование
1. **Python-пример (agentic RAG с Gemma)**:
   ```python
   from elysia import Tree

   tree = Tree()
   response, objects = tree(
       "Найди похожие видео-сцены в коллекции",  # Твой монтаж-クエリ
       collection_names=["YourCollection"]  # С Gemma-embeddings
   )
   print(response)
   ```

2. **Веб-апп**: В Chat tab задай запросы. Включи feedback (лайки/дизлайки для улучшения).
3. **Для Clade**: Интегрируй Elysia как агент: Используй Tree() для анализа видео-текста (эмбеддинги от Gemma), затем монтируй по результатам.

## Примечания
- Если Gemma не нужна: Elysia работает с дефолтными embedders (e.g., text2vec-openai).
- Обновления 2025: Elysia в активной разработке; проверь GitHub на fixes.
- Ресурсы: 
  - Доки: [weaviate.github.io/elysia](https://weaviate.github.io/elysia).
  - Blog: [weaviate.io/blog/elysia-agentic-rag](https://weaviate.io/blog/elysia-agentic-rag).
  - Weaviate Models: [weaviate.io/developers/weaviate/model-providers](https://weaviate.io/developers/weaviate/model-providers).

Если что-то не сработает (e.g., ошибки с моделями), проверь логи или спроси детали! 😊