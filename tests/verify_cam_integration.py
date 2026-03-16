#!/usr/bin/env python3
"""
Phase 76.4: CAM Integration Verification Script
Tests CAM tools integration in VETKA agents
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_cam_tools_registration():
    """Test 1: Verify CAM tools are registered"""
    print("🔧 Test 1: CAM Tools Registration")
    print("=" * 50)

    try:
        # Import tools module to trigger registration
        import src.agents.tools
        from src.tools.base_tool import registry

        # Check CAM tools are registered
        cam_tools = [
            "calculate_surprise",
            "compress_with_elision",
            "adaptive_memory_sizing",
        ]

        for tool_name in cam_tools:
            tool = registry.get(tool_name)
            if tool:
                print(f"✅ {tool_name}: Registered")
            else:
                print(f"❌ {tool_name}: NOT registered")
                return False

        print("✅ All CAM tools registered successfully")
        return True

    except Exception as e:
        print(f"❌ CAM tools registration test failed: {e}")
        return False


async def test_agent_permissions():
    """Test 2: Verify agent permissions include CAM tools"""
    print("\n👥 Test 2: Agent Permissions")
    print("=" * 50)

    try:
        from src.agents.tools import AGENT_TOOL_PERMISSIONS

        # Expected CAM tools per agent type
        expected_tools = {
            "PM": ["calculate_surprise", "adaptive_memory_sizing"],
            "Dev": ["compress_with_elision", "adaptive_memory_sizing"],
            "QA": ["calculate_surprise", "adaptive_memory_sizing"],
            "Architect": [
                "calculate_surprise",
                "compress_with_elision",
                "adaptive_memory_sizing",
            ],
            "Researcher": [
                "calculate_surprise",
                "compress_with_elision",
                "adaptive_memory_sizing",
            ],
            "Hostess": ["calculate_surprise"],
        }

        all_passed = True

        for agent_type, expected in expected_tools.items():
            agent_tools = AGENT_TOOL_PERMISSIONS.get(agent_type, [])
            missing_tools = []

            for tool in expected:
                if tool not in agent_tools:
                    missing_tools.append(tool)

            if missing_tools:
                print(f"❌ {agent_type}: Missing {missing_tools}")
                all_passed = False
            else:
                print(f"✅ {agent_type}: All CAM tools available")

        return all_passed

    except Exception as e:
        print(f"❌ Agent permissions test failed: {e}")
        return False


async def test_get_tools_for_agent():
    """Test 3: Test enhanced get_tools_for_agent function"""
    print("\n🛠️ Test 3: Enhanced get_tools_for_agent")
    print("=" * 50)

    try:
        from src.agents.tools import get_tools_for_agent

        # Test with researcher (should have all CAM tools)
        tools = get_tools_for_agent("Researcher")
        tool_names = [tool.get("function", {}).get("name") for tool in tools]

        cam_tools = [
            "calculate_surprise",
            "compress_with_elision",
            "adaptive_memory_sizing",
        ]
        found_tools = []
        missing_tools = []

        for cam_tool in cam_tools:
            if cam_tool in tool_names:
                found_tools.append(cam_tool)
            else:
                missing_tools.append(cam_tool)

        print(f"✅ Researcher tools found: {found_tools}")
        if missing_tools:
            print(f"❌ Researcher tools missing: {missing_tools}")
            return False

        print(f"✅ Total tools available to Researcher: {len(tools)}")
        return True

    except Exception as e:
        print(f"❌ get_tools_for_agent test failed: {e}")
        return False


async def test_aura_functions():
    """Test 4: Test Aura lookup functions"""
    print("\n🧠 Test 4: Aura Functions")
    print("=" * 50)

    try:
        from src.memory.aura_store import aura_lookup

        # Test basic lookup (Level 1)
        result = await aura_lookup("test query")
        print(f"✅ Basic aura_lookup executed: {result is not None}")

        return True

    except Exception as e:
        print(f"❌ Aura functions test failed: {e}")
        return False


async def test_orchestrator_integration():
    """Test 5: Test orchestrator integration"""
    print("\n🎭 Test 5: Orchestrator Integration")
    print("=" * 50)

    try:
        # Check that orchestrator has the new methods
        from src.orchestration.orchestrator_with_elisya import OrchestratorWithElisya

        # Check methods exist
        has_get_tools = hasattr(OrchestratorWithElisya, "get_tools_for_agent")
        has_dynamic_search = hasattr(OrchestratorWithElisya, "dynamic_semantic_search")

        print(f"✅ get_tools_for_agent method: {has_get_tools}")
        print(f"✅ dynamic_semantic_search method: {has_dynamic_search}")

        return has_get_tools and has_dynamic_search

    except Exception as e:
        print(f"❌ Orchestrator integration test failed: {e}")
        return False


async def main():
    """Run all verification tests"""
    print("🚀 VETKA Phase 76.4: CAM Integration Verification")
    print("=" * 60)

    tests = [
        ("CAM Tools Registration", test_cam_tools_registration),
        ("Agent Permissions", test_agent_permissions),
        ("Enhanced get_tools_for_agent", test_get_tools_for_agent),
        ("Aura Functions", test_aura_functions),
        ("Orchestrator Integration", test_orchestrator_integration),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n📊 VERIFICATION SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All CAM integration tests passed!")
        print("✅ VETKA agents now have CAM tools integration!")
        return 0
    else:
        print("⚠️ Some tests failed. Check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
