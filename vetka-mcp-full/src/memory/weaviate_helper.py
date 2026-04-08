"""
Weaviate v1 helper - GraphQL search + REST CRUD.

Provides hybrid, vector, and BM25 search via GraphQL plus REST upsert.

@status: active
@phase: 96
@depends: requests, config.config
@used_by: triple_write_manager.py, search handlers
"""
import requests
import json
import uuid as uuid_lib
from typing import Dict, List, Any, Optional
from config.config import WEAVIATE_URL, COLLECTIONS, VECTOR_SIZE

# FIX_99.4: MARKER_ARCH_001 resolved - vetka_weaviate_helper.py deleted (dead code)
# Remaining: weaviate_helper.py (search) + triple_write_manager.py (write) - complementary, not duplicate
class WeaviateHelper:
    def __init__(self):
        self.base_url = WEAVIATE_URL
        self.collections = COLLECTIONS
        self.graphql_url = f"{self.base_url}/v1/graphql"
        self.rest_url = self.base_url
    
    def ensure_collections(self):
        """Create collections if they don't exist"""
        schema = self._get_schema()
        existing = {c.get('class') for c in schema}
        
        for col_key, col_name in self.collections.items():
            if col_name not in existing:
                self._create_collection_rest(col_name, f"VETKA {col_key}")
                print(f"✅ Created {col_name}")
            else:
                print(f"✓ {col_name}")
    
    def _get_schema(self):
        try:
            resp = requests.get(f"{self.rest_url}/v1/schema", timeout=5)
            return resp.json().get("classes", [])
        except:
            return []
    
    def _create_collection_rest(self, col_name, description):
        """Create collection via REST API"""
        schema = {
            "class": col_name,
            "description": description,
            "vectorizer": "none",
            "vectorIndexConfig": {"distance": "cosine"},
            "properties": [
                {"name": "content", "dataType": ["text"]},
                {"name": "path", "dataType": ["text"]},
                {"name": "timestamp", "dataType": ["number"]},
                {"name": "creator", "dataType": ["text"]},
                {"name": "node_type", "dataType": ["text"]},
                {"name": "agent_role", "dataType": ["text"]},
                {"name": "metadata", "dataType": ["text"]}
            ]
        }
        try:
            resp = requests.post(f"{self.rest_url}/v1/schema", json=schema, timeout=10)
            return resp.status_code in [200, 201]
        except:
            return False
    
    def upsert_node(self, collection: str, node_id: Optional[str], content: str,
                   vector: List[float], metadata: Dict = None) -> bool:
        """Upsert node via REST API (node_id is auto-generated if None)"""
        if metadata is None:
            metadata = {}
        
        # Generate UUID if not provided
        if not node_id:
            node_id = str(uuid_lib.uuid4())
        elif not self._is_valid_uuid(node_id):
            # If node_id is not a UUID, convert it
            node_id = str(uuid_lib.uuid5(uuid_lib.NAMESPACE_DNS, node_id))
        
        col_name = self.collections.get(collection, collection)
        
        obj = {
            "class": col_name,
            "id": node_id,
            "properties": {
                "content": content,
                "path": metadata.get("path", ""),
                "timestamp": float(metadata.get("timestamp", 0)),
                "creator": metadata.get("creator", "system"),
                "node_type": metadata.get("node_type", "data"),
                "agent_role": metadata.get("agent_role", ""),
                "metadata": json.dumps(metadata)
            },
            "vector": vector
        }
        
        try:
            resp = requests.post(f"{self.rest_url}/v1/objects", json=obj, timeout=10)
            return resp.status_code in [200, 201]
        except Exception as e:
            print(f"Upsert error: {e}")
            return False
    
    @staticmethod
    def _is_valid_uuid(val):
        try:
            uuid_lib.UUID(str(val))
            return True
        except:
            return False
    
    def hybrid_search(self, collection: str, query: str, vector: List[float],
                     limit: int = 5) -> List[Dict]:
        """Hybrid search using GraphQL (BM25 + nearVector)"""
        col_name = self.collections.get(collection, collection)
        
        # Format vector as JSON string for GraphQL
        vector_str = json.dumps(vector)
        
        graphql_query = f"""
        {{
          Get{{
            {col_name}(
              hybrid: {{
                query: \"{self._escape_quotes(query)}\"
              }}
              limit: {limit}
            ) {{
              _additional {{
                score
              }}
              content
              file_path
              file_name
            }}
          }}
        }}
        """
        
        try:
            resp = requests.post(
                self.graphql_url,
                json={"query": graphql_query},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data:
                    results = data["data"].get("Get", {}).get(col_name, [])
                    return results
                elif "errors" in data:
                    print(f"GraphQL error: {data['errors']}")
        except Exception as e:
            print(f"Search error: {e}")
        
        return []
    
    def vector_search(self, collection: str, vector: List[float],
                     limit: int = 5) -> List[Dict]:
        """Pure vector search using nearVector"""
        col_name = self.collections.get(collection, collection)
        vector_str = json.dumps(vector)
        
        graphql_query = f"""
        {{
          Get{{
            {col_name}(
              nearVector: {{
                vector: {vector_str}
              }}
              limit: {limit}
            ) {{
              _additional {{
                distance
              }}
              content
              file_path
              file_name
            }}
          }}
        }}
        """
        
        try:
            resp = requests.post(
                self.graphql_url,
                json={"query": graphql_query},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data:
                    return data["data"].get("Get", {}).get(col_name, [])
        except:
            pass
        
        return []
    
    def bm25_search(self, collection: str, query: str, limit: int = 5) -> List[Dict]:
        """Pure BM25 text search"""
        col_name = self.collections.get(collection, collection)
        
        graphql_query = f"""
        {{
          Get{{
            {col_name}(
              bm25: {{
                query: \"{self._escape_quotes(query)}\"
              }}
              limit: {limit}
            ) {{
              _additional {{
                score
                id
              }}
              content
              file_path
              file_name
            }}
          }}
        }}
        """
        
        try:
            resp = requests.post(
                self.graphql_url,
                json={"query": graphql_query},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data:
                    # FIX_95.10: Map VetkaLeaf fields to standard format
                    results = data["data"].get("Get", {}).get(col_name, [])
                    for r in results:
                        # Map file_path → path for compatibility with hybrid_search
                        if 'file_path' in r:
                            r['path'] = r['file_path']
                        if 'file_name' in r:
                            r['name'] = r['file_name']
                    return results
                elif "errors" in data:
                    print(f"[BM25] GraphQL error: {data['errors']}")
        except Exception as e:
            print(f"[BM25] Search error: {e}")

        return []

    @staticmethod
    def _escape_quotes(s: str) -> str:
        """Escape user input for GraphQL string literals."""
        if not s:
            return ""

        # Normalize newlines/tabs to spaces first to avoid unterminated GraphQL strings.
        normalized = " ".join(s.replace("\r", " ").replace("\n", " ").replace("\t", " ").split())
        # Escape backslashes before quotes to preserve literal intent.
        return normalized.replace("\\", "\\\\").replace('"', '\\"')

# Global instance
weaviate = WeaviateHelper()
