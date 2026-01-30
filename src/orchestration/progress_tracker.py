"""
VETKA Progress Tracker - Real-time workflow progress updates.

@status: active
@phase: 96
@depends: dataclasses, typing
@used_by: src.orchestration.agent_orchestrator
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum
import time


class AgentStatus(Enum):
    """Agent execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class AgentProgress:
    """Track progress for a single agent"""
    name: str
    status: AgentStatus = AgentStatus.PENDING
    progress_percent: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return None


class ProgressTracker:
    """Track and emit workflow progress to UI via Socket.IO"""
    
    def __init__(self, socketio=None, agent_names: list = None):
        """
        Initialize progress tracker
        
        Args:
            socketio: Flask-SocketIO instance
            agent_names: List of agent names to track (e.g., ['PM', 'Architect', 'Dev', 'QA'])
        """
        self.socketio = socketio
        self.agents: Dict[str, AgentProgress] = {}
        self.workflow_start = time.time()
        
        # Initialize agents if names provided
        if agent_names:
            for name in agent_names:
                self.agents[name] = AgentProgress(name=name)
    
    def start_agent(self, agent_name: str):
        """Mark agent as started"""
        if agent_name not in self.agents:
            self.agents[agent_name] = AgentProgress(name=agent_name)
        
        self.agents[agent_name].status = AgentStatus.RUNNING
        self.agents[agent_name].start_time = time.time()
        self._emit_progress()
    
    def update_agent_progress(self, agent_name: str, progress_percent: int):
        """Update agent progress percentage"""
        if agent_name in self.agents:
            self.agents[agent_name].progress_percent = min(100, max(0, progress_percent))
            self._emit_progress()
    
    def complete_agent(self, agent_name: str, progress_percent: int = 100):
        """Mark agent as completed"""
        if agent_name not in self.agents:
            self.agents[agent_name] = AgentProgress(name=agent_name)
        
        self.agents[agent_name].status = AgentStatus.COMPLETE
        self.agents[agent_name].progress_percent = 100
        self.agents[agent_name].end_time = time.time()
        self._emit_progress()
    
    def error_agent(self, agent_name: str, error_message: str):
        """Mark agent as errored"""
        if agent_name not in self.agents:
            self.agents[agent_name] = AgentProgress(name=agent_name)
        
        self.agents[agent_name].status = AgentStatus.ERROR
        self.agents[agent_name].error_message = error_message
        self.agents[agent_name].end_time = time.time()
        self._emit_progress()
    
    def cancel_agent(self, agent_name: str):
        """Mark agent as cancelled"""
        if agent_name in self.agents:
            self.agents[agent_name].status = AgentStatus.CANCELLED
            self.agents[agent_name].end_time = time.time()
            self._emit_progress()
    
    def get_overall_progress(self) -> int:
        """Calculate overall workflow progress percentage"""
        if not self.agents:
            return 0
        
        total = len(self.agents)
        completed = sum(
            1 for p in self.agents.values() 
            if p.status in [AgentStatus.COMPLETE, AgentStatus.ERROR]
        )
        
        return int((completed / total) * 100)
    
    def get_overall_duration(self) -> float:
        """Get total workflow duration so far"""
        return time.time() - self.workflow_start
    
    def _emit_progress(self):
        """Emit progress update to all connected clients"""
        if not self.socketio:
            return
        
        progress_data = {
            'workflow_progress': self.get_overall_progress(),
            'workflow_duration': self.get_overall_duration(),
            'agents': [
                {
                    'name': p.name,
                    'status': p.status.value,
                    'progress': p.progress_percent,
                    'duration': p.duration,
                    'error': p.error_message
                }
                for p in self.agents.values()
            ],
            'timestamp': time.time()
        }
        
        self.socketio.emit("progress_update", progress_data)
    
    def to_dict(self) -> dict:
        """Export progress as dictionary"""
        return {
            'workflow_progress': self.get_overall_progress(),
            'workflow_duration': self.get_overall_duration(),
            'agents': [
                {
                    'name': p.name,
                    'status': p.status.value,
                    'progress': p.progress_percent,
                    'duration': p.duration,
                    'error': p.error_message
                }
                for p in self.agents.values()
            ]
        }
