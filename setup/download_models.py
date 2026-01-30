#!/usr/bin/env python3
"""
VETKA Phase 8.0 - Automatic Ollama Model Downloader
Downloads all required models for VETKA system
"""

import subprocess
import sys
import time
from typing import List, Tuple, Optional


def check_ollama_running() -> bool:
    """Check if Ollama service is running"""
    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=3)
        return response.status_code == 200
    except Exception:
        return False


def get_installed_models() -> List[str]:
    """Get list of installed models"""
    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            return [m['name'] for m in response.json().get('models', [])]
    except Exception:
        pass
    return []


def pull_model(model_name: str) -> bool:
    """Pull a model from Ollama"""
    try:
        print(f"    Pulling {model_name}...")
        result = subprocess.run(
            ['ollama', 'pull', model_name],
            capture_output=False,
            timeout=1800  # 30 minutes timeout
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"    [!] Timeout pulling {model_name}")
        return False
    except Exception as e:
        print(f"    [X] Error: {e}")
        return False


def main():
    """Main model download routine"""

    print("=" * 70)
    print("  VETKA PHASE 8.0 - OLLAMA MODEL DOWNLOADER")
    print("=" * 70)

    # Required models (name, description, size estimate)
    required_models = [
        ('deepseek-llm:7b', 'Main reasoning model', '4GB'),
        ('qwen2:7b', 'Fast fallback model', '4GB'),
        ('embeddinggemma:300m', 'Embedding model (Gemma)', '600MB'),
        ('llama3.1:8b', 'HOPE pattern / vision fallback', '5GB'),
    ]

    # Optional models
    optional_models = [
        ('deepseek-coder:6.7b', 'Code specialist (alt)', '4GB'),
        ('nomic-embed-text', 'Alternative embedding model', '300MB'),
        ('mistral:7b', 'General assistant model', '4GB'),
    ]

    # Check Ollama
    print("\n[1/3] Checking Ollama service...")
    if not check_ollama_running():
        print("  [X] Ollama is not running!")
        print("")
        print("  Please start Ollama first:")
        print("    ollama serve")
        print("")
        print("  Or install Ollama from: https://ollama.ai")
        sys.exit(1)
    print("  [+] Ollama is running")

    # Get installed models
    print("\n[2/3] Checking installed models...")
    installed = get_installed_models()
    print(f"  Found {len(installed)} installed models")

    # Download required models
    print("\n[3/3] Downloading models...")
    print("-" * 40)

    print("\n  REQUIRED MODELS:")
    for model_name, description, size in required_models:
        # Check if already installed (base name match)
        base_name = model_name.split(':')[0]
        is_installed = any(base_name in m for m in installed)

        if is_installed:
            print(f"  [+] {model_name:25} - Already installed")
        else:
            print(f"  [ ] {model_name:25} - {description} (~{size})")
            print(f"      Downloading... (this may take several minutes)")

            success = pull_model(model_name)

            if success:
                print(f"  [+] {model_name:25} - Downloaded!")
            else:
                print(f"  [X] {model_name:25} - FAILED")
                print(f"      Try manually: ollama pull {model_name}")

    print("\n  OPTIONAL MODELS (skip if not needed):")
    for model_name, description, size in optional_models:
        base_name = model_name.split(':')[0]
        is_installed = any(base_name in m for m in installed)

        if is_installed:
            print(f"  [+] {model_name:25} - Already installed")
        else:
            print(f"  [ ] {model_name:25} - {description} (~{size})")
            print(f"      To install: ollama pull {model_name}")

    # Final check
    print("\n" + "=" * 70)
    print("  DOWNLOAD COMPLETE")
    print("=" * 70)

    # Refresh installed list
    installed = get_installed_models()

    required_base_names = [m[0].split(':')[0] for m in required_models]
    installed_required = sum(1 for base in required_base_names
                           if any(base in m for m in installed))

    print(f"\n  Required models: {installed_required}/{len(required_models)} installed")

    if installed_required == len(required_models):
        print("  [+] All required models ready!")
        print("\n  You can now run VETKA:")
        print("    python main.py")
    else:
        print("  [!] Some models missing - system may work in degraded mode")
        print("\n  To install missing models manually:")
        for model_name, _, _ in required_models:
            base_name = model_name.split(':')[0]
            if not any(base_name in m for m in installed):
                print(f"    ollama pull {model_name}")


if __name__ == '__main__':
    main()
