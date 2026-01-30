"""
VETKA Autogen Extension - Phase 7 Integration.

Adds Autogen + EvalAgent support to OrchestratorWithElisya.
Phase 7.1: MemoryManager integration + ollama SDK.

@status: active
@phase: 96
@depends: src.agents.eval_agent, src.orchestration.memory_manager, src.elisya.state, autogen
@used_by: src.orchestration.orchestrator_with_elisya
"""

import time
import uuid
from typing import Dict, Any, Optional
from src.agents.eval_agent import EvalAgent
from src.orchestration.memory_manager import MemoryManager
from src.elisya.state import ElisyaState, ConversationMessage


class AutogenExtension:
    """
    Extension module for OrchestratorWithElisya
    Provides execute_autogen_workflow_with_eval() method
    ✅ Phase 7.1: Uses ollama SDK + MemoryManager for high-score saving
    """
    
    def __init__(self, orchestrator):
        """Initialize with reference to main orchestrator"""
        self.orchestrator = orchestrator
        self.memory = MemoryManager()
        # ✅ NEW: Pass MemoryManager to EvalAgent for high-score automatic saving
        self.eval_agent = EvalAgent(
            model="deepseek-coder:6.7b",
            memory_manager=self.memory  # Enable automatic high-score saving
        )
    
    def execute_autogen_workflow_with_eval(
        self,
        feature_request: str,
        workflow_id: str = None,
    ) -> Dict[str, Any]:
        """
        Phase 7: Execute workflow using Autogen + Elisya + EvalAgent
        
        This integration:
        1. Uses Autogen GroupChat for multi-agent conversation
        2. Records all messages to Elisya State
        3. Evaluates final output with EvalAgent (LOD-aware)
        4. Automatically saves high-scores (>0.8) to Weaviate
        5. Returns comprehensive results
        
        Args:
            feature_request: Feature description
            workflow_id: Optional workflow ID
            
        Returns:
            {
                'workflow_id': str,
                'feature': str,
                'autogen_messages': [...],
                'final_output': str,
                'evaluation': {...},
                'duration': float,
                'status': 'complete' or 'error'
            }
        """
        workflow_id = workflow_id or str(uuid.uuid4())[:8]
        
        print('\n' + '='*70)
        print(f'🌳 VETKA AUTOGEN WORKFLOW WITH EVALAGENT [{workflow_id}]')
        print('='*70)
        
        result = {
            'workflow_id': workflow_id,
            'feature': feature_request,
            'autogen_messages': [],
            'final_output': '',
            'evaluation': {},
            'duration': 0,
            'status': 'complete',
            'error': None,
            'execution_mode': 'autogen_with_eval',
        }
        
        start_time = time.time()
        
        try:
            # Import Autogen components
            try:
                from autogen import AssistantAgent, GroupChat, GroupChatManager
            except ImportError:
                print("⚠️  Autogen not installed. Install with: pip install pyautogen")
                result['status'] = 'error'
                result['error'] = 'Autogen not installed'
                return result
            
            # Initialize ElisyaState for this workflow
            elisya_state = self.orchestrator._get_or_create_state(workflow_id, feature_request)
            
            print(f"\n✅ Initialized Autogen workflow")
            print(f"   Workflow ID: {workflow_id}")
            print(f"   Semantic path: {elisya_state.semantic_path}")
            
            # ===== SETUP AUTOGEN AGENTS =====
            print(f"\n📋 Creating Autogen agents...")
            
            config_list = [
                {
                    "model": "llama3.1",
                    "api_type": "ollama",
                    "api_base": "http://localhost:11434",
                }
            ]
            
            pm_autogen = AssistantAgent(
                name="PM",
                system_message="You are a Product Manager. Analyze the feature request and create a detailed plan. Be concise but thorough.",
                llm_config={"config_list": config_list, "temperature": 0.7, "max_tokens": 1000}
            )
            
            dev_autogen = AssistantAgent(
                name="Dev",
                system_message="You are a Senior Developer. Implement the feature based on the PM's plan. Focus on clean, production-ready code.",
                llm_config={"config_list": config_list, "temperature": 0.5, "max_tokens": 1500}
            )
            
            qa_autogen = AssistantAgent(
                name="QA",
                system_message="You are a QA Engineer. Write comprehensive tests for the feature. Use TDD principles.",
                llm_config={"config_list": config_list, "temperature": 0.5, "max_tokens": 1000}
            )
            
            print("✅ Autogen agents created: PM, Dev, QA")
            
            # ===== SETUP GROUPCHAT =====
            print(f"\n🔄 Setting up GroupChat...")
            
            groupchat = GroupChat(
                agents=[pm_autogen, dev_autogen, qa_autogen],
                messages=[],
                max_round=4,
                admin_name="PM"
            )
            
            manager = GroupChatManager(
                groupchat=groupchat,
                llm_config={"config_list": config_list, "temperature": 0.3}
            )
            
            print("✅ GroupChat initialized (max 4 rounds)")
            
            # ===== MESSAGE CAPTURE =====
            print(f"\n🚀 Starting Autogen GroupChat...")
            
            # Initiate chat
            try:
                pm_autogen.initiate_chat(
                    manager,
                    message=f"Please analyze and plan implementation for: {feature_request[:500]}"
                )
            except Exception as e:
                print(f"⚠️  Autogen chat error (may be expected): {e}")
            
            # Extract messages from groupchat
            autogen_messages = [
                {
                    'speaker': msg.get('name', 'unknown'),
                    'content': msg.get('content', '')[:500],  # Truncate
                    'timestamp': time.time()
                }
                for msg in groupchat.messages[-10:]  # Last 10 messages
            ]
            
            print(f"✅ Autogen GroupChat completed: {len(autogen_messages)} messages")
            
            # ===== UPDATE ELISYA STATE =====
            print(f"\n📝 Updating Elisya State...")
            
            elisya_state.speaker = 'Autogen'
            for msg in autogen_messages:
                elisya_state.conversation_history.append(
                    ConversationMessage(
                        speaker=msg['speaker'],
                        content=msg['content'][:500],
                        timestamp=msg['timestamp']
                    )
                )
            
            print(f"✅ Elisya State updated: {len(elisya_state.conversation_history)} messages")
            
            # ===== GET FINAL OUTPUT =====
            final_output = ""
            if groupchat.messages:
                # Get last message (usually Dev's implementation)
                for msg in reversed(groupchat.messages):
                    if msg.get('name') == 'Dev' and msg.get('content'):
                        final_output = msg.get('content', '')
                        break
                
                # Fallback: just get the last message
                if not final_output:
                    final_output = groupchat.messages[-1].get('content', '')
            
            print(f"\n📊 Final output length: {len(final_output)} chars")
            
            # ===== EVALAGENT EVALUATION =====
            print(f"\n🔍 Running EvalAgent (LOD-based)...")
            
            # Determine complexity based on feature length
            complexity = "MEDIUM"
            if len(feature_request) < 100:
                complexity = "SMALL"
            elif len(feature_request) > 500:
                complexity = "LARGE"
            
            print(f"   Complexity: {complexity}")
            
            # Evaluate with retry
            # ✅ NEW: EvalAgent will automatically save high-scores (>0.8) to Weaviate
            eval_result = self.eval_agent.evaluate_with_retry(
                task=feature_request,
                output=final_output,
                complexity=complexity
            )
            
            print(f"✅ EvalAgent complete:")
            print(f"   Score: {eval_result.get('score', 0):.2f}")
            print(f"   Status: {eval_result.get('final_status', 'unknown')}")
            print(f"   Token budget used: {eval_result.get('token_budget', 0)}")
            print(f"   Eval depth: {eval_result.get('eval_depth', 'unknown')}")
            if eval_result.get('score', 0) >= 0.8:
                print(f"   ✨ HIGH-SCORE: Automatically saved to Weaviate for few-shot learning!")
            
            # ===== SAVE RESULTS =====
            print(f"\n💾 Saving results to Weaviate...")
            
            self.memory.save_workflow_result(
                workflow_id,
                {
                    'feature': feature_request,
                    'autogen_messages': len(autogen_messages),
                    'final_output': final_output[:1000],
                    'eval_score': eval_result.get('score', 0),
                    'execution_mode': 'autogen_with_eval'
                }
            )
            
            # ===== BUILD RESULT =====
            result['autogen_messages'] = autogen_messages
            result['final_output'] = final_output
            result['evaluation'] = {
                'score': eval_result.get('score', 0),
                'feedback': eval_result.get('feedback', ''),
                'criteria': eval_result.get('scores', {}),
                'final_status': eval_result.get('final_status', 'unknown'),
                'retry_count': eval_result.get('retry_count', 0),
                'token_budget': eval_result.get('token_budget', 0),
                'eval_depth': eval_result.get('eval_depth', 'unknown'),
            }
            result['duration'] = time.time() - start_time
            result['status'] = 'complete'
            
            print('\n' + '='*70)
            print(f'✅ AUTOGEN WORKFLOW COMPLETE [{workflow_id}]')
            print(f'   Duration: {result["duration"]:.2f}s')
            print(f'   Messages: {len(autogen_messages)}')
            print(f'   Eval Score: {eval_result.get("score", 0):.2f}')
            print(f'   Eval Status: {eval_result.get("final_status", "unknown")}')
            print('='*70 + '\n')
            
            self.orchestrator.history.append(result)
            self.orchestrator.elisya_states[workflow_id] = elisya_state
            
        except Exception as e:
            print(f'\n❌ Autogen workflow error: {e}')
            import traceback
            traceback.print_exc()
            result['status'] = 'error'
            result['error'] = str(e)
            result['duration'] = time.time() - start_time
            self.memory.log_error(workflow_id, 'AutogenOrchestrator', str(e))
        
        return result
