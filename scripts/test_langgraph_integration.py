#!/usr/bin/env python3
"""
Phase 60.3: LangGraph Integration Test
Tests the full workflow with feature flag enabled

@file test_langgraph_integration.py
@status ACTIVE
@phase Phase 60.3 - Feature Flag Enable + Integration Testing
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_langgraph_workflow():
    """Test full LangGraph workflow execution"""

    print("\n" + "="*60)
    print("🧪 Phase 60.3: LangGraph Integration Test")
    print("="*60 + "\n")

    # Import after path setup
    from src.orchestration.orchestrator_with_elisya import (
        OrchestratorWithElisya,
        FEATURE_FLAG_LANGGRAPH
    )

    # Check feature flag
    print(f"📌 Feature Flag Status: {FEATURE_FLAG_LANGGRAPH}")
    if not FEATURE_FLAG_LANGGRAPH:
        print("❌ Feature flag is disabled! Enable it first.")
        return False

    print("✅ Feature flag is ENABLED\n")

    # Create orchestrator
    print("📦 Creating orchestrator...")
    try:
        orchestrator = OrchestratorWithElisya()
        print("✅ Orchestrator created\n")
    except Exception as e:
        print(f"❌ Failed to create orchestrator: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test request
    test_request = "Создай простую Python функцию для сложения двух чисел"
    workflow_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    print(f"📝 Test Request: {test_request}")
    print(f"📋 Workflow ID: {workflow_id}\n")

    # Track events
    events_received = []
    nodes_visited = []

    print("🚀 Starting workflow...\n")
    print("-" * 40)

    try:
        # Check if streaming method exists
        if hasattr(orchestrator, 'execute_with_langgraph_stream'):
            print("Using: execute_with_langgraph_stream()")

            async for event in orchestrator.execute_with_langgraph_stream(
                feature_request=test_request,
                workflow_id=workflow_id
            ):
                events_received.append(event)

                # Extract node name
                if isinstance(event, dict):
                    node_name = list(event.keys())[0] if event else "unknown"
                    nodes_visited.append(node_name)

                    state = event.get(node_name, {})

                    # Log progress
                    print(f"[{len(events_received):02d}] 📍 Node: {node_name}")

                    if 'current_agent' in state:
                        print(f"      Agent: {state['current_agent']}")

                    if 'eval_score' in state and state['eval_score'] is not None:
                        score = state['eval_score']
                        if score > 0:
                            passed = "✅ PASS" if score >= 0.75 else "❌ RETRY"
                            print(f"      Score: {score:.2f} {passed}")

                    if 'retry_count' in state and state['retry_count'] > 0:
                        print(f"      Retry: {state['retry_count']}/{state.get('max_retries', 3)}")

                    if 'next' in state:
                        print(f"      Next: {state['next']}")

                    print()

        elif hasattr(orchestrator, 'execute_with_langgraph'):
            print("Using: execute_with_langgraph() (non-streaming)")

            result = await orchestrator.execute_with_langgraph(
                feature_request=test_request,
                workflow_id=workflow_id
            )

            events_received.append(result)
            print(f"Result: {json.dumps(result, indent=2, default=str)[:500]}...")

        else:
            print("❌ No LangGraph execution method found!")
            print("Available methods:")
            for method in dir(orchestrator):
                if 'langgraph' in method.lower():
                    print(f"  - {method}")
            return False

    except Exception as e:
        print(f"\n❌ Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("-" * 40)
    print("\n📊 RESULTS SUMMARY\n")

    # Summary
    print(f"Total Events: {len(events_received)}")
    print(f"Nodes Visited: {' → '.join(nodes_visited)}")

    # Get final state
    if events_received:
        final_event = events_received[-1]
        if isinstance(final_event, dict):
            final_node = list(final_event.keys())[0]
            final_state = final_event.get(final_node, {})

            print(f"\n📋 Final State:")
            print(f"   Score: {final_state.get('eval_score', 'N/A')}")
            print(f"   Retries: {final_state.get('retry_count', 0)}")
            print(f"   Status: {final_state.get('next', 'unknown')}")

            # Check artifacts
            artifacts = final_state.get('artifacts', [])
            if artifacts:
                print(f"   Artifacts: {len(artifacts)}")
                for art in artifacts[:3]:
                    print(f"      - {art.get('name', 'unnamed')}")

    # Validate
    print("\n" + "="*60)
    print("✅ VALIDATION")
    print("="*60)

    checks = {
        "Events received": len(events_received) > 0,
        "Multiple nodes": len(nodes_visited) >= 3,
        "Has hostess": 'hostess' in nodes_visited,
        "Has eval": 'eval' in nodes_visited or any('eval' in str(n) for n in nodes_visited),
    }

    all_passed = True
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("🎉 Phase 60.3 Integration Test PASSED!")
    else:
        print("⚠️ Some checks failed - review output above")
    print("="*60 + "\n")

    return all_passed


async def test_retry_loop():
    """Test that retry loop works (score < 0.75 triggers learner)"""

    print("\n" + "="*60)
    print("🔄 Phase 60.3: Retry Loop Test")
    print("="*60 + "\n")

    from src.orchestration.langgraph_state import create_initial_state, should_retry

    # Test should_retry function
    print("Testing should_retry() function:\n")

    test_cases = [
        {"eval_score": 0.85, "retry_count": 0, "max_retries": 3, "expected": False},
        {"eval_score": 0.65, "retry_count": 0, "max_retries": 3, "expected": True},
        {"eval_score": 0.65, "retry_count": 2, "max_retries": 3, "expected": True},
        {"eval_score": 0.65, "retry_count": 3, "max_retries": 3, "expected": False},
        {"eval_score": 0.75, "retry_count": 0, "max_retries": 3, "expected": False},  # Threshold
    ]

    all_passed = True
    for tc in test_cases:
        state = create_initial_state("test", "context")
        state['eval_score'] = tc['eval_score']
        state['retry_count'] = tc['retry_count']
        state['max_retries'] = tc['max_retries']

        result = should_retry(state)
        passed = result == tc['expected']

        status = "✅" if passed else "❌"
        print(f"  {status} score={tc['eval_score']}, retry={tc['retry_count']}/{tc['max_retries']} → {result} (expected {tc['expected']})")

        if not passed:
            all_passed = False

    print()
    return all_passed


async def test_learner_agent():
    """Test LearnerAgent failure analysis"""

    print("\n" + "="*60)
    print("🧠 Phase 60.3: LearnerAgent Test")
    print("="*60 + "\n")

    try:
        from src.agents.learner_agent import LearnerAgent

        learner = LearnerAgent(memory_manager=None)

        # Test failure analysis
        result = await learner.analyze_failure(
            task="Create a function to calculate factorial",
            output="def factorial(n): return n * n",
            eval_feedback="Logic error: factorial(5) returns 25, expected 120",
            retry_count=0
        )

        print(f"Failure Category: {result.get('failure_category', 'unknown')}")
        print(f"Root Cause: {result.get('root_cause', 'unknown')[:100]}...")
        print(f"Confidence: {result.get('confidence', 0):.2f}")
        print(f"Enhanced Prompt: {result.get('enhanced_prompt', '')[:200]}...")

        # Validate
        checks = {
            "Has failure_category": 'failure_category' in result,
            "Has enhanced_prompt": 'enhanced_prompt' in result and len(result['enhanced_prompt']) > 0,
            "Has confidence": 'confidence' in result,
        }

        all_passed = True
        print("\nValidation:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}")
            if not passed:
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"❌ LearnerAgent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all Phase 60.3 tests"""

    print("\n" + "="*60)
    print("🚀 PHASE 60.3: INTEGRATION TESTING SUITE")
    print("="*60)
    print(f"Started: {datetime.now().isoformat()}")
    print("="*60 + "\n")

    results = {}

    # Test 1: Retry loop logic
    print("\n[Test 1/3] Retry Loop Logic")
    results['retry_loop'] = await test_retry_loop()

    # Test 2: LearnerAgent
    print("\n[Test 2/3] LearnerAgent")
    results['learner_agent'] = await test_learner_agent()

    # Test 3: Full workflow (only if others pass)
    print("\n[Test 3/3] Full Workflow Integration")
    if results['retry_loop'] and results['learner_agent']:
        results['full_workflow'] = await test_langgraph_workflow()
    else:
        print("⏭️ Skipping full workflow test (prerequisites failed)")
        results['full_workflow'] = False

    # Final summary
    print("\n" + "="*60)
    print("📊 FINAL SUMMARY")
    print("="*60)

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60)

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Phase 60.3 Complete!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed - review output above")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
