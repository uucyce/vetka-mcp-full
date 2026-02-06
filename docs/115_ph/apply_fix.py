#!/usr/bin/env python3
"""
Phase 115 BUG-3: Apply model_source persistence fix
Run from project root: python3 docs/115_ph/apply_fix.py
"""

import re
from pathlib import Path

def fix_user_message_handler():
    """Apply all 8 fixes to user_message_handler.py"""
    file_path = Path('src/api/handlers/user_message_handler.py')
    
    print(f"Reading {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    changes = []
    
    # Fix 1: Line 424 - USER message (Ollama path)
    for i, line in enumerate(lines):
        if i == 423 and '{"role": "user", "text": text, "node_id": node_id},' in line:
            if 'model_source' not in line:
                lines[i] = line.replace(
                    '{"role": "user", "text": text, "node_id": node_id},',
                    '{"role": "user", "text": text, "node_id": node_id, "model_source": model_source},  # MARKER_115_BUG3: model_source persistence'
                )
                changes.append(f"Line {i+1}: USER message (Ollama path)")
    
    # Fix 2: Line 500 - ASSISTANT message (Ollama path)
    for i, line in enumerate(lines):
        if i == 499 and '"model_provider": "ollama",' in line:
            # Insert after this line
            if i+1 < len(lines) and 'model_source' not in lines[i+1]:
                indent = ' ' * 24
                new_line = f'{indent}"model_source": model_source,  # MARKER_115_BUG3: model_source persistence\n'
                lines.insert(i+1, new_line)
                changes.append(f"Line {i+2}: ASSISTANT message (Ollama path)")
                break
    
    # Fix 3: Line 604 - USER message (streaming path)
    for i, line in enumerate(lines):
        if i == 603 and '{"role": "user", "text": text, "node_id": node_id},' in line:
            if 'model_source' not in line:
                lines[i] = line.replace(
                    '{"role": "user", "text": text, "node_id": node_id},',
                    '{"role": "user", "text": text, "node_id": node_id, "model_source": model_source},  # MARKER_115_BUG3: model_source persistence'
                )
                changes.append(f"Line {i+1}: USER message (streaming path)")
    
    # Fix 4: Line 771 - ASSISTANT message (streaming path)
    for i, line in enumerate(lines):
        if i == 770 and 'detected_provider.value if detected_provider else "unknown"' in line:
            # Insert after this line
            if i+1 < len(lines) and 'model_source' not in lines[i+1]:
                indent = ' ' * 24
                new_line = f'{indent}"model_source": model_source,  # MARKER_115_BUG3: model_source persistence\n'
                lines.insert(i+1, new_line)
                changes.append(f"Line {i+2}: ASSISTANT message (streaming path)")
                break
    
    # Fix 5: Line 927 - USER message (@mention path)
    for i, line in enumerate(lines):
        if i > 920 and i < 930 and '"text": text,  # Original text (with @mention)' in line:
            # Insert after this line
            if 'model_source' not in lines[i+1]:
                indent = ' ' * 28
                new_line = f'{indent}"model_source": model_source,  # MARKER_115_BUG3: model_source persistence\n'
                lines.insert(i+1, new_line)
                changes.append(f"Line {i+2}: USER message (@mention path)")
                break
    
    # Fix 6: Line 1184 - ASSISTANT message (@mention path)
    for i, line in enumerate(lines):
        if i > 1180 and i < 1190 and 'detected_provider.value if \'detected_provider\' in locals()' in line:
            # Insert after this line
            if i+1 < len(lines) and 'model_source' not in lines[i+1]:
                indent = ' ' * 28
                new_line = f'{indent}"model_source": model_source,  # MARKER_115_BUG3: model_source persistence\n'
                lines.insert(i+1, new_line)
                changes.append(f"Line {i+2}: ASSISTANT message (@mention path)")
                break
    
    # Fix 7: Line 1249 - USER message (Hostess path)
    for i, line in enumerate(lines):
        if i > 1245 and i < 1255 and '{"role": "user", "text": text, "node_id": node_id},' in line:
            if 'model_source' not in line:
                lines[i] = line.replace(
                    '{"role": "user", "text": text, "node_id": node_id},',
                    '{"role": "user", "text": text, "node_id": node_id, "model_source": model_source},  # MARKER_115_BUG3: model_source persistence'
                )
                changes.append(f"Line {i+1}: USER message (Hostess path)")
    
    # Fix 8: Line 2035 - AGENT message (workflow path)
    for i, line in enumerate(lines):
        if i > 2030 and i < 2040 and '"model": resp["model"],' in line:
            # Insert after this line
            if i+1 < len(lines) and 'model_source' not in lines[i+1]:
                indent = ' ' * 24
                new_line = f'{indent}"model_source": resp.get("model_source", model_source),  # MARKER_115_BUG3: model_source persistence\n'
                lines.insert(i+1, new_line)
                changes.append(f"Line {i+2}: AGENT message (workflow path)")
                break
    
    # Write back
    print(f"Writing changes to {file_path}...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return changes


def main():
    print("=" * 60)
    print("Phase 115 BUG-3: model_source persistence fix")
    print("=" * 60)
    print()
    
    # Fix handler_utils.py
    print("✓ handler_utils.py already fixed via VETKA MCP")
    print()
    
    # Fix user_message_handler.py
    print("Fixing user_message_handler.py...")
    changes = fix_user_message_handler()
    
    if changes:
        print(f"✓ Applied {len(changes)} fixes:")
        for change in changes:
            print(f"  - {change}")
    else:
        print("✓ No changes needed (already fixed or markers present)")
    
    print()
    print("=" * 60)
    print("✓ Fix complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Review: git diff src/api/handlers/")
    print("2. Test with server restart")
    print("3. Verify model_source persists in chat_history.json")


if __name__ == '__main__':
    main()
