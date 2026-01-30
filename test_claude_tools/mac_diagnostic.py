#!/usr/bin/env python3
"""
Mac Diagnostic Tool - Created by Claude via Filesystem tools
Tests port connectivity and system status for VETKA
"""
import socket
import subprocess
import sys
from datetime import datetime

def check_port(host, port, service_name):
    """Check if a port is listening"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((host, port))
    sock.close()
    
    if result == 0:
        return f"✅ {port:5d} → {service_name:20s} RUNNING"
    else:
        return f"❌ {port:5d} → {service_name:20s} STOPPED"

def run_command(cmd, description):
    """Run shell command safely"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    print("\n" + "="*70)
    print("🔍 VETKA MAC DIAGNOSTIC REPORT")
    print("="*70)
    print(f"\n⏰ Generated: {datetime.now().isoformat()}\n")
    
    # Port checks
    print("📊 SERVICE PORTS:")
    print("-" * 70)
    ports = {
        5001: "Flask UI",
        8080: "Weaviate",
        11434: "Ollama",
        6333: "Qdrant (alt)",
    }
    
    for port, name in ports.items():
        print(check_port('127.0.0.1', port, name))
    
    # Docker status
    print("\n🐳 DOCKER STATUS:")
    print("-" * 70)
    docker_ps = run_command("docker ps --format 'table {{.Names}}\t{{.Status}}'", "Docker PS")
    if docker_ps:
        print(docker_ps)
    else:
        print("❌ Docker not running or not found")
    
    # Python venv
    print("\n🐍 PYTHON ENVIRONMENT:")
    print("-" * 70)
    python_ver = run_command("python3 --version", "Python version")
    print(f"Python: {python_ver}")
    
    venv_status = run_command("echo $VIRTUAL_ENV", "Venv status")
    if venv_status:
        print(f"Venv: ✅ {venv_status}")
    else:
        print("Venv: ❌ Not activated")
    
    # Project structure
    print("\n📁 PROJECT STATUS:")
    print("-" * 70)
    main_py = run_command("ls -lh /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/main.py 2>/dev/null && echo '✅ Found' || echo '❌ Not found'", "Main file")
    print(f"main.py: {main_py}")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
