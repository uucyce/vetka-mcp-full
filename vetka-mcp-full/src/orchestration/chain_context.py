"""
Chain Context Manager for VETKA Agent Chain.

Manages PM -> Dev -> QA -> context passing with artifact and score tracking.

@status: active
@phase: 96
@depends: dataclasses, typing
@used_by: src.orchestration.orchestrator_with_elisya, src.api.handlers
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class ChainStep:
    """Single step in agent chain"""
    agent: str
    input_message: str
    output: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    artifacts: List[Dict] = field(default_factory=list)
    score: Optional[float] = None
    
    def summary(self, max_chars: int = 200) -> str:
        """Get truncated summary of output"""
        if len(self.output) <= max_chars:
            return self.output
        return self.output[:max_chars] + "..."


@dataclass
class ChainContext:
    """Full context of PM → Dev → QA → Architect chain"""
    user_message: str
    steps: List[ChainStep] = field(default_factory=list)
    status: str = "running"  # running, completed, failed
    workflow_id: str = ""
    
    def add_step(self, agent: str, input_msg: str, output: str, 
                 artifacts: List[Dict] = None, score: float = None) -> ChainStep:
        """Add completed step to chain"""
        step = ChainStep(
            agent=agent,
            input_message=input_msg,
            output=output,
            artifacts=artifacts or [],
            score=score
        )
        self.steps.append(step)
        return step
    
    def get_previous_output(self) -> Optional[str]:
        """Get output from previous step (for context passing)"""
        if self.steps:
            return self.steps[-1].output
        return None
    
    def get_step_by_agent(self, agent: str) -> Optional[ChainStep]:
        """Get step by agent name"""
        for step in self.steps:
            if step.agent == agent:
                return step
        return None
    
    def build_context_for_agent(self, agent: str) -> str:
        """
        Build full context string for specific agent.
        This is the KEY function for chain context passing!
        
        Returns:
            str: Complete prompt context including user message + previous outputs
        """
        context_parts = []
        
        # Always include original user message
        context_parts.append(f"📝 ЗАПРОС ПОЛЬЗОВАТЕЛЯ:\n{self.user_message}")
        
        if agent == "PM":
            # PM is first - just user message
            context_parts.append("\n🔗 ТЫ ПЕРВЫЙ В ЦЕПОЧКЕ PM → Dev → Architect → QA")
            context_parts.append("Проанализируй задачу пользователя и сформулируй чёткие требования и план действий.")
            
        elif agent == "Architect":
            # Architect gets PM output
            pm_step = self.get_step_by_agent("PM")
            if pm_step:
                context_parts.append(f"\n📋 АНАЛИЗ ОТ PM АГЕНТА:\n{pm_step.output}")
            context_parts.append("\n🔗 ТЫ ВТОРОЙ В ЦЕПОЧКЕ PM → Dev → Architect → QA")
            context_parts.append("Спроектируй архитектуру решения на основе анализа PM.")
            
        elif agent == "Dev":
            # Dev gets PM + Architect outputs
            pm_step = self.get_step_by_agent("PM")
            architect_step = self.get_step_by_agent("Architect")
            
            if pm_step:
                context_parts.append(f"\n📋 ТРЕБОВАНИЯ ОТ PM:\n{pm_step.output[:800]}")
            if architect_step:
                context_parts.append(f"\n🏗️ АРХИТЕКТУРА ОТ ARCHITECT:\n{architect_step.output}")
            
            context_parts.append("\n🔗 ТЫ ТРЕТИЙ В ЦЕПОЧКЕ PM → Dev → Architect → QA")
            context_parts.append("Напиши код согласно требованиям PM и архитектуре Architect.")
            
        elif agent == "QA":
            # QA gets complete chain history
            pm_step = self.get_step_by_agent("PM")
            architect_step = self.get_step_by_agent("Architect")
            dev_step = self.get_step_by_agent("Dev")
            
            if pm_step and pm_step.output:
                context_parts.append(f"\n📋 ТРЕБОВАНИЯ (от PM):\n{str(pm_step.output)[:500]}")
            if architect_step and architect_step.output:
                context_parts.append(f"\n🏗️ АРХИТЕКТУРА (от Architect):\n{str(architect_step.output)[:500]}")
            if dev_step:
                context_parts.append(f"\n💻 КОД ОТ DEV:\n{dev_step.output}")
                if dev_step.artifacts:
                    artifact_names = [a.get('filename', 'unknown') for a in dev_step.artifacts]
                    context_parts.append(f"\n📦 АРТЕФАКТЫ DEV: {', '.join(artifact_names)}")
            
            context_parts.append("\n🔗 ТЫ ЧЕТВЁРТЫЙ В ЦЕПОЧКЕ PM → Dev → Architect → QA")
            context_parts.append("Проверь код Dev, тесты и дай оценку от 0 до 1.")
        
        return "\n".join(context_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/Socket.IO"""
        return {
            "workflow_id": self.workflow_id,
            "user_message": self.user_message,
            "status": self.status,
            "steps": [
                {
                    "agent": s.agent,
                    "output": s.output[:200] + "..." if len(s.output) > 200 else s.output,
                    "artifacts_count": len(s.artifacts),
                    "score": s.score,
                    "timestamp": s.timestamp
                }
                for s in self.steps
            ]
        }


def create_chain_context(user_message: str, workflow_id: str = "") -> ChainContext:
    """Factory function to create new chain context"""
    return ChainContext(user_message=user_message, workflow_id=workflow_id)
