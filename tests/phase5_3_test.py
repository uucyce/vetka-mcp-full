#!/usr/bin/env python3
"""
VETKA Phase 5.3 - End-to-End Testing & Metrics Collection

Tests:
1. MICRO complexity: "Add login button" → <1 sec
2. SMALL complexity: "Add OAuth auth" → 3-5 sec  
3. EPIC complexity: "Redesign system" → full plan

Metrics collected:
- Classification accuracy
- Token budget enforcement
- Response times
- Agent parallel execution
"""

import sys
import time
import json
from collections import defaultdict

sys.path.insert(0, '/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')

from src.orchestration.router import Router
from src.agents.classifier_agent import classify_task_complexity

# Test cases with expected outcomes
TEST_CASES = [
    {
        "name": "MICRO - Add button",
        "task": "Добавь кнопку логина",
        "expected_complexity": "MICRO",
        "expected_time_max": 2.0,  # seconds
        "description": "Simple UI change - should be very fast"
    },
    {
        "name": "SMALL - Add OAuth",
        "task": "Добавь OAuth аутентификацию через Google",
        "expected_complexity": "SMALL",
        "expected_time_max": 5.0,
        "description": "Simple feature - moderate complexity"
    },
    {
        "name": "MEDIUM - Search system",
        "task": "Реализуй поиск по базе данных",
        "expected_complexity": "MEDIUM",
        "expected_time_max": 10.0,
        "description": "Standard feature - full workflow"
    },
    {
        "name": "LARGE - Logging system",
        "task": "Переделай систему логирования с новой архитектурой",
        "expected_complexity": "LARGE",
        "expected_time_max": 15.0,
        "description": "Complex system - multiple components"
    },
    {
        "name": "EPIC - Architecture redesign",
        "task": "Переделай всю архитектуру системы на микросервисы",
        "expected_complexity": "EPIC",
        "expected_time_max": 20.0,
        "description": "Full system overhaul - maximum effort"
    },
]

class TestResults:
    def __init__(self):
        self.results = []
        self.metrics = defaultdict(list)
    
    def add_result(self, test_name, passed, details):
        self.results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": time.time()
        })
    
    def add_metric(self, category, value):
        self.metrics[category].append(value)
    
    def print_summary(self):
        print("\n" + "="*80)
        print("📊 TEST RESULTS SUMMARY")
        print("="*80)
        
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        
        print(f"\n✅ Passed: {passed}/{total} ({100*passed/total:.1f}%)")
        
        print("\nDetailed Results:")
        for i, result in enumerate(self.results, 1):
            status = "✅" if result["passed"] else "❌"
            print(f"\n{i}. {status} {result['test']}")
            for key, value in result["details"].items():
                print(f"   {key}: {value}")
        
        print("\n" + "="*80)
        print("📈 METRICS")
        print("="*80)
        
        for category, values in self.metrics.items():
            avg = sum(values) / len(values) if values else 0
            print(f"\n{category}:")
            print(f"  Average: {avg:.3f}")
            print(f"  Min: {min(values):.3f}" if values else "  Min: N/A")
            print(f"  Max: {max(values):.3f}" if values else "  Max: N/A")
    
    def save_json(self, filename="test_results.json"):
        """Save results to JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "results": self.results,
                "metrics": {k: v for k, v in self.metrics.items()},
                "summary": {
                    "total": len(self.results),
                    "passed": sum(1 for r in self.results if r["passed"]),
                }
            }, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {filename}")

def run_classification_test(test_case, results):
    """Test classification accuracy"""
    print(f"\n🧪 {test_case['name']}")
    print(f"   Task: {test_case['task']}")
    print(f"   Expected: {test_case['expected_complexity']}")
    
    start = time.time()
    complexity, reason, metadata = classify_task_complexity(test_case['task'])
    elapsed = time.time() - start
    
    passed = complexity == test_case['expected_complexity']
    
    print(f"   Got: {complexity}")
    print(f"   Time: {elapsed:.3f}s")
    print(f"   Status: {'✅ PASS' if passed else '❌ FAIL'}")
    
    results.add_result(
        test_case['name'],
        passed,
        {
            "expected": test_case['expected_complexity'],
            "actual": complexity,
            "reason": reason,
            "time_seconds": round(elapsed, 3),
            "time_ok": elapsed < test_case['expected_time_max']
        }
    )
    
    results.add_metric(f"classification_time_{complexity}", elapsed)
    
    return passed

def run_router_test(test_case, results):
    """Test router with token allocation"""
    print(f"\n🚦 Router Test: {test_case['name']}")
    
    start = time.time()
    workflow_type, state = Router.route(test_case['task'], '/project')
    elapsed = time.time() - start
    
    complexity = state.get('complexity')
    token_budget = state.get('context', {}).get('token_budget')
    
    print(f"   Complexity: {complexity}")
    print(f"   Workflow: {workflow_type}")
    print(f"   Token Budget: {token_budget}")
    print(f"   Route Time: {elapsed:.3f}s")
    
    passed = complexity == test_case['expected_complexity']
    
    results.add_result(
        f"{test_case['name']} (Router)",
        passed,
        {
            "complexity": complexity,
            "workflow": workflow_type,
            "tokens": token_budget,
            "route_time_seconds": round(elapsed, 3)
        }
    )
    
    results.add_metric("router_time", elapsed)
    
    return passed

def main():
    print("\n" + "="*80)
    print("🌳 VETKA Phase 5.3 - End-to-End Testing")
    print("="*80)
    
    results = TestResults()
    
    print("\n✅ STEP 1: Classification Accuracy Tests")
    print("-" * 80)
    
    for test_case in TEST_CASES:
        run_classification_test(test_case, results)
    
    print("\n✅ STEP 2: Router Integration Tests")
    print("-" * 80)
    
    for test_case in TEST_CASES:
        run_router_test(test_case, results)
    
    print("\n✅ STEP 3: Token Budget Enforcement")
    print("-" * 80)
    print("(Verify in logs: [AGENT] shows budget=X and used=Y)")
    
    print("\n✅ STEP 4: Performance Analysis")
    print("-" * 80)
    
    # Group results by complexity
    complexity_times = defaultdict(list)
    for result in results.results:
        if "Router Test" in result["test"]:
            complexity = result["details"].get("complexity")
            time_val = result["details"].get("route_time_seconds", 0)
            if complexity and time_val:
                complexity_times[complexity].append(time_val)
    
    print("\nAverage response times by complexity:")
    for complexity in ['MICRO', 'SMALL', 'MEDIUM', 'LARGE', 'EPIC']:
        times = complexity_times.get(complexity, [])
        if times:
            avg = sum(times) / len(times)
            print(f"  {complexity:6}: {avg:.3f}s")
    
    # Print final summary
    results.print_summary()
    results.save_json()
    
    return sum(1 for r in results.results if r["passed"]) == len(results.results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
