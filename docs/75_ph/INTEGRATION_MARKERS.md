# Phase 75 Integration Markers for Opus

## 🎯 CRITICAL: Data Flow Gap

**Problem**: viewport_context & pinned_files **never reach** VETKAState
```
Frontend → user_message_handler (line 183-200: logged but not passed)
          → orchestrator.execute_with_langgraph() ❌ no viewport params
          → create_initial_state() ❌ no viewport params
          → VETKAState: viewport_context=None, pinned_files=None
```

---

## 📍 Exact Integration Points (Line Numbers)

### 1️⃣ langgraph_state.py
- **Line 84 (after)**: Add 3 fields:
  ```python
  viewport_context: Optional[Dict[str, Any]] = None
  pinned_files: Optional[List[Dict[str, Any]]] = None
  code_context: Optional[Dict[str, Any]] = None
  ```

- **Lines 92-98**: Update `create_initial_state()` signature:
  ```python
  def create_initial_state(
      ...,
      viewport_context: Optional[Dict] = None,
      pinned_files: Optional[List] = None,
      code_context: Optional[Dict] = None
  ) -> VETKAState:
  ```

- **Lines 123-173**: Initialize new fields in returned dict

### 2️⃣ langgraph_nodes.py - hostess_node

- **Line 48 (imports)**: Add
  ```python
  from src.orchestration.context_fusion import build_context_for_hostess
  ```

- **Line 183 (CRITICAL)**: BEFORE `_hostess_decide()` call
  ```python
  # Get fused spatial context for routing decision
  hostess_context = build_context_for_hostess(
      viewport_context=state.get('viewport_context'),
      pinned_files=state.get('pinned_files'),
      user_query=message
  )

  # Then call with new context
  decision = await self._hostess_decide(message, hostess_context)
  ```

- **Line 223**: Update `_hostess_decide()` to use fused_context for routing

### 3️⃣ langgraph_nodes.py - dev_qa_parallel_node

- **Line 48 (imports)**: Add
  ```python
  from src.orchestration.context_fusion import build_context_for_dev
  ```

- **After line 456 (CRITICAL)**: Build code context
  ```python
  # Fuse spatial + code context for Dev/QA
  code_context = {
      'summary': f'Dev/QA parallel execution',
      'last_operation': 'executing',
      'files_modified': [],
  }

  dev_context = build_context_for_dev(
      viewport_context=state.get('viewport_context'),
      pinned_files=state.get('pinned_files'),
      code_context=code_context,
      user_query=state.get('context', '')
  )

  combined_context = f"{dev_context}\n\n{combined_context}"
  ```

### 4️⃣ orchestrator_with_elisya.py

- **Line ~1935**: Pass viewport/pinned to state creation
  ```python
  state = self.nodes.create_initial_state(
      workflow_id=workflow_id,
      context=context,
      ...
      viewport_context=viewport_context,  # NEW
      pinned_files=pinned_files,           # NEW
  )
  ```

- **Line ~2021**: Same for async version

### 5️⃣ user_message_handler.py

- **~Line 450+**: Pass from request to orchestrator
  ```python
  await orchestrator.execute_with_langgraph(
      ...
      viewport_context=data.get('viewport_context'),  # NEW
      pinned_files=data.get('pinned_files'),          # NEW
  )
  ```

---

## 🧪 Verification Checklist

- [ ] VETKAState has 3 new optional fields
- [ ] hostess_node calls build_context_for_hostess()
- [ ] hostess_node uses fused context in _hostess_decide()
- [ ] dev_qa_parallel_node calls build_context_for_dev()
- [ ] fused context injected into combined_context
- [ ] Orchestrator passes viewport/pinned through chain
- [ ] Handler extracts and passes viewport/pinned data
- [ ] All 32 Phase 75 tests still pass
- [ ] No regressions in existing workflow

---

## 📊 Changes Summary
- **Files to modify**: 5 (langgraph_state.py, langgraph_nodes.py, orchestrator, user_message_handler)
- **New lines of code**: ~70
- **Effort**: ~3 hours including testing
- **Risk**: Low (all new fields Optional, backward compatible)

---

**Status**: Ready for Phase 75.5/76 integration
**Created**: 2026-01-20
**For**: Claude Code Opus 4.5
