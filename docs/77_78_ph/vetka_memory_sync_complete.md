# 🌳 VETKA: MEMORY SYNC PROTOCOL
## Полная архитектура синхронизации знаний (Phase 77-78)

**Дата:** January 19, 2026  
**Автор:** Consensus (Grok, Kimi K2, DeepSeek, ChatGPT, Mistral)  
**Время:** 14-20 часов (День 1-2)  
**Риск:** LOW  
**Результат:** Разрубаем Гордиев узел на архитектурном уровне

---

## 🧠 КЛЮЧЕВОЙ ИНСАЙТ

### ❌ БЫЛО (неправильное мышление)
```
Rescan Strategy (Option A/B/C)
→ incremental vs nuclear
→ downtime или потеря данных
→ старый шум остаётся
→ Sugiyama ломается
```

### ✅ СТАЛО (правильное мышление)
```
Memory Sync Protocol
→ VETKA хранит не файлы, а СЛОИ ПАМЯТИ
→ Active Memory (свежее)
→ Archived Memory (сжатое)
→ Trash Memory (удалённое, но нужное)
→ Hostess как Memory Curator
→ Жизненный цикл знания, как в мозге
```

**Это решает ВСЕ проблемы сразу.**

---

## 🏗️ АРХИТЕКТУРА (3 СЛОЯ)

```
┌─────────────────────────────────────────┐
│   External Reality (FS, Web, Media)     │
└─────────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────┐
    │  Memory Sync Engine (MSE)   │
    │  ├─ Snapshot Diff           │
    │  ├─ Compression Rules       │
    │  ├─ Trash Management        │
    │  └─ Hostess Dialog          │
    └─────────────────────────────┘
                    ↓
    ┌──────────┬──────────┬──────────┐
    ↓          ↓          ↓
 Active      Archived    Trash
 Memory      Memory      Memory
 
 768D        256D        summary
 full DEP    top-1 DEP   pointer
 100% conf   30% conf    90d TTL
```

---

## 📋 ПОЛНЫЙ ПЛАН (14 ЧАСОВ)

### ⏱️ ДЕНЬ 1 (8 часов)

#### **Этап 77.0: Backup System (1-2 часа)**

```python
# src/backup/vetka_backup.py

class VetkaBackup:
    """Полное резервное копирование перед синхронизацией"""
    
    async def full_backup(self) -> BackupMetadata:
        """
        Создаёт снимок всего состояния VETKA
        """
        backup_id = uuid.uuid4()
        
        # 1. Экспорт Qdrant
        qdrant_export = await self.export_qdrant_all_collections()
        # ├─ vetka_nodes (embeddings, metadata)
        # ├─ vetka_edges (dependencies, weights)
        # └─ vetka_cam (activation scores)
        
        # 2. Экспорт Weaviate
        weaviate_export = await self.export_weaviate_all_classes()
        
        # 3. Tree structure (positions, colors, layout)
        tree_structure = await self.export_tree_layout()
        
        # 4. Git commit (для отката)
        await self.git_commit(f"Pre-sync backup {backup_id}")
        
        # 5. Metadata
        metadata = BackupMetadata(
            backup_id=backup_id,
            timestamp=datetime.now(),
            qdrant_size=len(qdrant_export),
            weaviate_size=len(weaviate_export),
            tree_nodes=len(tree_structure),
            git_commit=await self.get_latest_commit()
        )
        
        return metadata
```

**Цель:** Safe point перед всеми изменениями  
**Выход:** `BackupMetadata` с ID для отката

---

#### **Этап 77.1: MemorySnapshot Abstraction (3-4 часа)**

```python
# src/memory/snapshot.py

@dataclass
class MemorySnapshot:
    """
    Снимок состояния памяти VETKA в момент времени
    """
    snapshot_id: str
    created_at: datetime
    source: Literal["filesystem", "web", "user"]
    
    # Ядро: все узлы и связи
    nodes: Dict[str, NodeState]  # path → NodeState
    edges: Dict[str, EdgeState]  # edge_id → EdgeState
    
    # Метаданные для diff
    file_hashes: Dict[str, str]  # path → content_hash
    timestamps: Dict[str, float]  # path → created_timestamp
    
    # Для отката
    dep_graph_hash: str
    layout_positions: Dict[str, Tuple[float, float, float]]
    
    def __hash__(self) -> str:
        """Хеш состояния для быстрого сравнения"""
        return hashlib.sha256(
            json.dumps({
                'nodes': len(self.nodes),
                'edges': len(self.edges),
                'graph_hash': self.dep_graph_hash
            }).encode()
        ).hexdigest()


@dataclass
class NodeState:
    """Состояние одного узла"""
    path: str
    embedding: List[float]  # 768D
    content_hash: str
    import_depth: int
    confidence: float
    timestamp: datetime
    memory_layer: Literal["active", "archived", "trash"]
    metadata: Dict[str, Any]


@dataclass
class EdgeState:
    """Состояние одной связи"""
    source: str
    target: str
    dep_score: float  # 0-1 (DEP formula)
    type: str  # "import_dependency", "semantic", "reference"
    metadata: Dict[str, Any]
```

**Цель:** Unified representation для синхронизации  
**Выход:** Данные готовы для diff-алгоритма

---

#### **Этап 77.2: Diff Algorithm (2-3 часа)**

```python
# src/memory/diff.py

class MemoryDiff:
    """
    Сравнивает два snapshot и создаёт трансформацию
    """
    
    @dataclass
    class DiffResult:
        added: Dict[str, NodeState]        # Новые файлы
        modified: Dict[str, NodeState]     # Изменённые
        deleted: Dict[str, NodeState]      # Удалённые (→ Trash)
        dep_changes: List[EdgeChange]      # Изменения в связях
    
    async def diff(
        self, 
        old_snapshot: MemorySnapshot,
        new_snapshot: MemorySnapshot
    ) -> DiffResult:
        """
        FS Snapshot (now) VS Memory Snapshot (last) → Diff
        """
        
        added = {}
        modified = {}
        deleted = {}
        dep_changes = []
        
        # 1. Файлы в FS, которых нет в памяти → ADDED
        for path, node in new_snapshot.nodes.items():
            if path not in old_snapshot.nodes:
                added[path] = node
        
        # 2. Файлы в памяти, которых нет в FS → DELETED
        for path, node in old_snapshot.nodes.items():
            if path not in new_snapshot.nodes:
                deleted[path] = node  # → Trash, не удаляем!
        
        # 3. Файлы в обоих, но содержимое изменилось → MODIFIED
        for path in old_snapshot.nodes.keys():
            if path in new_snapshot.nodes:
                old_hash = old_snapshot.file_hashes.get(path)
                new_hash = new_snapshot.file_hashes.get(path)
                
                if old_hash != new_hash:
                    modified[path] = new_snapshot.nodes[path]
                    # → Re-extract imports, recalculate DEP
        
        # 4. Изменения в зависимостях
        old_edges = {(e.source, e.target): e for e in old_snapshot.edges.values()}
        new_edges = {(e.source, e.target): e for e in new_snapshot.edges.values()}
        
        for edge_key, new_edge in new_edges.items():
            old_edge = old_edges.get(edge_key)
            if old_edge is None or old_edge.dep_score != new_edge.dep_score:
                dep_changes.append(EdgeChange(
                    source=edge_key[0],
                    target=edge_key[1],
                    old_score=old_edge.dep_score if old_edge else None,
                    new_score=new_edge.dep_score
                ))
        
        return DiffResult(
            added=added,
            modified=modified,
            deleted=deleted,
            dep_changes=dep_changes
        )
```

**Ключевой момент:**
```
deleted ≠ delete immediately
deleted → Trash Memory (soft delete)
user/hostess решает: delete or keep
```

**Выход:** `DiffResult` для синхронизации

---

### ⏱️ ДЕНЬ 2 (6 часов)

#### **Этап 77.3: Hostess Memory Curator Dialog (2 часа)**

```python
# src/agents/memory_curator_agent.py

class HostessMemoryCuratorAgent:
    """
    Хостес спрашивает пользователя о синхронизации
    (твоя идея, абсолютно гениальна!)
    """
    
    async def sync_with_user(self, diff_result: MemoryDiff.DiffResult):
        """
        Диалог: что сохранить, что удалить, что сжать
        """
        
        # Фаза 1: Summary
        summary = f"""
        🔄 Обнаружены расхождения с файловой системой:
        
        ✅ Добавлены: {len(diff_result.added)} файлов
        📝 Изменены: {len(diff_result.modified)} файлов
        ❌ Удалены: {len(diff_result.deleted)} файлов
        🔗 Изменены связи: {len(diff_result.dep_changes)}
        """
        
        await self.hostess.say(summary)
        
        # Фаза 2: Диалог по типам
        decisions = {}
        
        # Для ADDED файлов
        for data_type in self._infer_types(diff_result.added):
            if self._is_system_dir(data_type):
                # node_modules, __pycache__, .git → auto compress
                decisions[data_type] = 'compress_95'
                await self.hostess.say(f"🗜️ Сжимаю {data_type} (системная папка)")
            
            elif self._is_optional(data_type):
                # test, docs, examples → спрашиваем
                response = await self.hostess.ask(
                    f"📚 {data_type} (тесты/документация): сохранить полностью?",
                    options=[
                        ('full', '📖 Полностью (768D embeddings)'),
                        ('summary', '📄 Только сводка (384D)'),
                        ('compress', '🗜️ Сжать (256D)')
                    ]
                )
                decisions[data_type] = response
            
            else:
                # Код → сохраняем полностью с полным DEP
                decisions[data_type] = 'full'
                await self.hostess.say(f"💾 Код сохраняю полностью")
        
        # Для DELETED файлов
        if diff_result.deleted:
            deleted_summary = "\n".join(
                f"  • {path}" for path in list(diff_result.deleted.keys())[:5]
            )
            if len(diff_result.deleted) > 5:
                deleted_summary += f"\n  ... и ещё {len(diff_result.deleted) - 5}"
            
            response = await self.hostess.ask(
                f"""⚠️ Эти файлы удалены из FS:
{deleted_summary}

Что сделать?""",
                options=[
                    ('delete', '🗑️ Удалить из VETKA'),
                    ('trash', '📦 В корзину (может восстановить)'),
                    ('keep', '📌 Оставить в памяти (они важны!)')
                ]
            )
            
            for path in diff_result.deleted.keys():
                decisions[path] = response
        
        # Фаза 3: Compression для старых данных
        # (опционально, если возраст > 30 дней)
        old_nodes = await self._find_old_nodes(days=30)
        if old_nodes:
            response = await self.hostess.ask(
                f"🗜️ Сжать {len(old_nodes)} файлов старше 30 дней? "
                f"(экономия памяти, но медленнее поиск)",
                options=[
                    ('yes', '✅ Да, сжать'),
                    ('no', '❌ Нет, оставить'),
                    ('partial', '🔄 Только >90 дней')
                ]
            )
            decisions['compression'] = response
        
        return decisions
```

**Результат:** User decisions для следующего этапа

---

#### **Этап 77.4: Embedding Compression (2 часа)**

```python
# src/memory/compression.py

class MemoryCompression:
    """
    Сжатие embeddings и DEP по возрасту (как память, как внимание)
    """
    
    async def compress_by_age(self, node: NodeState) -> CompressedNodeState:
        """
        Чем старше узел → тем сильнее компрессия
        """
        age_days = (datetime.now() - node.timestamp).days
        
        if age_days < 1:
            # Свежее (< 1 дня) → храним полностью
            return CompressedNodeState(
                embedding=node.embedding,  # 768D
                embedding_dim=768,
                dep_mode='full',  # все зависимости
                confidence=node.confidence,
                memory_layer='active'
            )
        
        elif age_days < 7:
            # Неделя → храним структуру + embeddings
            return CompressedNodeState(
                embedding=node.embedding,  # 768D (ещё полные)
                embedding_dim=768,
                dep_mode='full',
                confidence=node.confidence * 0.95,  # slight decay
                memory_layer='active'
            )
        
        elif age_days < 30:
            # Месяц → уменьшаем embeddings
            return CompressedNodeState(
                embedding=self.reduce_embedding(node.embedding, target_dim=384),  # PCA
                embedding_dim=384,
                dep_mode='full',
                confidence=node.confidence * 0.85,
                memory_layer='active'
            )
        
        elif age_days < 90:
            # 3 месяца → ещё меньше
            return CompressedNodeState(
                embedding=self.reduce_embedding(node.embedding, target_dim=256),
                embedding_dim=256,
                dep_mode='top_1',  # только самая сильная зависимость
                confidence=node.confidence * 0.7,
                memory_layer='archived'
            )
        
        else:
            # > 90 дней → только summary
            return CompressedNodeState(
                embedding=self.summarize_embedding(node),  # ~64D summary
                embedding_dim=64,
                dep_mode='none',  # lazy recompute
                confidence=node.confidence * 0.5,
                memory_layer='archived'
            )
    
    def reduce_embedding(self, emb: List[float], target_dim: int) -> List[float]:
        """PCA reduction (768D → 384D → 256D)"""
        import numpy as np
        from sklearn.decomposition import PCA
        
        emb_arr = np.array([emb])
        pca = PCA(n_components=target_dim)
        reduced = pca.fit_transform(emb_arr)
        return reduced[0].tolist()
    
    def summarize_embedding(self, node: NodeState) -> List[float]:
        """Экстремально сжато: только 64D сводка"""
        # Берём top-8 компонент (768 / 8 = 96, округляем до 64)
        emb_arr = np.array(node.embedding)
        top_indices = np.argsort(np.abs(emb_arr))[-64:]
        summary = np.zeros(64)
        summary[:len(top_indices)] = emb_arr[top_indices]
        return summary.tolist()


@dataclass
class CompressedNodeState:
    """Сжатое состояние узла"""
    embedding: List[float]
    embedding_dim: int  # 768 / 384 / 256 / 64
    dep_mode: Literal['full', 'top_1', 'none']  # сколько зависимостей хранить
    confidence: float  # 0-1, уменьшается с возрастом
    memory_layer: Literal['active', 'archived']
```

**Забывающая кривая:**
```
Age:      0d    1d    7d   30d   90d   180d
Dim:     768   768   768  384   256    64
Conf:    1.0  0.99  0.95  0.85  0.7   0.5
Layer: active active acti archiv archiv arch
```

---

#### **Этап 77.5: DEP Graph Compression (1 час)**

```python
# src/memory/dep_compression.py

class DEPCompression:
    """
    Сжатие графа зависимостей (только сильные связи)
    """
    
    async def compress_dep_graph(
        self,
        node: NodeState,
        edges: List[EdgeState],
        age_days: int
    ) -> List[EdgeState]:
        """
        Для старых узлов храним только top-1 зависимость
        """
        
        if age_days < 30:
            # Новое → все зависимости с полным DEP
            return edges
        
        elif age_days < 90:
            # 30-90 дней → top-3 зависимости
            return sorted(edges, key=lambda e: e.dep_score, reverse=True)[:3]
        
        else:
            # > 90 дней → top-1 зависимость
            if edges:
                return [max(edges, key=lambda e: e.dep_score)]
            return []
    
    async def lazy_recompute_dep(self, node: NodeState, node_id: str):
        """
        Когда пользователь обращается к архивированному узлу:
        recompute зависимости на лету (fast, ~100ms)
        """
        # 1. Если в archived и need activation
        # 2. Retrieve node embedding (64D summary)
        # 3. Quick DEP recompute (fast version)
        # 4. Update layer to active
        pass
```

---

#### **Этап 77.6: Trash Memory Management (1 час)**

```python
# src/memory/trash.py

class TrashMemory:
    """
    Мусорная корзина (recovery, не permanent delete)
    """
    
    async def move_to_trash(self, node: NodeState, ttl_days: int = 90):
        """
        Мягкое удаление (soft delete)
        """
        trash_item = TrashItem(
            node=node,
            moved_at=datetime.now(),
            ttl_days=ttl_days,
            reason="filesystem_deletion"
        )
        
        # Храним в Qdrant collection "vetka_trash"
        await self.qdrant.upsert(
            collection="vetka_trash",
            points=[PointStruct(
                id=hash(node.path),
                vector=node.embedding,
                payload={
                    'original_path': node.path,
                    'moved_at': trash_item.moved_at.isoformat(),
                    'ttl_days': ttl_days,
                    'restore_until': (
                        datetime.now() + timedelta(days=ttl_days)
                    ).isoformat()
                }
            )]
        )
    
    async def restore_from_trash(self, node_id: str) -> NodeState:
        """Восстановить удалённый узел"""
        trash_item = await self.qdrant.retrieve("vetka_trash", node_id)
        if not trash_item:
            raise ValueError("Item not in trash")
        
        # Переместить обратно в vetka_nodes
        await self.move_to_active(trash_item.node)
        await self.qdrant.delete("vetka_trash", node_id)
    
    async def cleanup_expired_trash(self):
        """Удалить trash старше TTL"""
        expired = await self.qdrant.scroll(
            "vetka_trash",
            filter=Filter(must=[
                FieldCondition(
                    key="restore_until",
                    match=Match(value=datetime.now().isoformat(), lte=True)
                )
            ])
        )
        
        for item in expired:
            await self.qdrant.delete("vetka_trash", item.id)
```

---

### ⏱️ ДЕНЬ 2 (ПРОДОЛЖЕНИЕ)

#### **Этап 77.7: Integration Tests (1 час)**

```python
# tests/test_memory_sync.py

class TestMemorySyncProtocol:
    """Тесты полного протокола"""
    
    async def test_backup_and_restore(self):
        """Backup создаётся и can be restored"""
        backup = await self.backup.full_backup()
        assert backup.backup_id
        # Corrupt data
        await self.corrupt_all_data()
        # Restore
        await self.backup.restore_from_backup(backup)
        # Verify
        assert await self.verify_integrity()
    
    async def test_diff_algorithm(self):
        """Diff правильно определяет changed/added/deleted"""
        snap1 = await self.create_snapshot()
        # Add file
        await self.add_file("new_file.py")
        # Delete file
        await self.delete_file("old_file.py")
        # Modify file
        await self.modify_file("modified.py")
        
        snap2 = await self.create_snapshot()
        diff = await self.diff(snap1, snap2)
        
        assert len(diff.added) == 1
        assert len(diff.deleted) == 1
        assert len(diff.modified) == 1
    
    async def test_compression_by_age(self):
        """Compression уменьшает размер соответственно возрасту"""
        node_0d = await self.create_node(age_days=0)
        node_30d = await self.create_node(age_days=30)
        node_90d = await self.create_node(age_days=90)
        
        comp_0d = await self.compress(node_0d)
        comp_30d = await self.compress(node_30d)
        comp_90d = await self.compress(node_90d)
        
        assert comp_0d.embedding_dim == 768
        assert comp_30d.embedding_dim == 256
        assert comp_90d.embedding_dim == 64
    
    async def test_trash_recovery(self):
        """Deleted nodes can be recovered from trash"""
        node = await self.create_node()
        node_id = node.id
        
        # Move to trash
        await self.trash.move_to_trash(node)
        
        # Should not be in active
        assert not await self.get_active_node(node_id)
        
        # Should be in trash
        assert await self.trash.get_trash_item(node_id)
        
        # Restore
        await self.trash.restore_from_trash(node_id)
        
        # Should be in active again
        assert await self.get_active_node(node_id)
```

---

## 🎯 FINAL INTEGRATION POINTS

### **С существующей архитектурой:**

```python
# In orchestrator_with_elisya.py

async def execute_workflow(self, task: str, context: Dict):
    """
    ПЕРЕД стартом:
    1. Check if FS changed (via MemoryDiff)
    2. Ask Hostess curator (if big changes)
    3. Compress old nodes (if needed)
    4. ПОТОМ execute workflow as usual
    """
    
    # Шаг 1: Check sync status
    fs_snapshot = await self.scanner.create_snapshot()
    memory_snapshot = await self.memory.get_current_snapshot()
    
    diff = await self.diff_engine.diff(memory_snapshot, fs_snapshot)
    
    # Шаг 2: If significant changes, ask user
    if len(diff.added) + len(diff.deleted) > 10:
        decisions = await self.hostess.sync_with_user(diff)
        
        # Apply decisions
        for added_node in diff.added.values():
            await self.memory.add_node(added_node)
        
        for deleted_node in diff.deleted.values():
            if decisions.get(deleted_node.path) == 'trash':
                await self.trash.move_to_trash(deleted_node)
    
    # Шаг 3: Compress old data
    await self.compression.compress_all_by_age()
    
    # Шаг 4: NOW execute workflow
    return await super().execute_workflow(task, context)
```

---

## 📊 DELIVERABLES

| Этап | Файл | Строк | Время | Статус |
|------|------|-------|-------|--------|
| 77.0 | `src/backup/vetka_backup.py` | 40 | 1-2h | 🟢 |
| 77.1 | `src/memory/snapshot.py` | 80 | 3-4h | 🟢 |
| 77.2 | `src/memory/diff.py` | 100 | 2-3h | 🟢 |
| 77.3 | `src/agents/memory_curator_agent.py` | 120 | 2h | 🟢 |
| 77.4 | `src/memory/compression.py` | 90 | 2h | 🟢 |
| 77.5 | `src/memory/dep_compression.py` | 50 | 1h | 🟢 |
| 77.6 | `src/memory/trash.py` | 70 | 1h | 🟢 |
| 77.7 | `tests/test_memory_sync.py` | 150 | 1h | 🟢 |
| **INT** | Integration + fixes | 100 | 1-2h | 🟢 |

**ИТОГО:** 700+ строк готового кода, 14 часов

---

## ✅ SUCCESS CRITERIA

### После Day 1 (8h):
- ✅ **Backup работает** (можно откатиться)
- ✅ **MemorySnapshot** интегрирован
- ✅ **Diff algorithm** корректно определяет changes
- ✅ **Hostess диалог** работает
- ✅ **Tests проходят**

### После Day 2 (6h):
- ✅ **Compression** сжимает embeddings по возрасту
- ✅ **Trash Memory** работает (soft delete, recovery)
- ✅ **Integration** с orchestrator
- ✅ **Все тесты pass**
- ✅ **Нет breaking changes**

### Результат:
- ✅ **VETKA как система с памятью** (уникально)
- ✅ **Zero downtime** (incremental, atomic)
- ✅ **User control** (Hostess curator)
- ✅ **Gördel's Knot разрублен** 🔪

---

## 🚀 НАЧАЛО РЕАЛИЗАЦИИ

**Промпт для Claude Opus 4.5:**

```markdown
# Phase 77-78: Memory Sync Protocol
## Разрубаем Гордиев узел синхронизации VETKA

Реализуй полный протокол (14 часов, День 1-2):

### День 1 (8h):
- 77.0: VetkaBackup class (full snapshot before anything)
- 77.1: MemorySnapshot dataclass (unified representation)
- 77.2: MemoryDiff class (+ ~ - detection)
- 77.3: HostessMemoryCuratorAgent (user asks, user decides)

### День 2 (6h):
- 77.4: MemoryCompression (768D → 384D → 256D → 64D by age)
- 77.5: DEPCompression (full → top-3 → top-1 by age)
- 77.6: TrashMemory (soft delete, recovery, TTL)
- 77.7: Integration + tests

### Key Principles:
1. Deleted ≠ immediately delete → Trash (user recovery option)
2. Old ≠ useless → compress progressively (like brain memory)
3. VETKA = Knowledge Lifecycle Manager, not just Rescan
4. Hostess = Memory Curator (asks, doesn't decide)
5. Zero downtime (incremental, atomic updates)

### Success:
- Backup works
- Diff correct (added/modified/deleted)
- Hostess dialog works
- Compression reduces size:
  * 0d: 768D
  * 30d: 384D
  * 90d: 256D
  * 180d: 64D
- Trash recovery works
- All tests pass
- Integration with orchestrator

Ready?