  
{  
  “Metadata”: {  
    “Version”: “1.0”,  
    “Created”: “2026-02-02”,  
    “Total\_nodes”: 2169,  
    “Algorithm”: “Sugiyama Layout K with Hierarchical Agglomerative Clustering”,  
    “Sources”: \[  
      “17.6\_Knowledge Mode=Directory Mode”,  
      “MGC Hierarchical Memory Integration”,  
      “Refactoring after 22 phase”,  
      “VETKA Architecture Components”  
    \]  
  },  
    
  “Global\_config”: {  
    “ROOT\_TAG”: “VETKA\_Documentation”,  
    “TAG\_BASE\_Y”: 0,  
    “LAYER\_HEIGHT”: 100,  
    “SIBLING\_SPREAD”: 200,  
    “BASE\_SPREAD”: 150,  
    “CHAIN\_STEP\_Y”: 30  
  },  
    
  “Node\_types”: {  
    “File”: “source code files (.py, .js, .ts, etc.)”,  
    “Tag”: “semantic category or namespace”,  
    “Concept”: “abstract idea or design pattern”,  
    “Artifact”: “documentation, diagram, or output”  
  },  
    
  “Tag\_hierarchy”: {  
    “Description”: “Hierarchical organization of semantic tags”,  
    “Root”: {  
      “Id”: “root\_vetka”,  
      “Name”: “VETKA\_Documentation”,  
      “Depth”: 0,  
      “Parent\_id”: null,  
      “X”: 0,  
      “Y”: 0,  
      “Children”: \[  
        {  
          “Id”: “tag\_architecture”,  
          “Name”: “Architecture”,  
          “Depth”: 1,  
          “Parent\_id”: “root\_vetka”,  
          “Estimated\_node\_count”: 428,  
          “Semantic\_key”: “system-design, components, patterns”,  
          “Children”: \[  
            {  
              “Id”: “tag\_backend”,  
              “Name”: “Backend”,  
              “Depth”: 2,  
              “Parent\_id”: “tag\_architecture”,  
              “Estimated\_node\_count”: 312,  
              “Semantic\_key”: “python, async, database, api”  
            },  
            {  
              “Id”: “tag\_frontend”,  
              “Name”: “Frontend”,  
              “Depth”: 2,  
              “Parent\_id”: “tag\_architecture”,  
              “Estimated\_node\_count”: 116,  
              “Semantic\_key”: “javascript, react, ui, typescript”  
            }  
          \]  
        },  
        {  
          “Id”: “tag\_utils”,  
          “Name”: “Utils”,  
          “Depth”: 1,  
          “Parent\_id”: “root\_vetka”,  
          “Estimated\_node\_count”: 402,  
          “Semantic\_key”: “helpers, tools, infrastructure”  
        },  
        {  
          “Id”: “tag\_concepts”,  
          “Name”: “Concepts”,  
          “Depth”: 1,  
          “Parent\_id”: “root\_vetka”,  
          “Estimated\_node\_count”: 402,  
          “Semantic\_key”: “ideas, patterns, theory”  
        }  
      \]  
    }  
  },  
    
  “Node\_example”: {  
    “Description”: “Example node structure with all metadata”,  
    “Id”: “file\_agents\_py\_1”,  
    “Type”: “file”,  
    “Name”: “[agents.py](http://agents.py)”,  
    “Source\_doc”: “17.6\_Knowledge Mode=Directory Mode”,  
      
    “Knowledge\_metadata”: {  
      “Knowledge\_level”: 0.75,  
      “Time\_to\_understand\_minutes”: 45,  
      “Complexity\_score”: 0.65,  
      “Importance\_score”: 0.85,  
      “Depth\_in\_hierarchy”: 3  
    },  
      
    “Hierarchy\_position”: {  
      “Tag\_id”: “tag\_backend”,  
      “Tag\_path”: \[“root\_vetka”, “tag\_architecture”, “tag\_backend”\],  
      “Layer”: 3,  
      “Position\_in\_tag”: 5  
    },  
      
    “Inputs”: {  
      “Depends\_on\_files”: \[  
        {“name”: “[handlers.py](http://handlers.py)”, “type”: “function\_def”, “count”: 5},  
        {“name”: “[memory.py](http://memory.py)”, “type”: “class\_def”, “count”: 2}  
      \],  
      “Depends\_on\_concepts”: \[  
        “Async-dispatch”,  
        “State-machine”,  
        “Message-router”  
      \],  
      “Requires\_knowledge”: \[  
        “Python 3.10+”,  
        “Asyncio”,  
        “SQLAlchemy ORM”  
      \],  
      “Input\_matrix”: {  
        “Total\_dependencies”: 7,  
        “By\_type”: {  
          “Files”: 2,  
          “Concepts”: 3,  
          “Knowledge\_prereqs”: 3  
        }  
      }  
    },  
      
    “Outputs”: {  
      “Provides\_to\_files”: \[  
        {“name”: “[orchestrator.py](http://orchestrator.py)”, “exports”: \[“Agent”, “TaskQueue”\]},  
        {“name”: “[service.py](http://service.py)”, “exports”: \[“AgentManager”\]}  
      \],  
      “Provides\_concepts”: \[  
        “Async-agent”,  
        “Message-dispatcher”,  
        “Task-queue”  
      \],  
      “Output\_matrix”: {  
        “Total\_exports”: 3,  
        “By\_type”: {  
          “Files”: 2,  
          “Concepts”: 3  
        }  
      }  
    },  
      
    “Semantic\_attributes”: {  
      “Tags”: \[“backend”, “async”, “state-machine”, “core-logic”\],  
      “Category”: “core-logic”,  
      “Related\_concepts”: \[  
        “Agents”,  
        “Dispatch”,  
        “Communication”,  
        “Task-management”  
      \],  
      “Embedding\_vector”: null  
    },  
      
    “Visualization”: {  
      “Layer”: 3,  
      “X”: 450,  
      “Y”: 300,  
      “Color”: “\#4CAF50”,  
      “Size”: 1.5,  
      “Icon”: “file-code”  
    }  
  },  
    
  “Edge\_types”: {  
    “Dependency”: “Node A depends on Node B for functionality”,  
    “Concept\_link”: “Semantic connection between concepts”,  
    “Hierarchy”: “Parent-child relationship in tag tree”,  
    “Knowledge\_prerequisite”: “Node A requires understanding of Node B”  
  },  
    
  “Edge\_example”: {  
    “Id”: “edge\_agents\_handlers\_1”,  
    “From\_node\_id”: “file\_agents\_py\_1”,  
    “To\_node\_id”: “file\_handlers\_py\_1”,  
    “Type”: “dependency”,  
    “Strength”: 0.9,  
    “Description”: “[agents.py](http://agents.py) imports handlers from [handlers.py](http://handlers.py)”,  
    “Source\_doc”: “Code analysis from VETKA\_MCP tools”  
  },  
    
  “Visualization\_layers”: {  
    “Layer\_1\_overview”: {  
      “Description”: “High-level view of main categories”,  
      “Nodes\_count”: 5,  
      “Nodes”: \[  
        {“id”: “tag\_architecture”, “count”: 428},  
        {“id”: “tag\_utils”, “count”: 402},  
        {“id”: “tag\_concepts”, “count”: 402},  
        {“id”: “tag\_infrastructure”, “count”: 312},  
        {“id”: “tag\_other”, “count”: 625}  
      \],  
      “Metrics”: {  
        “Most\_populated”: “Backend (612 nodes) ⚠️ NEEDS REFACTORING”,  
        “Least\_populated”: “Concepts (402 nodes)”,  
        “Avg\_nodes\_per\_category”: 433.8  
      }  
    },  
      
    “Layer\_2\_detailed”: {  
      “Description”: “Full DAG with all 2169 nodes and dependencies”,  
      “Rendering\_hints”: {  
        “Color\_by”: “knowledge\_level”,  
        “Size\_by”: “importance\_score”,  
        “Group\_by”: “tag\_hierarchy”,  
        “Edge\_filter”: “show dependencies with strength \> 0.5”  
      }  
    }  
  },  
    
  “Mgc\_cache\_strategy”: {  
    “Generation\_0”: {  
      “Scope”: “Hot nodes (frequently updated)”,  
      “Storage”: “RAM / In-memory cache”,  
      “Ttl\_hours”: 1,  
      “Refresh\_policy”: “on-write”  
    },  
    “Generation\_1”: {  
      “Scope”: “Warm nodes (periodic updates)”,  
      “Storage”: “Redis / Intermediate cache”,  
      “Ttl\_hours”: 24,  
      “Refresh\_policy”: “on-schedule”  
    },  
    “Generation\_2”: {  
      “Scope”: “Cold nodes (archived, rarely accessed)”,  
      “Storage”: “PostgreSQL / Disk / JSON”,  
      “Ttl\_hours”: null,  
      “Refresh\_policy”: “manual”  
    }  
  },  
    
  “Cam\_replication”: {  
    “Primary\_wal”: {  
      “Type”: “Write-Ahead Logs”,  
      “Purpose”: “Ensure consistency across generations”,  
      “Technology”: “PostgreSQL WAL \+ Logical Replication”  
    },  
    “Intermediate\_vector\_db”: {  
      “Type”: “Semantic edge storage”,  
      “Purpose”: “Fast semantic search and concept linking”,  
      “Technology”: “Gdrant vector database”  
    },  
    “Read\_replicas”: {  
      “Count”: 3,  
      “Purpose”: “Scale read queries for analysis”,  
      “Distribution”: “geographic or by workload type”  
    }  
  },  
    
  “Implementation\_roadmap”: {  
    “Phase\_1”: {  
      “Duration\_weeks”: “0-1”,  
      “Name”: “Information Audit”,  
      “Tasks”: \[  
        “Parse all 2169 nodes from source”,  
        “Classify by type: file, tag, concept, artifact”,  
        “Calculate knowledge\_level and time\_to\_understand”  
      \]  
    },  
    “Phase\_2”: {  
      “Duration\_weeks”: “1-3”,  
      “Name”: “Build Hierarchy”,  
      “Tasks”: \[  
        “Apply Hierarchical Agglomerative Clustering to tags”,  
        “Create ROOT\_TAG structure”,  
        “Compute layer (depth) for each node”  
      \]  
    },  
    “Phase\_3”: {  
      “Duration\_weeks”: “3-6”,  
      “Name”: “Apply Sugiyama Layout”,  
      “Tasks”: \[  
        “Implement Y-coordinate formula (layer-based)”,  
        “Implement X-coordinate formula (angular spread)”,  
        “Implement adaptive\_spread (similarity-based)”  
      \]  
    },  
    “Phase\_4”: {  
      “Duration\_weeks”: “6-10”,  
      “Name”: “Integrate MGC/CAM”,  
      “Tasks”: \[  
        “Configure caching by generation (0, 1, 2)”,  
        “Setup WAL replication”,  
        “Integrate Gdrant for semantic search”  
      \]  
    },  
    “Phase\_5”: {  
      “Duration\_weeks”: “10+”,  
      “Name”: “Visualization & Analysis”,  
      “Tasks”: \[  
        “Implement Layer 1 (overview)”,  
        “Implement Layer 2 (detailed DAG)”,  
        “Add interactive filters and drill-down”  
      \]  
    }  
  },  
    
  “Formulas”: {  
    “Y\_coordinate\_tag”: “y \= TAG\_BASE\_Y \+ depth \* LAYER\_HEIGHT”,  
    “Y\_coordinate\_file”: “y \= parent\_tag\_y \+ CHAIN\_STEP\_Y \* position\_in\_chain”,  
    “X\_coordinate\_sibling”: “x\_normalized \= (index / (count \- 1)) \- 0.5”,  
    “X\_coordinate\_spread”: “x \= parent\_x \+ normalized \* SIBLING\_SPREAD”,  
    “Adaptive\_spread\_factor”: “spread \= BASE\_SPREAD \* adaptive\_factor(similarity)”,  
    “Knowledge\_level”: “kl \= 0.5\*len(inputs) \+ 0.3\*time\_depth \+ 0.2\*semantic\_sim”  
  }  
}  
