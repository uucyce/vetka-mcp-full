"""
VETKA Router for workflow routing and task classification.

@status: active
@phase: 96
@depends: src.orchestration.workflow_state, src.agents.classifier_agent
@used_by: src.api.handlers, main
"""
import uuid
from src.orchestration.workflow_state import WorkflowState, TOKEN_BUDGETS
from src.agents.classifier_agent import classify_task_complexity

# Fallback for get_context_manager
def get_context_manager():
    """Fallback when Elysia is not available"""
    return None

# Token budgets by complexity
COMPLEXITY_TOKENS = {
    'MICRO': 500,
    'SMALL': 1500,
    'MEDIUM': 3000,
    'LARGE': 6000,
    'EPIC': 12000,
}

class Router:
    WORKFLOW_KEYWORDS = {
        'plan': 'pm_plan',
        'feature': 'dev_implement',
        'implement': 'dev_implement',
        'test': 'qa_test',
        'debug': 'debug',
        'refactor': 'refactor',
    }

    @staticmethod
    def route(command: str, path: str, context: dict = None, zoom_level: float = 1.0):
        # STEP 1: CLASSIFY task complexity using Llama 3.1
        complexity, reason, metadata = classify_task_complexity(command)
        print(f"\n📊 [CLASSIFY] {complexity}")
        print(f"   Reason: {reason}")
        
        # STEP 2: Determine workflow type
        workflow_type = Router._determine_workflow(command)
        
        # STEP 3: Allocate tokens based on complexity
        token_budget = COMPLEXITY_TOKENS.get(complexity, 3000)
        print(f"   Tokens: {token_budget}")
        
        try:
            cm = get_context_manager()
            if cm:
                elysia_context = cm.get_context_for_workflow(workflow_type, path, zoom_level)
            else:
                elysia_context = {}
        except:
            elysia_context = {}
        
        elysia_context.update({'budget': {'total_tokens': token_budget}, 'lod_level': 'tree', 'visible_branches': []})
        
        # STEP 4: Create state with classification metadata
        state = Router._create_initial_state(
            command, 
            path, 
            workflow_type, 
            {**(context or {}), **elysia_context, 'complexity': complexity, 'token_budget': token_budget}
        )
        return workflow_type, state

    @staticmethod
    def _determine_workflow(command: str) -> str:
        for keyword, workflow in Router.WORKFLOW_KEYWORDS.items():
            if keyword in command.lower():
                return workflow
        return 'pm_plan'

    @staticmethod
    def _create_initial_state(command, path, workflow_type, context):
        workflow_id = str(uuid.uuid4())[:8]
        token_budget = context.get('token_budget', TOKEN_BUDGETS.get(workflow_type, 3000))

        state = {
            'task': command,
            'task_type': workflow_type,
            'workflow_id': workflow_id,
            'path': path,
            'complexity': context.get('complexity', 'MEDIUM'),
            'zoom_level': context.get('zoom_level', 1.0),
            'lod_level': context.get('lod_level', 'tree'),
            'visible_collections': context.get('visible_branches', []),
            'context': {**context, 'token_budget': token_budget},
            'current_agent': None,
            'agent_outputs': [],
            'results': {},
            'memory_updates': [],
            'step_number': 0,
            'status': 'pending',
            'error': None,
            'messages': [
                {'role': 'system', 'content': f'Starting {workflow_type} (Complexity: {context.get("complexity", "MEDIUM")})'},
                {'role': 'user', 'content': command},
            ],
        }
        return state
