#!/usr/bin/env python3
"""
Phase 60.3: Socket.IO Workflow Events Test
Tests real-time event streaming from LangGraph workflow

@file test_socket_events.py
@status ACTIVE
@phase Phase 60.3 - Feature Flag Enable + Integration Testing
"""

import socketio
import time
import sys
import argparse

# Track events
events_received = []
connection_established = False

sio = socketio.Client()


@sio.on('connect', namespace='/workflow')
def on_connect():
    global connection_established
    connection_established = True
    print('✅ Connected to /workflow namespace')
    sio.emit('join_workflow', {'workflow_id': 'test-monitor'}, namespace='/workflow')


@sio.on('connect', namespace='/')
def on_connect_main():
    print('✅ Connected to main namespace')


@sio.on('joined_workflow', namespace='/workflow')
def on_joined(data):
    print(f'✅ Joined workflow: {data}')


@sio.on('node_started', namespace='/workflow')
def on_node_started(data):
    events_received.append(('node_started', data))
    print(f'📍 Node started: {data.get("node")}')


@sio.on('node_completed', namespace='/workflow')
def on_node_completed(data):
    events_received.append(('node_completed', data))
    duration = data.get('duration_ms', 0)
    print(f'✅ Node completed: {data.get("node")} ({duration}ms)')


@sio.on('score_computed', namespace='/workflow')
def on_score(data):
    events_received.append(('score_computed', data))
    passed = "PASS" if data.get('passed') else "FAIL"
    score = data.get('score', 0)
    print(f'📊 Score: {score:.2f} ({passed})')


@sio.on('retry_decision', namespace='/workflow')
def on_retry(data):
    events_received.append(('retry_decision', data))
    will_retry = "YES" if data.get('will_retry') else "NO"
    print(f'🔄 Retry: {will_retry} ({data.get("retry_count")}/{data.get("max_retries")})')


@sio.on('learner_suggestion', namespace='/workflow')
def on_learner(data):
    events_received.append(('learner_suggestion', data))
    category = data.get('failure_category', 'unknown')
    print(f'🧠 Learner: category={category}')


@sio.on('workflow_started', namespace='/workflow')
def on_workflow_started(data):
    events_received.append(('workflow_started', data))
    print(f'🚀 Workflow started: {data.get("workflow_id")}')


@sio.on('workflow_completed', namespace='/workflow')
def on_complete(data):
    events_received.append(('workflow_completed', data))
    print(f'🎉 Workflow completed! Score: {data.get("final_score")}')
    print(f'\n📊 Total events received: {len(events_received)}')


@sio.on('langgraph_progress', namespace='/')
def on_langgraph_progress(data):
    """Legacy event from main namespace"""
    events_received.append(('langgraph_progress', data))
    node = data.get('node', 'unknown')
    state = data.get('state', {})
    print(f'📍 Progress: {node} (agent: {state.get("current_agent", "N/A")})')


@sio.on('disconnect', namespace='/workflow')
def on_disconnect():
    print('❌ Disconnected from /workflow')


@sio.on('disconnect', namespace='/')
def on_disconnect_main():
    print('❌ Disconnected from main')


@sio.on('*', namespace='/workflow')
def catch_all(event, data):
    """Catch any unknown events"""
    if event not in ['connect', 'disconnect', 'joined_workflow']:
        events_received.append((event, data))
        print(f'📨 Event: {event} - {str(data)[:100]}...')


def main():
    parser = argparse.ArgumentParser(description='Test Socket.IO workflow events')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', default=5001, type=int, help='Server port')
    parser.add_argument('--timeout', default=60, type=int, help='Max wait time in seconds')
    args = parser.parse_args()

    url = f'http://{args.host}:{args.port}'

    print("\n" + "="*60)
    print("🔌 Phase 60.3: Socket.IO Events Test")
    print("="*60)
    print(f"Server: {url}")
    print(f"Timeout: {args.timeout}s")
    print("="*60 + "\n")

    print('🔌 Connecting to Socket.IO...')
    try:
        # Try connecting to both namespaces
        sio.connect(url, namespaces=['/', '/workflow'], wait_timeout=10)
        print('✅ Connection established\n')

        print('🎧 Listening for events...')
        print('   (Start a workflow in another terminal or browser)')
        print('   (Press Ctrl+C to stop)\n')
        print("-" * 40)

        # Wait for events
        start_time = time.time()
        while time.time() - start_time < args.timeout:
            sio.sleep(1)

            # Check for workflow completion
            if any(e[0] == 'workflow_completed' for e in events_received):
                print("\n✅ Workflow completed, exiting...")
                break

        print("-" * 40)

    except KeyboardInterrupt:
        print('\n\n⏹️ Stopped by user')
    except Exception as e:
        print(f'❌ Connection failed: {e}')
        return 1
    finally:
        print(f'\n📊 Total events received: {len(events_received)}')

        if events_received:
            print("\nEvent Summary:")
            event_types = {}
            for event_type, _ in events_received:
                event_types[event_type] = event_types.get(event_type, 0) + 1

            for event_type, count in sorted(event_types.items()):
                print(f"  {event_type}: {count}")

        sio.disconnect()

    # Return success if we got events
    if events_received:
        print("\n✅ Socket.IO events test PASSED!")
        return 0
    else:
        print("\n⚠️ No events received (is a workflow running?)")
        return 1


if __name__ == '__main__':
    sys.exit(main())
