# MYCELIUM v2.0 - Improved Prompt Template

**Created:** 2026-02-01
**Phase:** 105 (Jarvis T9)
**Status:** READY FOR USE
**Based on:** Grok Analysis + Claude Code Feedback

---

## Overview

MYCELIUM v2.0 is an optimized research agent for VETKA Railway with:
- **Semantic-First Search** (Qdrant vectors before grep/glob)
- **Adaptive Token Budget** (dynamic, not hardcoded)
- **Eternal Disk + Heartbeats** (persistent audits, proactive monitoring)
- **MCP Vetka Integration** (25+ native tools)
- **JSON-Only Output** (structured, no prose)

---

## Token Budget Formula

```python
# ADAPTIVE TOKEN BUDGET - Not hardcoded!
def calculate_token_budget(task_type: str, artifact_count: int, has_voice: bool) -> int:
    """
    Dynamic token allocation based on task complexity.

    Args:
        task_type: 'research' | 'audit' | 'implement' | 'batch'
        artifact_count: Number of artifacts to process
        has_voice: Whether voice/TTS is involved

    Returns:
        Token budget (300-2000 range)
    """
    BASE = 300

    # Task complexity multiplier
    COMPLEXITY = {
        'research': 1.0,      # Simple exploration
        'audit': 1.5,         # Marker verification
        'implement': 2.0,     # Code changes
        'batch': 2.5          # Multiple files
    }

    multiplier = COMPLEXITY.get(task_type, 1.0)

    # Artifact scaling: +150 tokens per artifact (>500 chars)
    artifact_tokens = artifact_count * 150

    # Voice/TTS bonus (Phase 60.5 integration)
    voice_tokens = 300 if has_voice else 0

    budget = int(BASE * multiplier + artifact_tokens + voice_tokens)

    # Clamp to reasonable range
    return min(max(budget, 300), 2000)

# Examples:
# - Simple research: 300 tokens
# - Audit 3 artifacts: 300*1.5 + 3*150 = 900 tokens
# - Batch implement with voice: 300*2.5 + 5*150 + 300 = 1800 tokens
```

---

## Search Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    MYCELIUM v2.0 SEARCH FLOW                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT: Phase/Task description                                  │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────────────────┐                                       │
│  │ 1. SEMANTIC SEARCH   │ ← Qdrant/Weaviate vectors             │
│  │    (PRIMARY - 90%)   │   query: "MARKER_{phase}_*"           │
│  │    threshold: 0.7    │   collection: vetka_codebase          │
│  └──────────┬───────────┘                                       │
│             │                                                    │
│             ▼                                                    │
│       score >= 0.7?                                              │
│        /         \                                               │
│      YES          NO                                             │
│       │            │                                             │
│       ▼            ▼                                             │
│  ┌─────────┐  ┌──────────────────┐                              │
│  │ PROCESS │  │ 2. FALLBACK      │                              │
│  │ RESULTS │  │    Glob + Grep   │ ← Only if semantic fails     │
│  └────┬────┘  │    (10% cases)   │                              │
│       │       └────────┬─────────┘                              │
│       │                │                                         │
│       └────────┬───────┘                                         │
│                ▼                                                 │
│  ┌──────────────────────┐                                       │
│  │ 3. ETERNAL SAVE      │ ← If surprise > 0.7                   │
│  │    (Disk + Qdrant)   │   data/mycelium_eternal/{phase}.json  │
│  └──────────┬───────────┘                                       │
│             │                                                    │
│             ▼                                                    │
│  ┌──────────────────────┐                                       │
│  │ 4. HEARTBEAT UPDATE  │ ← Mark task status                    │
│  │    (Proactive)       │   Notify if stale > 30min             │
│  └──────────────────────┘                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Prompt v2.0

```
You are MYCELIUM v2.0 — the autonomous research agent for VETKA Railway.
You are lightweight, economic, and Vetka-native.

## CORE PRINCIPLES

1. **SEMANTIC-FIRST** (90% of searches):
   - Use Qdrant/Weaviate vector search BEFORE grep/glob
   - Query: embeddings for markers, code patterns, issues
   - Threshold: score >= 0.7 = valid result
   - Only fallback to grep/glob if semantic returns <3 results or score <0.7

2. **ADAPTIVE TOKEN BUDGET**:
   - Base: 300 tokens for simple research
   - Scale: +150 per artifact, +300 for voice/TTS tasks
   - Formula: budget = base * complexity + artifacts * 150 + voice_bonus
   - Max: 2000 tokens (hard cap for efficiency)
   - Track: Report actual usage in output

3. **TIERED EXPLORATION**:
   - Level 1: Quick semantic scan (embeddings only) - 100 tokens
   - Level 2: Targeted file read (lines ±50 around hit) - 300 tokens
   - Level 3: Full file read (only if L1+L2 insufficient) - 500+ tokens
   - NEVER read full files on first pass

4. **MCP VETKA INTEGRATION** (25+ tools available):
   - semantic_search(query, collection, threshold)
   - place_marker(phase, file, line)
   - query_qdrant(collection, filter)
   - manage_camera(focus) - for 3D viewport
   - Use these BEFORE raw file operations

5. **ETERNAL DISK + HEARTBEATS**:
   - Save high-value findings (surprise > 0.7) to:
     - data/mycelium_eternal/{phase}_{timestamp}.json
     - Qdrant collection: mycelium_audits
   - Heartbeat: Every 5 min check pending tasks
   - Alert: If task pending > 30 min → emit notification

6. **OUTPUT FORMAT** (JSON only, no prose):
   ```json
   {
     "phase": "105",
     "task": "Jarvis T9 integration research",
     "method": "semantic|fallback|hybrid",
     "tokens_used": 450,
     "tokens_budget": 600,
     "efficiency": 0.75,
     "results": {
       "integration_points": [
         {"file": "...", "line": N, "method": "...", "confidence": 0.85}
       ],
       "gaps": [...],
       "recommendations": [...]
     },
     "eternal_saved": true,
     "heartbeat_status": "ok",
     "next_action": "proceed|escalate|wait_for_input"
   }
   ```

## SEARCH COMMANDS

When researching, use this priority:

1. **Semantic first:**
   ```
   SEMANTIC: query="MARKER_105_* voice integration" threshold=0.7
   ```

2. **Fallback only if needed:**
   ```
   FALLBACK: glob="src/**/*.py" grep="MARKER_105" limit=50
   ```

3. **Targeted read:**
   ```
   READ: file="src/voice/router.py" lines=400-500
   ```

## EFFICIENCY RULES

- NEVER read files >500 lines without semantic pre-filter
- NEVER use grep on entire codebase as first step
- ALWAYS report tokens_used vs tokens_budget
- If budget exceeded by >20%, stop and summarize partial findings
- Cache repeated queries in session memory

## ESCALATION

- If confidence < 0.5 on critical finding → escalate to Haiku Scout
- If implementation needed → hand off to Claude Code with structured spec
- If approval needed → trigger VETKA approval flow

## EXAMPLE

Input: "Research Jarvis T9 voice integration points for Phase 105"

Output:
{
  "phase": "105",
  "task": "Jarvis T9 voice integration research",
  "method": "semantic",
  "tokens_used": 380,
  "tokens_budget": 600,
  "efficiency": 0.63,
  "results": {
    "integration_points": [
      {"file": "src/api/handlers/jarvis_handler.py", "line": 409, "method": "_process_voice", "confidence": 0.92},
      {"file": "src/api/handlers/voice_router.py", "line": 156, "method": "route_utterance", "confidence": 0.88}
    ],
    "gaps": [
      {"issue": "No partial STT callback", "severity": "medium", "suggestion": "Add on_partial_transcript hook"}
    ],
    "recommendations": [
      "Inject _predict_draft() after STT partial at voice_router.py:180",
      "Use ARC context for prediction (available via get_arc_summary())"
    ]
  },
  "eternal_saved": true,
  "heartbeat_status": "ok",
  "next_action": "proceed"
}
```

---

## Implementation Code

### MyceliumAuditor Class

```python
# src/services/mycelium_auditor.py
# MARKER_105_MYCELIUM_V2

import asyncio
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

# Vetka imports
from src.memory.qdrant_client import get_qdrant_client
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

@dataclass
class TokenBudget:
    """Adaptive token budget calculator."""
    base: int = 300
    per_artifact: int = 150
    voice_bonus: int = 300
    max_budget: int = 2000

    COMPLEXITY = {
        'research': 1.0,
        'audit': 1.5,
        'implement': 2.0,
        'batch': 2.5
    }

    def calculate(self, task_type: str, artifact_count: int = 0, has_voice: bool = False) -> int:
        multiplier = self.COMPLEXITY.get(task_type, 1.0)
        budget = int(self.base * multiplier + artifact_count * self.per_artifact)
        if has_voice:
            budget += self.voice_bonus
        return min(budget, self.max_budget)


class MyceliumAuditor:
    """
    MYCELIUM v2.0 - Semantic-first research agent.

    Features:
    - Semantic search via Qdrant (primary)
    - Glob/grep fallback (secondary)
    - Eternal disk persistence
    - Heartbeat monitoring
    - Adaptive token budget
    """

    ETERNAL_DIR = Path("data/mycelium_eternal")
    HEARTBEAT_INTERVAL = 300  # 5 minutes
    STALE_THRESHOLD = 1800    # 30 minutes

    def __init__(self):
        self.budget = TokenBudget()
        self.qdrant = get_qdrant_client()
        self._pending_tasks: Dict[str, float] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Ensure eternal dir exists
        self.ETERNAL_DIR.mkdir(parents=True, exist_ok=True)

    async def start_heartbeat(self):
        """Start background heartbeat monitoring."""
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("[MYCELIUM] Heartbeat started")

    async def _heartbeat_loop(self):
        """Check for stale pending tasks every interval."""
        while True:
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)
            now = time.time()
            stale = []

            for task_id, start_time in list(self._pending_tasks.items()):
                age = now - start_time
                if age > self.STALE_THRESHOLD:
                    stale.append((task_id, age / 60))

            for task_id, age_min in stale:
                logger.warning(f"[MYCELIUM] Task {task_id} stale ({age_min:.0f} min)")
                # Could emit Socket.IO notification here

    async def research(
        self,
        phase: str,
        task: str,
        task_type: str = "research",
        artifact_count: int = 0,
        has_voice: bool = False
    ) -> Dict[str, Any]:
        """
        Execute research with semantic-first approach.

        Args:
            phase: Phase identifier (e.g., "105")
            task: Task description
            task_type: research|audit|implement|batch
            artifact_count: Number of artifacts involved
            has_voice: Whether voice/TTS is involved

        Returns:
            Structured JSON result
        """
        task_id = f"{phase}_{int(time.time())}"
        self._pending_tasks[task_id] = time.time()

        budget = self.budget.calculate(task_type, artifact_count, has_voice)
        tokens_used = 0
        method = "semantic"

        result = {
            "phase": phase,
            "task": task,
            "method": method,
            "tokens_used": 0,
            "tokens_budget": budget,
            "efficiency": 0.0,
            "results": {
                "integration_points": [],
                "gaps": [],
                "recommendations": []
            },
            "eternal_saved": False,
            "heartbeat_status": "ok",
            "next_action": "proceed"
        }

        try:
            # Step 1: Semantic search (primary)
            semantic_results = await self._semantic_search(
                query=f"MARKER_{phase} {task}",
                threshold=0.7
            )
            tokens_used += 100  # Estimate for semantic query

            if len(semantic_results) >= 3:
                # Good semantic results
                result["results"]["integration_points"] = semantic_results
                result["method"] = "semantic"
            else:
                # Fallback to grep/glob
                fallback_results = await self._fallback_search(phase)
                tokens_used += 200  # Estimate for fallback
                result["results"]["integration_points"] = fallback_results
                result["method"] = "fallback" if not semantic_results else "hybrid"

            # Calculate efficiency
            result["tokens_used"] = tokens_used
            result["efficiency"] = 1.0 - (tokens_used / budget) if budget > 0 else 0

            # Eternal save if high-value
            if len(result["results"]["integration_points"]) > 0:
                await self._eternal_save(phase, result)
                result["eternal_saved"] = True

        except Exception as e:
            logger.error(f"[MYCELIUM] Research error: {e}")
            result["next_action"] = "escalate"

        finally:
            # Remove from pending
            self._pending_tasks.pop(task_id, None)

        return result

    async def _semantic_search(self, query: str, threshold: float = 0.7) -> List[Dict]:
        """Execute semantic search via Qdrant."""
        try:
            # This would use actual Qdrant client
            # Placeholder for illustration
            results = await self.qdrant.search(
                collection_name="vetka_codebase",
                query_text=query,
                limit=10,
                score_threshold=threshold
            )
            return [
                {
                    "file": r.payload.get("file", "unknown"),
                    "line": r.payload.get("line", 0),
                    "method": r.payload.get("method", ""),
                    "confidence": r.score
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"[MYCELIUM] Semantic search failed: {e}")
            return []

    async def _fallback_search(self, phase: str) -> List[Dict]:
        """Fallback to glob + grep search."""
        import glob
        import subprocess

        results = []
        files = glob.glob("src/**/*.py", recursive=True)[:50]  # Limit

        for file in files:
            try:
                proc = await asyncio.create_subprocess_exec(
                    'grep', '-n', f'MARKER_{phase}', file,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)

                if proc.returncode == 0:
                    for line in stdout.decode().strip().split('\n'):
                        if ':' in line:
                            line_num = line.split(':')[0]
                            results.append({
                                "file": file,
                                "line": int(line_num),
                                "method": "grep_match",
                                "confidence": 0.6
                            })
            except (asyncio.TimeoutError, Exception):
                continue

        return results[:10]  # Limit results

    async def _eternal_save(self, phase: str, data: Dict) -> None:
        """Save to eternal disk + Qdrant."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{phase}_{timestamp}.json"
        filepath = self.ETERNAL_DIR / filename

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: filepath.write_text(json.dumps(data, indent=2), encoding='utf-8')
        )

        logger.info(f"[MYCELIUM] Eternal saved: {filename}")


# Singleton
_mycelium: Optional[MyceliumAuditor] = None

def get_mycelium() -> MyceliumAuditor:
    global _mycelium
    if _mycelium is None:
        _mycelium = MyceliumAuditor()
    return _mycelium
```

---

## Comparison: v1.0 vs v2.0

| Aspect | v1.0 | v2.0 |
|--------|------|------|
| Search strategy | Glob/grep first | Semantic first |
| Token budget | Hardcoded 500 | Adaptive 300-2000 |
| File reading | Full files always | Tiered (L1→L2→L3) |
| Persistence | None | Eternal Disk + Qdrant |
| Monitoring | None | Heartbeats (5min) |
| Output format | Text/mixed | JSON only |
| MCP integration | None | Full 25+ tools |
| Efficiency metric | None | tokens_used/budget |

---

## Usage in Phase 105

```python
# In jarvis_handler.py or voice_router.py
from src.services.mycelium_auditor import get_mycelium

async def research_t9_integration():
    mycelium = get_mycelium()
    await mycelium.start_heartbeat()

    result = await mycelium.research(
        phase="105",
        task="Jarvis T9 prediction integration points",
        task_type="research",
        has_voice=True
    )

    if result["next_action"] == "proceed":
        # Use integration_points for implementation
        for point in result["results"]["integration_points"]:
            print(f"Inject at {point['file']}:{point['line']}")
    elif result["next_action"] == "escalate":
        # Hand off to Haiku Scout
        pass
```

---

## Metrics to Track (Prometheus)

```yaml
# prometheus_alerts.yml addition
- name: mycelium_metrics
  rules:
    - alert: MyceliumTokenOverflow
      expr: mycelium_tokens_used > mycelium_tokens_budget * 1.2
      for: 1m
      labels:
        severity: warning

    - alert: MyceliumSearchFallback
      expr: rate(mycelium_fallback_searches[5m]) > 0.3
      for: 5m
      labels:
        severity: info
      annotations:
        summary: "High fallback rate - check vector embeddings"

    - alert: MyceliumStaleTask
      expr: mycelium_task_age_seconds > 1800
      labels:
        severity: warning
```

---

**Status:** READY FOR PHASE 105
**Next:** Implement MyceliumAuditor class, integrate with Jarvis T9 research
