#!/bin/bash
# Phase 88: Test script for mention matching fix

set -e

echo "=== Phase 88 Mention Matching Test ==="
echo

# Step 1: Find test group
echo "Step 1: Finding test group..."
GROUP_DATA=$(curl -s http://localhost:5001/api/groups | jq '.groups[] | select(.name | contains("отладка"))')
GROUP_ID=$(echo "$GROUP_DATA" | jq -r '.id')
GROUP_NAME=$(echo "$GROUP_DATA" | jq -r '.name')

if [ -z "$GROUP_ID" ] || [ "$GROUP_ID" == "null" ]; then
    echo "❌ Test group not found!"
    exit 1
fi

echo "✅ Found group: $GROUP_NAME"
echo "   ID: $GROUP_ID"
echo

# Step 2: Show participants
echo "Step 2: Group participants:"
echo "$GROUP_DATA" | jq '.participants | to_entries[] | {agent_id: .value.agent_id, display_name: .value.display_name, role: .value.role}'
echo

# Step 3: Send test message
echo "Step 3: Sending test message with mentions..."
RESPONSE=$(curl -s -X POST "http://localhost:5001/api/groups/$GROUP_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "@PM",
    "content": "Phase 88 Test: @Researcher please analyze. @Dev verify the logic.",
    "message_type": "chat"
  }')

MESSAGE_ID=$(echo "$RESPONSE" | jq -r '.message.id')
MENTIONS=$(echo "$RESPONSE" | jq -r '.message.mentions[]' | tr '\n' ', ' | sed 's/,$//')

if [ -z "$MESSAGE_ID" ] || [ "$MESSAGE_ID" == "null" ]; then
    echo "❌ Failed to send message!"
    echo "$RESPONSE" | jq .
    exit 1
fi

echo "✅ Message sent successfully"
echo "   ID: $MESSAGE_ID"
echo "   Detected mentions: $MENTIONS"
echo

# Step 4: Wait for responses
echo "Step 4: Waiting 3 seconds for agent responses..."
sleep 3
echo

# Step 5: Check for responses
echo "Step 5: Checking recent messages..."
MESSAGES=$(curl -s "http://localhost:5001/api/groups/$GROUP_ID/messages?limit=10")
echo "$MESSAGES" | jq '.messages[] | {sender: .sender_id, preview: .content[:80], time: .created_at}'
echo

# Count responses after our test message
RESPONSE_COUNT=$(echo "$MESSAGES" | jq "[.messages[] | select(.created_at > \"$(echo "$RESPONSE" | jq -r '.message.created_at')\") and .sender_id != \"@PM\"] | length")

echo "=== Test Summary ==="
echo "Messages after test: $RESPONSE_COUNT"
echo
if [ "$RESPONSE_COUNT" -gt 0 ]; then
    echo "✅ SUCCESS: Agents responded to mentions!"
else
    echo "⚠️  WARNING: No agent responses detected yet"
    echo "   (Check server logs for GROUP_DEBUG output)"
fi
echo

echo "=== Expected in Logs ==="
echo "[GROUP_DEBUG] Agent PM (Gpt 5.1) mentioned: ['Researcher', 'Dev']"
echo "[GROUP_DEBUG] Added Researcher to responders from agent @mention"
echo "[GROUP_DEBUG] Added Dev to responders from agent @mention"
echo

echo "To monitor logs in real-time, run:"
echo "  tail -f <server_log_file> | grep GROUP_DEBUG"
