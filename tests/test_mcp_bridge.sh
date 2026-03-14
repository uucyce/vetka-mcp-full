#!/bin/bash
# Test VETKA MCP Bridge for OpenCode
# Usage: ./test_mcp_bridge.sh

set -e

PROJECT_ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
BRIDGE_PATH="$PROJECT_ROOT/src/mcp/vetka_mcp_bridge.py"

echo "🧪 VETKA MCP Bridge Test Suite"
echo "================================"
echo ""

# Test 1: Check if bridge file exists
echo "✅ Test 1: Bridge file exists"
if [ -f "$BRIDGE_PATH" ]; then
  echo "   Found: $BRIDGE_PATH"
else
  echo "   ❌ FAILED: Bridge file not found"
  exit 1
fi
echo ""

# Test 2: Check shebang
echo "✅ Test 2: Shebang check"
SHEBANG=$(head -n1 "$BRIDGE_PATH")
if [[ "$SHEBANG" == "#!/usr/bin/env python3" ]]; then
  echo "   ✅ Correct shebang: $SHEBANG"
else
  echo "   ⚠️  Shebang: $SHEBANG (expected #!/usr/bin/env python3)"
fi
echo ""

# Test 3: Check if Python can import the module
echo "✅ Test 3: Python import test"
cd "$PROJECT_ROOT"
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from src.mcp import vetka_mcp_bridge
    print('   ✅ Module imports successfully')
except ImportError as e:
    print(f'   ❌ Import failed: {e}')
    sys.exit(1)
" || exit 1
echo ""

# Test 4: Check if logger is defined
echo "✅ Test 4: Logger definition check"
if grep -q "^logger = " "$BRIDGE_PATH"; then
  echo "   ✅ Logger is defined"
else
  echo "   ❌ FAILED: Logger not found"
  exit 1
fi
echo ""

# Test 5: Check if VETKA server is running
echo "✅ Test 5: VETKA server connection"
if curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
  echo "   ✅ VETKA server is running on localhost:5001"
else
  echo "   ⚠️  VETKA server not responding (start with: python main.py)"
fi
echo ""

# Test 6: Check OpenCode config
echo "✅ Test 6: OpenCode config validation"
CONFIG_PATH="$PROJECT_ROOT/opencode.json"
if [ -f "$CONFIG_PATH" ]; then
  echo "   ✅ Config exists: $CONFIG_PATH"

  # Check if command uses absolute path
  if grep -q "\"$BRIDGE_PATH\"" "$CONFIG_PATH"; then
    echo "   ✅ Command uses absolute path"
  else
    echo "   ⚠️  Command might not use absolute path"
  fi

  # Check timeout
  TIMEOUT=$(grep -o '"timeout": [0-9]*' "$CONFIG_PATH" | grep -o '[0-9]*')
  if [ "$TIMEOUT" -ge 30000 ]; then
    echo "   ✅ Timeout is $TIMEOUT ms (>=30s)"
  else
    echo "   ⚠️  Timeout is $TIMEOUT ms (recommended: 30000+)"
  fi
else
  echo "   ❌ Config not found: $CONFIG_PATH"
  exit 1
fi
echo ""

# Test 7: Syntax check
echo "✅ Test 7: Python syntax check"
if python3 -m py_compile "$BRIDGE_PATH" 2>&1; then
  echo "   ✅ No syntax errors"
else
  echo "   ❌ FAILED: Syntax errors detected"
  exit 1
fi
echo ""

echo "================================"
echo "🎉 All tests passed!"
echo ""
echo "Next steps:"
echo "1. Restart OpenCode to reload config"
echo "2. Test MCP tools with: @vetka vetka_health"
echo "3. Check logs in: data/mcp_audit/"
