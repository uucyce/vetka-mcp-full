"""
VETKA Memory Manager - Triple Write System

@file memory_manager.py
@status ACTIVE
@phase Phase 36 (semantic_search added)
@calledBy orchestrator_with_elisya.py
@lastAudit 2026-01-04

Features:
- Triple Write: Qdrant + Weaviate + ChangeLog
- UUID fix, Gemma support, input validation
- Session cleanup, pathlib integration
- Optimized logging (no noise, singleton init)
"""
import json
import uuid
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Optional imports — graceful degradation если нет зависимостей
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False

# Logger (configured by main.py, no basicConfig here)
logger = logging.getLogger("VetkaMemory")

# Singleton flag to log initialization only ONCE
_INIT_LOGGED = False


class MemoryManager:
    """
    Triple Write Architecture for VETKA Phase 9

    РОЛИ КАЖДОЙ БД:

    1. ChangeLog (JSON файл)
       - Immutable audit trail
       - Все события последовательно
       - Backup и recovery
       - Источник истины при конфликтах

    2. Weaviate (Graph DB)
       - Structured metadata + relationships
       - Поле 'score' = number (float 0-1)
       - Поле 'student_level' = int (0-5)
       - Используется для: связи агентов, историю обучения

    3. Qdrant (Vector DB)
       - Embedded vectors для семантического поиска
       - Поле 'content' → embedding → vector поиск
       - Используется для: few-shot retrieval, similarity search

    EXAMPLE WORKFLOW:
        entry = {
            'workflow_id': 'abc123',
            'score': 0.85,              # <- float!
            'content': 'Solution code', # <- embedded to vector
            'student_level': 2,         # <- int!
            'timestamp': '2025-12-13...'
        }

        Triple Write:
        1. ChangeLog.append(entry)          <- immutable
        2. Weaviate.create(entry)           <- score=number
        3. Qdrant.upsert(vector, entry)     <- content->vector

    Если один слой упал — остальные живы.
    ChangeLog — всегда источник истины.
    """

    # ✅ PATCH #2: Supported embedding models with metadata
    EMBEDDING_MODELS = {
        "embeddinggemma:300m": {
            "size": 768,
            "quality": 4.8,
            "priority": 1,
            "description": "Google Gemma 2 (300M) — Best quality (recommended)"
        },
        "nomic-embed-text": {
            "size": 768,
            "quality": 4.5,
            "priority": 2,
            "description": "Nomic — Fast & reliable (fallback)"
        },
    }

    def __init__(
        self,
        weaviate_url: str = "http://localhost:8080",
        qdrant_url: str = "http://localhost:6333",
        changelog_path: str = "data/changelog.jsonl",
        embedding_model: str = "auto"  # ✅ PATCH #2: auto-detection
    ):
        global _INIT_LOGGED

        self.weaviate_url = weaviate_url
        self.qdrant_url = qdrant_url
        self.changelog_path = changelog_path

        # ✅ PATCH #2: Auto-select best available embedding model
        if embedding_model == "auto":
            self.embedding_model = self._select_best_embedding_model()
        else:
            self.embedding_model = embedding_model

        # Инициализация клиентов
        self.session = requests.Session() if HAS_REQUESTS else None
        self.qdrant = self._init_qdrant() if HAS_QDRANT else None

        # ✅ PATCH #7: Use pathlib for cross-platform paths
        changelog_file = Path(changelog_path)
        changelog_file.parent.mkdir(parents=True, exist_ok=True)

        self._ensure_weaviate_schemas()
        self._ensure_qdrant_collection()

        # ✅ PATCH #8: Log init only ONCE (singleton pattern for logging)
        if not _INIT_LOGGED:
            logger.info(f"MemoryManager initialized: Triple Write READY (embedding: {self.embedding_model})")
            _INIT_LOGGED = True

    def _select_best_embedding_model(self) -> Optional[str]:
        """✅ PATCH #2: Auto-select best available embedding model"""
        global _INIT_LOGGED

        if not HAS_OLLAMA:
            if not _INIT_LOGGED:
                logger.warning("Ollama not available — embeddings disabled")
            return None

        # Try models in priority order
        for model_name in sorted(
            self.EMBEDDING_MODELS.keys(),
            key=lambda m: self.EMBEDDING_MODELS[m]["priority"]
        ):
            try:
                # Test if model exists
                result = ollama.embeddings(
                    model=model_name,
                    prompt="test"
                )
                if result.get("embedding"):
                    config = self.EMBEDDING_MODELS[model_name]
                    if not _INIT_LOGGED:
                        logger.info(
                            f"Using {model_name} (quality: {config['quality']}/5.0, size: {config['size']}D)"
                        )
                    return model_name
            except Exception as e:
                logger.debug(f"{model_name} unavailable: {e}")

        if not _INIT_LOGGED:
            logger.warning("No embedding model available")
        return None

    def _get_embedding_dim(self) -> int:
        """✅ PATCH #2+#3: Get vector dimension for current model (not hardcoded)"""
        if not self.embedding_model:
            return 768  # default
        
        return self.EMBEDDING_MODELS.get(self.embedding_model, {}).get("size", 768)

    def _init_qdrant(self) -> Optional["QdrantClient"]:
        """Инициализирует Qdrant клиент"""
        global _INIT_LOGGED
        try:
            client = QdrantClient(url=self.qdrant_url)
            # Проверяем связь
            client.get_collections()
            if not _INIT_LOGGED:
                logger.debug(f"Qdrant connected: {self.qdrant_url}")

                # Log version info (non-blocking warning)
                try:
                    import qdrant_client
                    client_version = getattr(qdrant_client, '__version__', 'unknown')
                    logger.debug(f"Qdrant client version: {client_version}")

                    # Check for potential version mismatch (informational only)
                    if client_version != 'unknown':
                        major_version = int(client_version.split('.')[0])
                        if major_version >= 2:
                            logger.debug(
                                f"ℹ️  Qdrant client v{client_version} - ensure server compatibility"
                            )
                except Exception as ve:
                    logger.debug(f"Could not verify Qdrant version: {ve}")

            return client
        except Exception as e:
            if not _INIT_LOGGED:
                logger.warning(f"Qdrant connection failed: {e}")
            return None

    def _ensure_weaviate_schemas(self):
        """Создаём схемы в Weaviate если их нет"""
        global _INIT_LOGGED

        if not HAS_REQUESTS or not self.session:
            logger.debug("Requests not available — skipping Weaviate schema setup")
            return

        try:
            # Проверяем, живо ли Weaviate
            response = self.session.get(f"{self.weaviate_url}/v1/meta", timeout=5)
            if response.status_code != 200:
                logger.debug(f"Weaviate not responding: {response.status_code}")
                return
        except Exception as e:
            logger.debug(f"Weaviate unreachable: {e}")
            return

        # Схема для VetkaElisyaLog (основная)
        schema = {
            "class": "VetkaElisyaLog",
            "properties": [
                {"name": "workflow_id", "dataType": ["string"]},
                {"name": "speaker", "dataType": ["string"]},
                {"name": "content", "dataType": ["text"]},
                {"name": "branch_path", "dataType": ["string"]},
                {"name": "score", "dataType": ["number"]},
                {"name": "timestamp", "dataType": ["string"]},
                {"name": "entry_type", "dataType": ["string"]},
            ]
        }

        try:
            # Проверяем наличие класса
            url = f"{self.weaviate_url}/v1/schema"
            resp = self.session.get(url, timeout=5)
            if resp.status_code == 200:
                classes = [c.get("class") for c in resp.json().get("classes", [])]
                if "VetkaElisyaLog" not in classes:
                    resp = self.session.post(f"{url}/VetkaElisyaLog", json=schema, timeout=5)
                    if resp.status_code in [200, 201]:
                        logger.debug("Weaviate schema created: VetkaElisyaLog")
        except Exception as e:
            logger.debug(f"Failed to create Weaviate schema: {e}")

    def _ensure_qdrant_collection(self):
        """✅ PATCH #3: Создаём collection в Qdrant с параметризованным размером вектора"""
        global _INIT_LOGGED

        if not HAS_QDRANT or not self.qdrant:
            logger.debug("Qdrant not available — skipping collection setup")
            return

        try:
            self.qdrant.get_collection("vetka_elisya")
            logger.debug("Qdrant collection exists: vetka_elisya")
        except Exception:
            try:
                # ✅ PATCH #3: Dynamic vector size from model config
                embedding_dim = self._get_embedding_dim()

                self.qdrant.create_collection(
                    collection_name="vetka_elisya",
                    vectors_config=VectorParams(
                        size=embedding_dim,  # ✅ Not hardcoded
                        distance=Distance.COSINE
                    )
                )
                if not _INIT_LOGGED:
                    logger.info(f"Qdrant collection created: vetka_elisya (vector_size: {embedding_dim}D)")
            except Exception as e:
                logger.debug(f"Failed to create Qdrant collection: {e}")

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Delegate to unified EmbeddingService (Phase 36.1)"""
        from src.utils.embedding_service import get_embedding
        return get_embedding(text)

    def triple_write(self, entry: Dict[str, Any]) -> str:
        """
        Triple Write: ChangeLog → Weaviate → Qdrant
        Returns: entry_id
        
        ✅ PATCH #4: Input validation for score, workflow_id
        
        Даже если Weaviate и Qdrant упали — ChangeLog всегда сохранится.
        """
        entry_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        # ✅ PATCH #4: Validate and coerce score
        score = entry.get("score")
        if score is not None:
            try:
                score = float(score)
                if not (0 <= score <= 1):
                    logger.warning(f"Score out of range (0-1): {score}")
                    score = None
            except (TypeError, ValueError):
                logger.warning(f"Invalid score type: {type(score)}")
                score = None
        
        # ✅ PATCH #4: Validate workflow_id
        workflow_id = str(entry.get("workflow_id", "unknown")).strip()
        if not workflow_id or len(workflow_id) > 100:
            workflow_id = "unknown"

        # ✅ PATCH #4: Sanitize all strings
        write_entry = {
            "id": entry_id,
            "workflow_id": workflow_id,
            "speaker": str(entry.get("speaker", "system"))[:100],
            "content": str(entry.get("content", ""))[:5000],  # лимит на размер
            "branch_path": str(entry.get("branch_path", "unknown"))[:500],
            "score": score,  # ✅ validated
            "entry_type": str(entry.get("type", "log"))[:50],
            "timestamp": timestamp,
            "raw": entry
        }

        try:
            # 1️⃣ ChangeLog (КРИТИЧНАЯ ОПЕРАЦИЯ — всегда должна успешиться)
            self._changelog_write(write_entry)
            logger.debug(f"[ChangeLog] {entry_id[:8]} saved")

            # 2️⃣ Weaviate (best-effort)
            self._weaviate_write(write_entry)

            # 3️⃣ Qdrant (best-effort)
            self._qdrant_write(write_entry)

            logger.debug(f"[Triple Write] {entry_id[:8]} complete")
            return entry_id

        except Exception as e:
            logger.error(f"Triple Write FAILED (but ChangeLog saved): {e}")
            return entry_id

    def _changelog_write(self, entry: Dict):
        """Пишет в ChangeLog (append-only)"""
        try:
            changelog_file = Path(self.changelog_path)
            with open(changelog_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            logger.error(f"ChangeLog write FAILED: {e}")
            raise  # Re-raise — это критично

    def _weaviate_write(self, entry: Dict):
        """
        Пишет в Weaviate (best-effort) с валидацией типов данных.

        ✅ PATCH #9: Типы данных валидированы для предотвращения 422 ошибок
        """
        if not self.session:
            return

        try:
            # Валидируем типы данных перед отправкой
            def safe_str(val, max_len: int = 5000) -> str:
                """Конвертировать в строку с ограничением длины"""
                if val is None:
                    return ""
                return str(val)[:max_len]

            def safe_float(val) -> float:
                """Конвертировать в float (для score)"""
                if val is None:
                    return 0.0
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return 0.0

            url = f"{self.weaviate_url}/v1/objects"
            payload = {
                "class": "VetkaElisyaLog",
                "properties": {
                    "workflow_id": safe_str(entry.get("workflow_id"), 100),
                    "speaker": safe_str(entry.get("speaker"), 100),
                    "content": safe_str(entry.get("content"), 5000),
                    "branch_path": safe_str(entry.get("branch_path"), 500),
                    "score": safe_float(entry.get("score")),
                    "timestamp": safe_str(entry.get("timestamp"), 50),
                    "entry_type": safe_str(entry.get("entry_type"), 50),
                }
            }
            response = self.session.post(url, json=payload, timeout=5)
            if response.status_code not in [200, 201]:
                # Log detailed error for 422
                if response.status_code == 422:
                    logger.debug(f"Weaviate 422 (type mismatch): {response.text[:200]}")
                else:
                    logger.debug(f"Weaviate write failed: {response.status_code}")
        except Exception as e:
            logger.debug(f"Weaviate write error: {e}")

    def _qdrant_write(self, entry: Dict):
        """
        ✅ PATCH #1: Пишет в Qdrant с использованием string ID (guaranteed unique)
        (best-effort)
        """
        if not self.qdrant:
            return
        
        try:
            vector = self._get_embedding(entry.get("content", ""))
            if not vector:
                logger.debug("No vector — skipping Qdrant write")
                return
            
            # ✅ PATCH #1: Use string ID directly (guaranteed unique, no hash collision)
            point_id = entry.get("id")
            
            self.qdrant.upsert(
                collection_name="vetka_elisya",
                points=[PointStruct(id=point_id, vector=vector, payload=entry)]
            )
            logger.debug(f"[Qdrant] {point_id[:8]} saved")
        except Exception as e:
            logger.debug(f"Qdrant write error: {e}")

    def save_feedback(
        self,
        evaluation_id: str,
        task: str,
        output: str,
        rating: str,
        correction: str = "",
        score: Optional[float] = None
    ) -> bool:
        """Сохраняет пользовательский фидбек → используется для few-shot"""
        entry = {
            "type": "user_feedback",
            "evaluation_id": evaluation_id,
            "task": task,
            "output": output,
            "rating": rating,
            "correction": correction,
            "score": score,
            "speaker": "user"
        }
        try:
            self.triple_write(entry)
            return True
        except Exception as e:
            logger.error(f"save_feedback failed: {e}")
            return False

    def get_high_score_examples(
        self,
        task_type: str = "code",
        min_score: float = 0.8,
        limit: int = 3
    ) -> List[Dict]:
        """Возвращает high-score примеры для few-shot (из ChangeLog)"""
        examples = []
        try:
            changelog_file = Path(self.changelog_path)
            if not changelog_file.exists():
                return examples
            
            with open(changelog_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        score = entry.get("score")
                        if score and score >= min_score:
                            examples.append(entry)
                            if len(examples) >= limit:
                                break
                    except Exception:
                        continue
            
            logger.debug(f"Found {len(examples)} high-score examples")
            return examples
        except Exception as e:
            logger.debug(f"get_high_score_examples failed: {e}")
            return []

    def get_similar_context(
        self,
        query: str,
        workflow_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Семантический поиск (Qdrant) + fallback на ChangeLog"""
        results = []
        
        # 1️⃣ Пробуем Qdrant (если доступен)
        if self.qdrant:
            try:
                vector = self._get_embedding(query)
                if vector:
                    qdrant_results = self.qdrant.search(
                        collection_name="vetka_elisya",
                        query_vector=vector,
                        limit=limit
                    )
                    results = [hit.payload for hit in qdrant_results]
                    logger.debug(f"Qdrant search returned {len(results)} results")
                    return results
            except Exception as e:
                logger.debug(f"Qdrant search failed: {e}")
        
        # 2️⃣ Fallback на ChangeLog (текстовый поиск)
        try:
            query_lower = query.lower()
            changelog_file = Path(self.changelog_path)
            with open(changelog_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if query_lower in entry.get("content", "").lower():
                            if not workflow_id or entry.get("workflow_id") == workflow_id:
                                results.append(entry)
                                if len(results) >= limit:
                                    break
                    except Exception:
                        continue
            
            logger.debug(f"ChangeLog fallback returned {len(results)} results")
            return results
        except Exception as e:
            logger.debug(f"ChangeLog search failed: {e}")
            return []

    # New method for Task 3: Search for files similar to a given node_path
    async def search_similar(self, node_path: str, limit: int = 5) -> List[Dict]:
        """
        Ищет файлы с похожим контентом с помощью Qdrant.

        Args:
            node_path: Путь к файлу-источнику для поиска (ищет его вектор).
            limit: Максимальное количество результатов.

        Returns:
            List[Dict]: Список похожих файлов (Dict) с ключом 'score'.
        """
        if not self.qdrant or not self.embedding_model:
            logger.debug("Qdrant or embedding model not available - skipping search_similar")
            return []

        try:
            # 1. Найти вектор для node_path (используя Qdrant filter, т.к. векторы лежат там)
            # Find the vector associated with node_path
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="path",
                        match=MatchValue(value=node_path)
                    )
                ]
            )
            
            # Retrieve point with vector
            points = self.qdrant.get_collection("vetka_elisya") # Needs correct client usage to retrieve
            
            # Using scroll/search is safer if direct retrieval is missing
            result = self.qdrant.scroll(
                collection_name="vetka_elisya",
                scroll_filter=search_filter,
                limit=1,
                with_vectors=True,
                with_payload=True,
            )
            
            if not result[0]:
                logger.debug(f"No existing vector found for path: {node_path}")
                return []
            
            query_vector = result[0][0].vector
            
            # 2. Искать похожие точки по найденному вектору
            search_results = self.qdrant.search(
                collection_name="vetka_elisya",
                query_vector=query_vector,
                limit=limit + 1, # +1 เพื่อ исключить сам себя
                query_filter=Filter(
                    must_not=[
                        FieldCondition(
                            key="path",
                            match=MatchValue(value=node_path)
                        )
                    ]
                )
            )

            # Форматирование результата
            formatted_results = [
                {'path': hit.payload.get('path', 'unknown'), 'score': hit.score}
                for hit in search_results
            ]
            
            logger.debug(f"search_similar returned {len(formatted_results)} results for {node_path}")
            return formatted_results

        except Exception as e:
            logger.error(f"search_similar failed: {e}")
            return []

    def semantic_search(self, query: str, limit: int = 10, collection: str = "vetka_elisya") -> List[Dict]:
        """
        Semantic search using Qdrant vector similarity.

        Args:
            query: Text query to search for
            limit: Maximum number of results
            collection: Qdrant collection name

        Returns:
            List[Dict]: Results with 'path', 'content', 'score' keys
        """
        if not self.qdrant or not self.embedding_model:
            logger.debug("Qdrant or embedding model not available - skipping semantic_search")
            return []

        try:
            # Get query embedding
            query_vector = self._get_embedding(query)
            if not query_vector:
                logger.warning("Failed to get embedding for query")
                return []

            # Search in Qdrant
            search_results = self.qdrant.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=limit,
                with_payload=True
            )

            # Format results
            results = []
            for hit in search_results:
                results.append({
                    'path': hit.payload.get('path', 'unknown'),
                    'content': hit.payload.get('content', ''),
                    'type': hit.payload.get('type', 'file'),
                    'score': hit.score
                })

            logger.debug(f"semantic_search returned {len(results)} results for query: {query[:50]}...")
            return results

        except Exception as e:
            logger.error(f"semantic_search failed: {e}")
            return []

    def get_workflow_history(self, workflow_id: str) -> List[Dict]:
        """История по workflow_id из ChangeLog"""
        history = []
        try:
            changelog_file = Path(self.changelog_path)
            if not changelog_file.exists():
                return history
            
            with open(changelog_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("workflow_id") == workflow_id:
                            history.append(entry)
                    except Exception:
                        continue
            
            logger.debug(f"Workflow history: {len(history)} entries")
            return history
        except Exception as e:
            logger.debug(f"get_workflow_history failed: {e}")
            return []

    def health_check(self) -> Dict[str, bool]:
        """Проверка всех трёх систем"""
        health = {
            "changelog": False,
            "weaviate": False,
            "qdrant": False,
            "overall": False
        }
        
        # ChangeLog
        try:
            changelog_file = Path(self.changelog_path)
            health["changelog"] = changelog_file.exists()
        except Exception:
            pass
        
        # Weaviate
        try:
            if self.session:
                response = self.session.get(f"{self.weaviate_url}/v1/meta", timeout=3)
                health["weaviate"] = response.status_code == 200
        except Exception:
            pass
        
        # Qdrant
        try:
            if self.qdrant:
                self.qdrant.get_collection("vetka_elisya")
                health["qdrant"] = True
        except Exception:
            pass
        
        # Overall: ChangeLog ОБЯЗАТЕЛЕН, остальные — best-effort
        health["overall"] = health["changelog"]

        logger.debug(f"Health check: {health}")
        return health

    # ✅ PATCH #5: Context manager support for proper cleanup
    def close(self):
        """Close all connections properly"""
        if self.session:
            try:
                self.session.close()
                logger.debug("Session closed")
            except Exception as e:
                logger.debug(f"Error closing session: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup"""
        self.close()
        return False

    def __del__(self):
        """Cleanup on garbage collection"""
        try:
            self.close()
        except Exception:
            pass

    # ===== LEGACY METHODS (для обратной совместимости) =====
    
    def save_workflow_result(self, workflow_id: str, result: dict) -> bool:
        """Legacy: Save complete workflow result"""
        entry = {
            "type": "workflow_complete",
            "workflow_id": workflow_id,
            "result": result,
            "speaker": "system"
        }
        try:
            self.triple_write(entry)
            return True
        except Exception:
            return False

    def save_agent_output(
        self,
        agent_name: str,
        output: str,
        workflow_id: str,
        task_type: str = "unknown"
    ) -> bool:
        """Legacy: Save individual agent output"""
        entry = {
            "type": "agent_output",
            "agent_name": agent_name,
            "output": output,
            "workflow_id": workflow_id,
            "task_type": task_type,
            "speaker": agent_name
        }
        try:
            self.triple_write(entry)
            return True
        except Exception:
            return False

    def log_error(
        self,
        workflow_id: str,
        agent_name: str,
        error: str
    ) -> bool:
        """Legacy: Log error"""
        entry = {
            "type": "error",
            "workflow_id": workflow_id,
            "agent_name": agent_name,
            "error": error,
            "speaker": "system"
        }
        try:
            self.triple_write(entry)
            return True
        except Exception:
            return False

    def save_evaluation_result(self, evaluation_id, task, output, complexity, score, scores_breakdown):
        """Legacy: Save evaluation result"""
        entry = {
            "type": "evaluation",
            "evaluation_id": evaluation_id,
            "task": task,
            "output": output,
            "complexity": complexity,
            "score": score,
            "scores_breakdown": scores_breakdown,
            "speaker": "eval_agent"
        }
        try:
            self.triple_write(entry)
            return True
        except Exception:
            return False

    def retrieve_past_feedback(self, task, limit=3):
        """Legacy: Retrieve past feedback"""
        try:
            examples = self.get_high_score_examples(limit=limit)
            return [e for e in examples if e.get("type") == "user_feedback"]
        except Exception:
            return []

    def query_high_score_examples(self, complexity, limit=3, min_score=0.8):
        """Legacy: Query high score examples"""
        return self.get_high_score_examples(min_score=min_score, limit=limit)

    def create_few_shot_prompt_section(self, examples):
        """Legacy: Create few-shot prompt section"""
        if not examples:
            return ""
        result = "EXAMPLES: "
        for i, e in enumerate(examples, 1):
            task = e.get('task', '')
            result += f"Ex {i}: {task}; "
        return result

    def get_agent_stats(self, agent_name: str) -> Dict:
        """Legacy: Get agent stats"""
        try:
            entries = []
            changelog_file = Path(self.changelog_path)
            with open(changelog_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("agent_name") == agent_name or entry.get("speaker") == agent_name:
                            entries.append(entry)
                    except Exception:
                        continue
            return {
                "agent_name": agent_name,
                "total_runs": len(entries),
                "outputs": entries
            }
        except Exception:
            return {}

    def search_workflows(self, query: str) -> List[Dict]:
        """Legacy: Search workflows"""
        try:
            results = self.get_similar_context(query, limit=10)
            return [e for e in results if e.get("type") == "workflow_complete"]
        except Exception:
            return []

    # ===== ARC SOLVER METHODS =====

    def save_arc_example(self, example: Dict[str, Any]) -> Optional[str]:
        """
        Сохранить пример ARC для обучения.

        Args:
            example: {
                "type": str,
                "code": str,
                "explanation": str,
                "score": float,
                "metadata": dict,
                "timestamp": str
            }

        Returns:
            str: ID сохраненного примера или None при ошибке
        """
        try:
            entry = {
                'type': 'arc_example',
                'arc_type': example.get('type', 'unknown'),
                'code': example.get('code', ''),
                'explanation': example.get('explanation', ''),
                'score': example.get('score', 0.0),
                'success': example.get('success', False),
                'metadata': example.get('metadata', {}),
                'timestamp': example.get('timestamp', datetime.now(timezone.utc).isoformat()),
                'workflow_id': example.get('workflow_id', 'unknown'),
                'speaker': 'arc_solver'
            }

            # Triple Write
            example_id = self.triple_write(entry)

            logger.info(f"✅ ARC example saved: {example_id[:8] if example_id else 'unknown'}")
            return example_id

        except Exception as e:
            logger.error(f"❌ Failed to save ARC example: {e}")
            return None

    def load_arc_examples(self, limit: int = 20, min_score: float = 0.5) -> List[Dict]:
        """
        Загрузить ARC примеры для few-shot learning.

        Args:
            limit: Максимальное количество примеров
            min_score: Минимальный score для отбора

        Returns:
            List[Dict]: Список ARC примеров
        """
        examples = []
        try:
            changelog_file = Path(self.changelog_path)
            if not changelog_file.exists():
                return examples

            with open(changelog_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("type") == "arc_example":
                            score = entry.get("score", 0)
                            if score >= min_score:
                                examples.append(entry)
                                if len(examples) >= limit:
                                    break
                    except Exception:
                        continue

            # Сортируем по score (лучшие первые)
            examples.sort(key=lambda x: x.get('score', 0), reverse=True)
            logger.debug(f"Loaded {len(examples)} ARC examples (min_score={min_score})")
            return examples[:limit]

        except Exception as e:
            logger.debug(f"load_arc_examples failed: {e}")
            return []


def get_memory_manager(
    weaviate_url: str = 'http://localhost:8080',
    qdrant_url: str = 'http://localhost:6333',
    changelog_path: str = 'data/changelog.jsonl',
    embedding_model: str = 'auto'  # ✅ PATCH #2: auto-detection by default
) -> MemoryManager:
    """Factory function to create MemoryManager instance"""
    return MemoryManager(
        weaviate_url=weaviate_url,
        qdrant_url=qdrant_url,
        changelog_path=changelog_path,
        embedding_model=embedding_model
    )
