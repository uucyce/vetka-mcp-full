#!/usr/bin/env python3
"""
VETKA Weaviate Collections Initializer.

Creates required Weaviate collections at startup if they don't exist.

@status: active
@phase: 96
@depends: requests
@used_by: components_init.py (manual execution)
"""
import requests, json, time, sys

WEAVIATE_URL = "http://localhost:8080"

COLLECTIONS = {
    'shared': {'name': 'VetkaSharedMemory', 'desc': 'Shared memory across agents'},
    'agents': {'name': 'VetkaAgentsMemory', 'desc': 'Individual agent knowledge'},
    'changelog': {'name': 'VetkaChangeLog', 'desc': 'System change history'},
    'global': {'name': 'VetkaGlobal', 'desc': 'Global knowledge base'},
    'tree': {'name': 'VetkaTree', 'desc': 'Tree level knowledge'},
    'leaf': {'name': 'VetkaLeaf', 'desc': 'Leaf level knowledge'}
}

PROPS = [
    {"name": "content", "dataType": ["text"]},
    {"name": "path", "dataType": ["text"]},
    {"name": "timestamp", "dataType": ["number"]},
    {"name": "creator", "dataType": ["text"]},
    {"name": "node_type", "dataType": ["text"]},
    {"name": "agent_role", "dataType": ["text"]},
    {"name": "metadata", "dataType": ["text"]}
]

def check_weaviate():
    try:
        resp = requests.get(f"{WEAVIATE_URL}/v1/meta", timeout=3)
        return resp.status_code == 200
    except Exception as e:
        print(f"Health check error: {e}")
        return False

def get_schema():
    try:
        resp = requests.get(f"{WEAVIATE_URL}/v1/schema", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("classes", [])
    except Exception as e:
        print(f"Schema fetch error: {e}")
    return []

def collection_exists(name):
    schema = get_schema()
    return any(c.get("class") == name for c in schema)

def create_collection(name, desc):
    if collection_exists(name):
        print(f"✓ {name}")
        return True
    
    schema_obj = {
        "class": name,
        "description": desc,
        "vectorizer": "none",
        "vectorIndexConfig": {"distance": "cosine"},
        "properties": PROPS
    }
    
    try:
        resp = requests.post(f"{WEAVIATE_URL}/v1/schema", json=schema_obj, timeout=10)
        if resp.status_code in [200, 201]:
            print(f"✅ {name}")
            return True
        else:
            print(f"❌ {name} - {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ {name}: {str(e)[:50]}")
        return False

if __name__ == "__main__":
    print("\nVETKA Weaviate Collections Init\n")
    
    if not check_weaviate():
        print("ERROR: Weaviate not responding at", WEAVIATE_URL)
        sys.exit(1)
    
    print("Creating collections...\n")
    count = 0
    for key, cfg in COLLECTIONS.items():
        if create_collection(cfg['name'], cfg['desc']):
            count += 1
        time.sleep(0.05)
    
    print(f"\nDone: {count}/{len(COLLECTIONS)} created")
    sys.exit(0)
