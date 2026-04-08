"""
VETKA Agent Orchestrator - Manages multi-agent workflow execution.

@status: active
@phase: 96
@depends: src.agents, src.orchestration.progress_tracker, src.orchestration.memory_manager
@used_by: src.api, main
"""

import time
from typing import Optional

from src.agents import (
    VETKAPMAgent,
    VETKADevAgent,
    VETKAQAAgent,
    VETKAArchitectAgent
)
from src.agents.streaming_agent import StreamingAgent
from src.orchestration.progress_tracker import ProgressTracker
from src.orchestration.memory_manager import MemoryManager


class AgentOrchestrator:
    """Orchestrates multi-agent workflow execution with streaming and progress tracking"""
    
    def __init__(self, socketio=None):
        """
        Initialize orchestrator with optional Socket.IO for real-time updates
        
        Args:
            socketio: python-socketio AsyncServer for real-time updates (optional)
        """
        self.pm = VETKAPMAgent()
        self.dev = VETKADevAgent()
        self.qa = VETKAQAAgent()
        self.architect = VETKAArchitectAgent()
        self.socketio = socketio
        self.history = []
        self.memory = MemoryManager()

    def execute_full_workflow(self, feature_request: str) -> dict:
        """Execute full workflow (legacy, non-streaming)"""
        
        print('\n' + '='*70)
        print('🌳 VETKA FULL WORKFLOW')
        print('='*70)
        
        result = {
            'feature': feature_request,
            'steps': {},
            'duration': 0
        }
        
        start_time = time.time()
        
        try:
            # Step 1: PM Plans
            print('\n1️⃣  PM Agent - Planning...')
            pm_plan = self.pm.plan_feature(feature_request)
            result['steps']['pm_plan'] = pm_plan
            print('   ✅ Plan created')
            
            # Step 2: Architect Designs
            print('\n2️⃣  Architect Agent - Designing...')
            architecture = self.architect.design_solution(pm_plan)
            result['steps']['architecture'] = architecture
            print('   ✅ Architecture designed')
            
            # Step 3: Dev Implements
            print('\n3️⃣  Dev Agent - Implementing...')
            implementation = self.dev.implement_feature(pm_plan)
            result['steps']['implementation'] = implementation
            print('   ✅ Implementation plan created')
            
            # Step 4: QA Tests
            print('\n4️⃣  QA Agent - Testing...')
            test_plan = self.qa.test_feature(feature_request)
            result['steps']['test_plan'] = test_plan
            print('   ✅ Test plan created')
            
            result['status'] = 'complete'
            result['duration'] = time.time() - start_time
            
            print('\n' + '='*70)
            print('✅ WORKFLOW COMPLETE')
            print('='*70)
            
            # Store in history
            self.history.append(result)
            
        except Exception as e:
            print(f'\n❌ Workflow error: {e}')
            result['status'] = 'error'
            result['error'] = str(e)
            result['duration'] = time.time() - start_time
        
        return result

    def execute_full_workflow_streaming(
        self,
        feature_request: str,
        workflow_id: str = None
    ) -> dict:
        """
        Execute full workflow with real-time streaming and progress tracking
        
        Args:
            feature_request: Feature description
            workflow_id: Unique workflow ID for tracking
        
        Returns:
            Complete workflow result with all agent outputs
        """
        import uuid
        
        workflow_id = workflow_id or str(uuid.uuid4())[:8]
        
        print('\n' + '='*70)
        print(f'🌳 VETKA STREAMING WORKFLOW [{workflow_id}]')
        print('='*70)
        
        result = {
            'workflow_id': workflow_id,
            'feature': feature_request,
            'pm_plan': '',
            'architecture': '',
            'implementation': '',
            'tests': '',
            'status': 'complete',
            'error': None,
            'duration': 0
        }
        
        # Initialize progress tracker
        progress = ProgressTracker(
            socketio=self.socketio,
            agent_names=['PM', 'Architect', 'Dev', 'QA']
        )
        
        start_time = time.time()
        
        try:
            # Create streaming agents
            pm_streaming = StreamingAgent(self.pm, self.socketio)
            arch_streaming = StreamingAgent(self.architect, self.socketio)
            dev_streaming = StreamingAgent(self.dev, self.socketio)
            qa_streaming = StreamingAgent(self.qa, self.socketio)
            
            # Step 1: PM Plans
            print('\n1️⃣  PM Agent - Planning with streaming...')
            progress.start_agent('PM')
            plan = pm_streaming.plan_feature_streaming(feature_request)
            result['pm_plan'] = plan
            self.memory.save_agent_output('PM', plan, workflow_id, 'planning')
            progress.complete_agent('PM')
            print('   ✅ Plan created and streamed')
            
            # Step 2: Architect Designs
            print('\n2️⃣  Architect Agent - Designing with streaming...')
            progress.start_agent('Architect')
            design = arch_streaming.design_solution_streaming(feature_request)
            result['architecture'] = design
            self.memory.save_agent_output('Architect', design, workflow_id, 'design')
            progress.complete_agent('Architect')
            print('   ✅ Architecture designed and streamed')
            
            # Step 3: Dev Implements
            print('\n3️⃣  Dev Agent - Implementing with streaming...')
            progress.start_agent('Dev')
            impl = dev_streaming.implement_feature_streaming(plan)
            result['implementation'] = impl
            self.memory.save_agent_output('Dev', impl, workflow_id, 'implementation')
            progress.complete_agent('Dev')
            print('   ✅ Implementation created and streamed')
            
            # Step 4: QA Tests
            print('\n4️⃣  QA Agent - Testing with streaming...')
            progress.start_agent('QA')
            tests = qa_streaming.test_feature_streaming(feature_request)
            result['tests'] = tests
            self.memory.save_agent_output('QA', tests, workflow_id, 'testing')
            progress.complete_agent('QA')
            print('   ✅ Tests created and streamed')
            
            result['status'] = 'complete'
            result['duration'] = time.time() - start_time
            
            # Save complete workflow
            self.memory.save_workflow_result(workflow_id, result)
            
            print('\n' + '='*70)
            print('✅ STREAMING WORKFLOW COMPLETE')
            print(f'   Duration: {result["duration"]:.2f}s')
            print('='*70)
            
            # Store in history
            self.history.append(result)
            
        except Exception as e:
            print(f'\n❌ Workflow error: {e}')
            result['status'] = 'error'
            result['error'] = str(e)
            result['duration'] = time.time() - start_time
            
            # Log error to memory
            self.memory.log_error(workflow_id, 'Orchestrator', str(e))
            
            # Update progress with error
            progress.error_agent('Orchestrator', str(e))
        
        return result

    def get_workflow_history(self, limit: int = 10):
        """Get workflow execution history"""
        return {
            'local_history': self.history[-limit:],
            'weaviate_history': self.memory.get_workflow_history(limit)
        }

    def get_agent_statistics(self):
        """Get statistics about agent performance"""
        return {
            'total_workflows': len(self.history),
            'successful': sum(1 for w in self.history if w.get('status') == 'complete'),
            'failed': sum(1 for w in self.history if w.get('status') == 'error'),
            'agents': {
                'pm_stats': self.memory.get_agent_stats('PM'),
                'dev_stats': self.memory.get_agent_stats('Dev'),
                'qa_stats': self.memory.get_agent_stats('QA'),
                'architect_stats': self.memory.get_agent_stats('Architect'),
            }
        }


    def _build_context_section(self, past_feedback, examples):
        lines = ['', '='*60, '🧠 LEARNING CONTEXT FROM PAST TASKS:', '='*60]
        
        if past_feedback:
            lines.append('PAST FEEDBACK:')
            for fb in past_feedback:
                emoji = '✅' if fb.get('rating') == '👍' else '❌'
                correction = fb.get('correction', 'No correction')
                lines.append(f'{emoji} {correction}')
        
        if examples:
            lines.append('HIGH-QUALITY EXAMPLES:')
            for ex in examples:
                task = ex.get('task', '')[:100]
                score = ex.get('score', 'N/A')
                lines.append(f'- Task: {task}')
                lines.append(f'  Score: {score}')
        
        lines.append('='*60)
        return '\n'.join(lines)

    async def execute_full_workflow_with_learning(self, feature, complexity, workflow_id):
        print(f'🧠 WORKFLOW WITH LEARNING: {workflow_id}')
        past_feedback = self.memory.retrieve_past_feedback(feature, limit=3)
        examples = self.memory.query_high_score_examples(complexity=complexity, limit=3, min_score=0.8)
        context_section = self._build_context_section(past_feedback, examples)
        print(f'   📝 Context: {len(past_feedback)} feedback + {len(examples)} examples')
        result = await self.execute_full_workflow_streaming(feature, workflow_id)
        return result
