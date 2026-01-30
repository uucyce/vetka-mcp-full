#!/bin/bash
# Chat Panel Diagnostic Script
# Phase 18 Implementation Check

echo "==================================================================="
echo "🔍 CHAT PANEL PHASE 18 - DIAGNOSTIC REPORT"
echo "==================================================================="
echo ""

# 1. File exists?
echo "📁 STEP 1: Checking HTML file..."
if [ -f "frontend/templates/vetka_tree_3d.html" ]; then
    echo "   ✅ HTML file exists"
    ls -lh frontend/templates/vetka_tree_3d.html
else
    echo "   ❌ HTML file NOT found!"
    exit 1
fi
echo ""

# 2. New panel in file?
echo "🆕 STEP 2: Checking for new chat panel..."
PANEL_COUNT=$(grep -c 'id="chat-panel"' frontend/templates/vetka_tree_3d.html)
echo "   New chat-panel found: $PANEL_COUNT times"
if [ "$PANEL_COUNT" -gt "0" ]; then
    echo "   ✅ Chat panel HTML exists"
    grep -n 'id="chat-panel"' frontend/templates/vetka_tree_3d.html | head -2
else
    echo "   ❌ Chat panel HTML missing!"
fi
echo ""

# 3. CSS classes?
echo "🎨 STEP 3: Checking CSS..."
CSS_COUNT=$(grep -c '\.chat-panel {' frontend/templates/vetka_tree_3d.html)
echo "   CSS .chat-panel classes: $CSS_COUNT"
if [ "$CSS_COUNT" -gt "0" ]; then
    echo "   ✅ Chat panel CSS exists"
else
    echo "   ❌ Chat panel CSS missing!"
fi
echo ""

# 4. JavaScript function?
echo "⚡ STEP 4: Checking JavaScript..."
JS_COUNT=$(grep -c 'function onNodeSelected' frontend/templates/vetka_tree_3d.html)
echo "   onNodeSelected function: $JS_COUNT"
if [ "$JS_COUNT" -gt "0" ]; then
    echo "   ✅ Chat panel JavaScript exists"
else
    echo "   ❌ Chat panel JavaScript missing!"
fi

# Check interact.js
INTERACT_COUNT=$(grep -c 'interactjs' frontend/templates/vetka_tree_3d.html)
echo "   interact.js library: $INTERACT_COUNT references"
echo ""

# 5. Flask returning it?
echo "🌐 STEP 5: Checking Flask endpoint..."
if curl -s http://localhost:5001/3d > /dev/null 2>&1; then
    FLASK_RESULT=$(curl -s http://localhost:5001/3d | grep -c 'id="chat-panel"')
    echo "   Flask /3d contains chat-panel: $FLASK_RESULT"

    if [ "$FLASK_RESULT" -eq "0" ]; then
        echo "   ❌ PROBLEM: Flask not serving new HTML!"
        echo "   → Solution: Restart Flask server"
        echo "      pkill -9 -f python && python main_fixed_phase_7_8.py"
    else
        echo "   ✅ Flask serving correct HTML"
    fi

    # Check response size
    RESPONSE_SIZE=$(curl -s http://localhost:5001/3d | wc -c)
    echo "   Response size: $RESPONSE_SIZE bytes (~58KB expected)"
else
    echo "   ⚠️  Flask server not responding on port 5001"
    echo "   → Check if server is running: ps aux | grep python"
fi
echo ""

# 6. Old panels still present?
echo "🗑️  STEP 6: Checking for old panels..."
OLD_PANEL=$(grep -c 'Agent Activity\|agent-response-panel\|cam-status-panel' frontend/templates/vetka_tree_3d.html)
if [ "$OLD_PANEL" -gt "0" ]; then
    echo "   ⚠️  Found $OLD_PANEL old panel references"
    echo "   Lines containing old panels:"
    grep -n 'Agent Activity\|agent-response-panel\|cam-status-panel' frontend/templates/vetka_tree_3d.html | head -5
else
    echo "   ✅ No old panels found"
fi
echo ""

# 7. Check for syntax errors
echo "🔧 STEP 7: Checking HTML syntax..."
# Count opening and closing tags
OPEN_DIVS=$(grep -o '<div' frontend/templates/vetka_tree_3d.html | wc -l)
CLOSE_DIVS=$(grep -o '</div>' frontend/templates/vetka_tree_3d.html | wc -l)
echo "   Opening <div> tags: $OPEN_DIVS"
echo "   Closing </div> tags: $CLOSE_DIVS"
if [ "$OPEN_DIVS" -eq "$CLOSE_DIVS" ]; then
    echo "   ✅ Div tags balanced"
else
    echo "   ⚠️  Div tags unbalanced (difference: $((OPEN_DIVS - CLOSE_DIVS)))"
fi
echo ""

# 8. Backend Socket.IO handlers
echo "🔌 STEP 8: Checking backend handlers..."
BACKEND_CHAT=$(grep -c 'handle_load_chat_context\|handle_user_message' main_fixed_phase_7_8.py)
echo "   Backend chat handlers: $BACKEND_CHAT"
if [ "$BACKEND_CHAT" -gt "0" ]; then
    echo "   ✅ Backend Socket.IO handlers exist"
else
    echo "   ❌ Backend handlers missing!"
fi
echo ""

# Summary
echo "==================================================================="
echo "📊 SUMMARY & RECOMMENDATIONS"
echo "==================================================================="
echo ""

if [ "$PANEL_COUNT" -gt "0" ] && [ "$CSS_COUNT" -gt "0" ] && [ "$JS_COUNT" -gt "0" ]; then
    echo "✅ CODE STATUS: All Phase 18 code is present in HTML file"
    echo ""

    if [ "$FLASK_RESULT" -gt "0" ] 2>/dev/null; then
        echo "✅ FLASK STATUS: Server is serving correct HTML"
        echo ""
        echo "🎯 NEXT STEPS:"
        echo "   1. Hard refresh browser: Cmd+Shift+R (Mac) or Ctrl+F5 (Windows)"
        echo "   2. Or open Incognito mode: Cmd+Shift+N (Chrome)"
        echo "   3. Open DevTools (F12) and check Console for errors"
        echo "   4. In Console, type: document.getElementById('chat-panel')"
        echo "      → Should return HTMLDivElement, not null"
        echo "   5. Check panel visibility:"
        echo "      document.getElementById('chat-panel').style.display"
        echo "      → Should be 'flex', not 'none'"
        echo ""
        echo "🔍 LIKELY CAUSE: Browser cache"
        echo "   → Solution: Force hard refresh or use Incognito mode"
    else
        echo "❌ FLASK STATUS: Server not serving new HTML (cached)"
        echo ""
        echo "🎯 NEXT STEPS:"
        echo "   1. Kill Flask: lsof -ti:5001 | xargs kill -9"
        echo "   2. Clear Python cache: find . -name __pycache__ -exec rm -rf {} +"
        echo "   3. Restart: source .venv/bin/activate && python main_fixed_phase_7_8.py"
        echo "   4. Hard refresh browser: Cmd+Shift+R"
    fi
else
    echo "❌ CODE STATUS: Phase 18 code incomplete"
    echo ""
    echo "Missing components:"
    [ "$PANEL_COUNT" -eq "0" ] && echo "   ❌ Chat panel HTML"
    [ "$CSS_COUNT" -eq "0" ] && echo "   ❌ Chat panel CSS"
    [ "$JS_COUNT" -eq "0" ] && echo "   ❌ Chat panel JavaScript"
    echo ""
    echo "🎯 NEXT STEPS:"
    echo "   → Request CLEAN version of vetka_tree_3d.html"
fi

echo ""
echo "==================================================================="
echo "Diagnostic complete at $(date)"
echo "==================================================================="
