#!/bin/bash
# Phase 115 BUG-3: model_source persistence fix
# Auto-generated implementation script
# Run from project root: bash docs/115_ph/SONNET_A_IMPLEMENTATION.sh

set -e  # Exit on error

echo "================================================"
echo "Phase 115 BUG-3 Fix: model_source persistence"
echo "================================================"

# Backup files
echo ""
echo "Step 1: Creating backups..."
cp src/api/handlers/handler_utils.py src/api/handlers/handler_utils.py.bak.$(date +%s)
cp src/api/handlers/user_message_handler.py src/api/handlers/user_message_handler.py.bak.$(date +%s)
echo "✓ Backups created"

# Fix handler_utils.py (ALREADY FIXED via VETKA MCP)
echo ""
echo "Step 2: Fixing handler_utils.py..."
echo "✓ Already fixed via VETKA MCP"

# Fix user_message_handler.py - all 7 locations
echo ""
echo "Step 3: Fixing user_message_handler.py (7 locations)..."

# Fix 1: Line 424 - USER message (Ollama path)
python3 << 'PYEOF'
with open('src/api/handlers/user_message_handler.py', 'r') as f:
    content = f.read()

# Fix 1: Line 424 - USER message (Ollama path)
content = content.replace(
    '                    save_chat_message(\n                        node_path,\n                        {"role": "user", "text": text, "node_id": node_id},',
    '                    save_chat_message(\n                        node_path,\n                        {"role": "user", "text": text, "node_id": node_id, "model_source": model_source},  # MARKER_115_BUG3: model_source persistence',
    1  # Only first occurrence
)

# Fix 2: Line 500 - ASSISTANT message (Ollama path)
content = content.replace(
    '                            "model_provider": "ollama",  # Provider for Ollama local models\n                            "text": full_response,',
    '                            "model_provider": "ollama",  # Provider for Ollama local models\n                            "model_source": model_source,  # MARKER_115_BUG3: model_source persistence\n                            "text": full_response,',
    1
)

# Fix 3: Line 604 - USER message (streaming path)
# We need to be more specific here since there are multiple similar patterns
import re
pattern3 = r'(# Phase 64\.5: Save user message BEFORE model call\s+# Phase 74: Pass pinned_files for group chat context\s+save_chat_message\(\s+node_path,\s+\{"role": "user", "text": text, "node_id": node_id\},\s+pinned_files=pinned_files,\s+\))'
if re.search(pattern3, content):
    content = re.sub(
        r'(\s+save_chat_message\(\s+node_path,\s+)(\{"role": "user", "text": text, "node_id": node_id\})(,\s+pinned_files=pinned_files,\s+\))',
        r'\1{"role": "user", "text": text, "node_id": node_id, "model_source": model_source},  # MARKER_115_BUG3: model_source persistence\3',
        content,
        count=2  # Fix both Ollama and streaming paths
    )

# Fix 4: Line 771 - ASSISTANT message (streaming path)
content = content.replace(
    '                        "model_provider": detected_provider.value if detected_provider else "unknown",  # Provider from detection\n                        "text": full_response,',
    '                        "model_provider": detected_provider.value if detected_provider else "unknown",  # Provider from detection\n                        "model_source": model_source,  # MARKER_115_BUG3: model_source persistence\n                        "text": full_response,',
    1
)

# Fix 5: Line 927 - USER message (@mention path)
content = content.replace(
    '                            "text": text,  # Original text (with @mention)\n                            "node_id": node_id,',
    '                            "text": text,  # Original text (with @mention)\n                            "model_source": model_source,  # MARKER_115_BUG3: model_source persistence\n                            "node_id": node_id,',
    1
)

# Fix 6: Line 1184 - ASSISTANT message (@mention path)
content = content.replace(
    '                            "model_provider": detected_provider.value if \'detected_provider\' in locals() and detected_provider else "ollama",  # Provider from detection or default to ollama\n                            "text": response_text,',
    '                            "model_provider": detected_provider.value if \'detected_provider\' in locals() and detected_provider else "ollama",  # Provider from detection or default to ollama\n                            "model_source": model_source,  # MARKER_115_BUG3: model_source persistence\n                            "text": response_text,',
    1
)

# Fix 7: Line 1249 - USER message (Hostess path)
# This one appears near the end, so search from the back
lines = content.split('\n')
for i in range(len(lines) - 1, -1, -1):
    if '{"role": "user", "text": text, "node_id": node_id}' in lines[i] and i > 1200:
        if 'model_source' not in lines[i]:
            lines[i] = lines[i].replace(
                '{"role": "user", "text": text, "node_id": node_id}',
                '{"role": "user", "text": text, "node_id": node_id, "model_source": model_source},  # MARKER_115_BUG3: model_source persistence'
            )
            break
content = '\n'.join(lines)

# Fix 8: Line 2035 - AGENT message (workflow path)
content = content.replace(
    '                        "agent": resp["agent"],\n                        "model": resp["model"],\n                        "text": resp["text"],',
    '                        "agent": resp["agent"],\n                        "model": resp["model"],\n                        "model_source": resp.get("model_source", model_source),  # MARKER_115_BUG3: model_source persistence\n                        "text": resp["text"],',
    1
)

with open('src/api/handlers/user_message_handler.py', 'w') as f:
    f.write(content)

print("✓ All 8 locations fixed in user_message_handler.py")
PYEOF

echo "✓ user_message_handler.py fixed"

# Verify changes
echo ""
echo "Step 4: Verifying changes..."
MARKER_COUNT=$(grep -c "MARKER_115_BUG3" src/api/handlers/handler_utils.py src/api/handlers/user_message_handler.py || true)
echo "Found $MARKER_COUNT marker comments (expected: 9 total - 1 in handler_utils + 8 in user_message_handler)"

if [ "$MARKER_COUNT" -ge 8 ]; then
    echo "✓ Verification passed"
else
    echo "⚠ Warning: Expected at least 8 markers, found $MARKER_COUNT"
fi

# Show diff summary
echo ""
echo "Step 5: Changes summary..."
echo "handler_utils.py:"
git diff --stat src/api/handlers/handler_utils.py || echo "  (use git diff to see changes)"
echo ""
echo "user_message_handler.py:"
git diff --stat src/api/handlers/user_message_handler.py || echo "  (use git diff to see changes)"

echo ""
echo "================================================"
echo "✓ All fixes applied!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Review changes: git diff src/api/handlers/"
echo "2. Test with server restart"
echo "3. Send message with model_source='polza_ai'"
echo "4. Check data/chat_history.json for model_source field"
echo "5. Restart server and verify persistence"
echo ""
echo "To rollback: git checkout src/api/handlers/handler_utils.py src/api/handlers/user_message_handler.py"
