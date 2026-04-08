"""
Classifier Agent - Task complexity classification with improved boundaries.

@status: active
@phase: 96
@depends: httpx, json
@used_by: orchestrator, routing
"""

import httpx
import re
import json
from typing import Tuple
from pathlib import Path


class ClassifierAgent:
    """Классифицирует сложность задач с 105 примерами"""
    
    def __init__(self, use_context=True):
        self.ollama_url = "http://localhost:11434"
        self.model = "llama3.1:8b-instruct-q4_0"
        self.timeout = 30
        self.use_context = use_context
        self.training_examples = self._load_training_examples()
    
    def _load_training_examples(self) -> list:
        """Загрузить 105 примеров"""
        try:
            data_path = Path(__file__).parent.parent.parent / "datasets" / "training_examples_extended.json"
            if data_path.exists():
                with open(data_path, 'r') as f:
                    examples = json.load(f)
                return examples
            return []
        except:
            return []
    
    def _build_context_prompt(self, task: str) -> str:
        """Построить промпт с примерами"""
        context = "LEARN FROM THESE EXAMPLES:\n"
        context += "="*70 + "\n\n"
        
        by_complexity = {}
        for ex in self.training_examples[:20]:
            c = ex.get('complexity', '')
            if c not in by_complexity:
                by_complexity[c] = []
            by_complexity[c].append(ex)
        
        for complexity in ["MICRO", "SMALL", "MEDIUM", "LARGE", "EPIC"]:
            if complexity in by_complexity:
                context += f"{complexity}:\n"
                for ex in by_complexity[complexity][:2]:
                    t = ex.get('task', '')[:55]
                    r = ex.get('reason', '')[:40]
                    context += f"  • {t:55} ({r})\n"
                context += "\n"
        
        context += "="*70 + "\n\n"
        return context
    
    def classify(self, task: str) -> Tuple[str, str, dict]:
        """Классификация с улучшенным промптом"""
        
        if self.use_context and self.training_examples:
            context = self._build_context_prompt(task)
            prompt = context + f"""Classify this NEW task:

TASK: {task}

TIME BOUNDARIES (Critical):
- MICRO:   < 1 min     (button color, typo, config)
- SMALL:   5-15 min    (form, component, simple)
- MEDIUM:  20-45 min   (auth system, search, dashboard)
- LARGE:   1-3 hours   (microservice, database, logging)
- EPIC:    3+ hours + ARCHITECTURE CHANGE (migration, full redesign, kubernetes, blockchain)

KEY: EPIC = Entire system architecture changes. Not just "big feature".

Answer:
CATEGORY: [MICRO|SMALL|MEDIUM|LARGE|EPIC]
REASON: [one line]"""
        else:
            prompt = f"""Classify:

TASK: {task}

- MICRO: <1 min
- SMALL: 5-15 min
- MEDIUM: 20-45 min  
- LARGE: 1-3 hours
- EPIC: 3+ hours + architecture change

CATEGORY: [MICRO|SMALL|MEDIUM|LARGE|EPIC]
REASON: [line]"""

        try:
            client = httpx.Client(base_url=self.ollama_url, timeout=self.timeout)
            resp = client.post("/api/generate", json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.05,
            })
            
            if resp.status_code == 200:
                response = resp.json().get("response", "")
                return self._parse_response(response, task)
            else:
                return "MEDIUM", "API error", {"error": resp.status_code}
        except Exception as e:
            return "MEDIUM", f"Fallback", {"error": str(e)}
    
    def _parse_response(self, response: str, task: str) -> Tuple[str, str, dict]:
        """Parse response"""
        cat_match = re.search(r'CATEGORY:\s*(MICRO|SMALL|MEDIUM|LARGE|EPIC)', response, re.IGNORECASE)
        category = cat_match.group(1).upper() if cat_match else "MEDIUM"
        
        reason_match = re.search(r'REASON:\s*(.+?)$', response, re.MULTILINE)
        reason = reason_match.group(1).strip() if reason_match else "Classified"
        
        return category, reason, {
            "examples_loaded": len(self.training_examples),
            "model": self.model,
        }


def classify_task_complexity(task: str, use_context: bool = True) -> Tuple[str, str, dict]:
    """Public API"""
    classifier = ClassifierAgent(use_context=use_context)
    return classifier.classify(task)
