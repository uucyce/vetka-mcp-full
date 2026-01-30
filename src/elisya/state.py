"""
ElisyaState: Shared memory layer for all agents.
NOT a database - a language where agents think together.

@status: active
@phase: 96
@depends: dataclasses, typing, enum, time
@used_by: elisya_state_service, orchestrator_with_elisya
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import time


class LODLevel(Enum):
    """Level of Detail for context filtering"""
    GLOBAL = "global"      # 500 tokens
    TREE = "tree"          # 1500 tokens
    LEAF = "leaf"          # 3000 tokens
    FULL = "full"          # 10000+ tokens


class SemanticTint(Enum):
    """Semantic context coloring for agent focus"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    SCALABILITY = "scalability"
    GENERAL = "general"


@dataclass
class ConversationMessage:
    """Single conversation turn"""
    speaker: str                          # PM|Dev|QA|Architect|EvalAgent
    content: str                          # Agent output
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


@dataclass
class FewShotExample:
    """Few-shot example for retry/learning"""
    agent_type: str                       # Dev|QA|Architect
    task: str                             # Task description
    output: str                           # Example output
    score: float                          # Quality score (0-1)
    semantic_path: str = ""               # Related path


@dataclass
class ElisyaState:
    """
    Shared memory state for all agents.
    
    This is the LANGUAGE that agents use to communicate.
    NOT JSON-RPC, NOT REST, NOT database queries.
    Pure state that every agent reads, interprets for their task, 
    and writes back results.
    """
    
    # === WORKFLOW IDENTITY ===
    workflow_id: str                      # Unique workflow ID
    speaker: str = "PM"                   # Current speaker
    semantic_path: str = "projects/unknown"  # Grows as conversation evolves
    
    # === CONTEXT & FILTERING ===
    context: str = ""                     # Reframed context (for current agent)
    lod_level: str = "tree"               # GLOBAL|TREE|LEAF|FULL
    tint: str = "general"                 # Security|Performance|Reliability|...
    
    # === MEMORY & LEARNING ===
    conversation_history: List[ConversationMessage] = field(default_factory=list)
    few_shots: List[FewShotExample] = field(default_factory=list)
    
    # === METRICS ===
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    score: float = 0.0                    # EvalAgent score
    
    # === EXECUTION STATE ===
    raw_context: str = ""                 # Original, unfiltered context
    original_request: Dict = field(default_factory=dict)  # User request metadata
    
    def add_message(self, speaker: str, content: str, metadata: Dict = None) -> None:
        """Add message to conversation history"""
        self.speaker = speaker  # Update speaker FIRST
        msg = ConversationMessage(
            speaker=speaker,
            content=content,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        self.conversation_history.append(msg)
    
    def get_last_n_messages(self, n: int = 3) -> List[ConversationMessage]:
        """Get last N messages for context"""
        return self.conversation_history[-n:] if self.conversation_history else []
    
    def get_conversation_text(self, limit_tokens: int = 1500) -> str:
        """Get conversation history as formatted text (truncated by tokens)"""
        text = ""
        for msg in reversed(self.conversation_history):
            line = f"[{msg.speaker}]: {msg.content}\n"
            text = line + text
            
            # Rough token count (1 token ≈ 4 chars)
            if len(text) * 0.25 > limit_tokens:
                break
        
        return text
    
    def set_tint(self, tint: str) -> None:
        """Set semantic tint (focus area)"""
        if tint in [t.value for t in SemanticTint]:
            self.tint = tint
    
    def set_lod(self, lod: str) -> None:
        """Set level of detail"""
        if lod in [l.value for l in LODLevel]:
            self.lod_level = lod
    
    def to_dict(self) -> Dict:
        """Serialize to dict for storage"""
        return {
            "workflow_id": self.workflow_id,
            "speaker": self.speaker,
            "semantic_path": self.semantic_path,
            "context": self.context,
            "lod_level": self.lod_level,
            "tint": self.tint,
            "conversation_history": [
                {
                    "speaker": msg.speaker,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "metadata": msg.metadata
                }
                for msg in self.conversation_history
            ],
            "few_shots": [
                {
                    "agent_type": fs.agent_type,
                    "task": fs.task,
                    "output": fs.output,
                    "score": fs.score,
                    "semantic_path": fs.semantic_path
                }
                for fs in self.few_shots
            ],
            "timestamp": self.timestamp,
            "retry_count": self.retry_count,
            "score": self.score,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ElisyaState":
        """Deserialize from dict"""
        state = cls(
            workflow_id=data.get("workflow_id", ""),
            speaker=data.get("speaker", "PM"),
            semantic_path=data.get("semantic_path", "projects/unknown"),
            context=data.get("context", ""),
            lod_level=data.get("lod_level", "tree"),
            tint=data.get("tint", "general"),
            timestamp=data.get("timestamp", time.time()),
            retry_count=data.get("retry_count", 0),
            score=data.get("score", 0.0),
        )
        
        # Restore conversation history
        for msg_data in data.get("conversation_history", []):
            msg = ConversationMessage(
                speaker=msg_data.get("speaker", ""),
                content=msg_data.get("content", ""),
                timestamp=msg_data.get("timestamp", time.time()),
                metadata=msg_data.get("metadata", {})
            )
            state.conversation_history.append(msg)
        
        # Restore few-shots
        for fs_data in data.get("few_shots", []):
            fs = FewShotExample(
                agent_type=fs_data.get("agent_type", ""),
                task=fs_data.get("task", ""),
                output=fs_data.get("output", ""),
                score=fs_data.get("score", 0.0),
                semantic_path=fs_data.get("semantic_path", "")
            )
            state.few_shots.append(fs)
        
        return state
