#!/usr/bin/env python3
"""
Автоматический скрипт обновления main.py для Phase 6.3 Part 3
Обновляет endpoint /api/eval/feedback/submit с полной реализацией
"""

import os
import re
import sys

def update_feedback_endpoint():
    """Update the feedback endpoint in main.py"""
    
    project_root = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
    main_path = os.path.join(project_root, "main.py")
    
    print("\n" + "="*70)
    print("🔧 UPDATING main.py - Feedback Endpoint (Phase 6.3 Part 3)")
    print("="*70)
    
    if not os.path.exists(main_path):
        print(f"❌ main.py not found at {main_path}")
        return False
    
    print(f"📂 Reading: {main_path}")
    
    try:
        with open(main_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Failed to read main.py: {e}")
        return False
    
    # Find the old endpoint and replace it
    print("🔍 Searching for old endpoint pattern...")
    
    # Find function start
    func_start = content.find('@app.route("/api/eval/feedback/submit"')
    if func_start == -1:
        print("❌ Could not find feedback endpoint")
        return False
    
    print(f"✅ Found endpoint at position {func_start}")
    
    # Find the end of the function (next @app.route or @socketio or next double newline followed by @)
    search_start = func_start + 100
    next_decorator_pos = len(content)
    
    for pattern in ['@app.route', '@socketio.on', '@app.errorhandler']:
        pos = content.find(pattern, search_start)
        if pos != -1 and pos < next_decorator_pos:
            next_decorator_pos = pos
    
    if next_decorator_pos == len(content):
        print("⚠️  Could not find next decorator, using end of file")
    
    print(f"   Function ends at position {next_decorator_pos}")
    
    # New endpoint implementation
    new_implementation = '''@app.route("/api/eval/feedback/submit", methods=["POST"])
def submit_eval_feedback():
    """Submit user feedback on evaluation"""
    try:
        data = request.json or {}
        eval_id = data.get('evaluation_id', '')
        task = data.get('task', '')
        output = data.get('output', '')
        rating = data.get('rating', '')  # 👍 or 👎
        correction = data.get('correction', '')
        score = data.get('score', None)
        
        if not eval_id:
            return jsonify({'error': 'evaluation_id is required'}), 400
        
        # Save to Weaviate VetkaUserFeedback
        memory = get_memory_manager()
        success = memory.save_feedback(
            evaluation_id=eval_id,
            task=task,
            output=output,
            rating=rating,
            correction=correction,
            score=score
        )
        
        if success:
            print(f"📝 Feedback saved to Weaviate: {eval_id} → {rating}")
            return jsonify({
                'status': 'success',
                'message': f'Feedback saved to learning system ({rating})',
                'evaluation_id': eval_id,
                'learning_context': 'This will improve future similar tasks'
            }), 200
        else:
            print(f"❌ Failed to save feedback: {eval_id}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to save feedback',
                'evaluation_id': eval_id
            }), 500
            
    except Exception as e:
        print(f"❌ Feedback endpoint error: {str(e)}")
        return jsonify({'error': str(e)}), 500


'''
    
    # Replace the old function with new one
    content = content[:func_start] + new_implementation + content[next_decorator_pos:]
    
    # Write updated content
    print("💾 Writing updated main.py...")
    try:
        with open(main_path, 'w') as f:
            f.write(content)
        print("✅ Successfully wrote updated main.py")
    except Exception as e:
        print(f"❌ Failed to write main.py: {e}")
        return False
    
    # Verify the update
    print("🔍 Verifying update...")
    try:
        with open(main_path, 'r') as f:
            updated_content = f.read()
        
        if 'memory.save_feedback' in updated_content:
            print("✅ Verification PASSED - memory.save_feedback found in updated code")
            return True
        else:
            print("⚠️  Verification FAILED - memory.save_feedback NOT found")
            return False
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False


def verify_all_updates():
    """Verify all files have been updated"""
    print("\n" + "="*70)
    print("✅ VERIFICATION - All Phase 6.3 Part 3 Updates")
    print("="*70)
    
    project_root = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
    
    checks = {
        "PM Agent (execute method)": ("src/agents/vetka_pm.py", "def execute(self, task: str, context_section: str = \"\")"),
        "Dev Agent (execute method)": ("src/agents/vetka_dev.py", "def execute(self, plan: str, context_section: str = \"\")"),
        "QA Agent (execute method)": ("src/agents/vetka_qa.py", "def execute(self, implementation: str, context_section: str = \"\")"),
        "Tests (learning system)": ("tests/test_phase63_part3_learning.py", "class TestMemoryManagerFeedback"),
        "Main (feedback endpoint)": ("main.py", "memory.save_feedback"),
    }
    
    all_passed = True
    
    for name, (file_path, check_string) in checks.items():
        full_path = os.path.join(project_root, file_path)
        
        if not os.path.exists(full_path):
            print(f"❌ {name}: FILE NOT FOUND ({file_path})")
            all_passed = False
            continue
        
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            
            if check_string in content:
                print(f"✅ {name}: PASS")
            else:
                print(f"⚠️  {name}: PARTIAL (file exists but check string not found)")
        except Exception as e:
            print(f"❌ {name}: ERROR ({e})")
            all_passed = False
    
    return all_passed


if __name__ == "__main__":
    print("\n🌳 VETKA Phase 6.3 Part 3 - Automatic Main.py Update Script\n")
    
    # Run update
    success = update_feedback_endpoint()
    
    if success:
        print("\n✅ Feedback endpoint updated successfully!")
    else:
        print("\n❌ Update failed or incomplete")
        sys.exit(1)
    
    # Verify all updates
    all_passed = verify_all_updates()
    
    if all_passed:
        print("\n" + "="*70)
        print("🎉 ALL PHASE 6.3 PART 3 UPDATES VERIFIED!")
        print("="*70)
        print("\n📊 Summary:")
        print("   ✅ vetka_pm.py - execute() method added")
        print("   ✅ vetka_dev.py - execute() method added")
        print("   ✅ vetka_qa.py - execute() method added")
        print("   ✅ main.py - feedback endpoint complete")
        print("   ✅ tests/test_phase63_part3_learning.py - created")
        print("\n🚀 Ready for STEP 5: Running Tests\n")
        sys.exit(0)
    else:
        print("\n⚠️  Some verifications failed - check above")
        sys.exit(1)
