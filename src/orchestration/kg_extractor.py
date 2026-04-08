"""
VETKA Knowledge Graph Extractor.

Phase 17: Extract semantic knowledge graphs from file systems.

Extracts prerequisite relationships and knowledge levels from:
- Code files (using AST analysis)
- Documentation (using LLM extraction)
- Embeddings (using similarity inference)

Based on:
- Grok Topic 2 (semantic vs structural)
- CodeGraph methodology
- Doc2Graph approach

@status: active
@phase: 96
@depends: ast, networkx, ollama
@used_by: src.orchestration.cam_engine
"""

import logging
import ast
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
from collections import defaultdict
import networkx as nx

# Optional imports
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

logger = logging.getLogger("VETKA_KG")


@dataclass
class Concept:
    """Represents a concept in the knowledge graph."""
    id: str
    name: str
    file_path: str
    concept_type: str  # 'class', 'function', 'topic', 'module'
    description: str = ""
    knowledge_level: float = 0.5
    prerequisites: List[str] = None
    dependents: List[str] = None

    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []
        if self.dependents is None:
            self.dependents = []


@dataclass
class KnowledgeEdge:
    """Represents a prerequisite relationship."""
    source: str  # prerequisite (must know first)
    target: str  # dependent (requires source)
    edge_type: str  # 'imports', 'calls', 'inherits', 'prerequisite', 'related'
    confidence: float = 1.0


class KGExtractor:
    """
    Extract Knowledge Graph from file system + embeddings.

    Pipeline:
    1. Scan all files + extract concepts
    2. Extract code dependencies (AST-based)
    3. Extract document relations (LLM-based)
    4. Build prerequisite graph (DAG)
    5. Compute knowledge levels
    6. Return semantic graph
    """

    def __init__(self, llm_model: str = "gemma2:9b"):
        """
        Initialize KG extractor.

        Args:
            llm_model: LLM model for document extraction
        """
        self.llm_model = llm_model
        self.concepts: Dict[str, Concept] = {}
        self.edges: List[KnowledgeEdge] = []
        self.graph: Optional[nx.DiGraph] = None

        logger.info(f"KG Extractor initialized (LLM: {llm_model})")

    async def extract_knowledge_graph(self, vetka_tree: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main extraction pipeline.

        Args:
            vetka_tree: VETKA tree from CAM engine (dict of node_id -> node)

        Returns:
            Dictionary with:
                - concepts: List of Concept objects
                - edges: List of KnowledgeEdge objects
                - levels: Dict of concept_id -> knowledge_level
                - graph: NetworkX DiGraph
        """
        logger.info(f"Extracting knowledge graph from {len(vetka_tree)} nodes")

        # Step 1: Extract concepts from all files
        for node_id, node in vetka_tree.items():
            file_path = node.get('path') if isinstance(node, dict) else node.path

            if file_path and os.path.exists(file_path):
                await self._extract_concepts_from_file(file_path)

        logger.info(f"Extracted {len(self.concepts)} concepts")

        # Step 2: Extract code dependencies
        code_edges = await self._extract_all_code_dependencies(vetka_tree)
        self.edges.extend(code_edges)
        logger.info(f"Extracted {len(code_edges)} code dependency edges")

        # Step 3: Extract document relations
        doc_edges = await self._extract_all_doc_relations(vetka_tree)
        self.edges.extend(doc_edges)
        logger.info(f"Extracted {len(doc_edges)} document relation edges")

        # Step 4: Build DAG
        self.graph = self._build_dag()
        logger.info(f"Built DAG with {self.graph.number_of_nodes()} nodes, "
                   f"{self.graph.number_of_edges()} edges")

        # Step 5: Compute knowledge levels
        levels = self._compute_all_knowledge_levels()
        logger.info(f"Computed knowledge levels for {len(levels)} concepts")

        return {
            'concepts': list(self.concepts.values()),
            'edges': self.edges,
            'levels': levels,
            'graph': self.graph,
            'stats': {
                'num_concepts': len(self.concepts),
                'num_edges': len(self.edges),
                'avg_level': sum(levels.values()) / len(levels) if levels else 0
            }
        }

    async def _extract_concepts_from_file(self, file_path: str):
        """
        Extract concepts from a single file.

        For code: extracts classes, functions, modules
        For docs: extracts topics/sections

        Args:
            file_path: Path to file
        """
        suffix = Path(file_path).suffix.lower()

        if suffix == '.py':
            await self._extract_python_concepts(file_path)
        elif suffix in ['.md', '.txt']:
            await self._extract_doc_concepts(file_path)
        # Add more file types as needed

    async def _extract_python_concepts(self, file_path: str):
        """Extract Python classes, functions, modules as concepts."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)
            module_name = Path(file_path).stem

            # Module-level concept
            module_id = f"module:{module_name}"
            self.concepts[module_id] = Concept(
                id=module_id,
                name=module_name,
                file_path=file_path,
                concept_type='module',
                description=f"Python module: {module_name}"
            )

            # Extract classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_id = f"class:{module_name}.{node.name}"
                    self.concepts[class_id] = Concept(
                        id=class_id,
                        name=node.name,
                        file_path=file_path,
                        concept_type='class',
                        description=ast.get_docstring(node) or f"Class {node.name}"
                    )

                elif isinstance(node, ast.FunctionDef):
                    func_id = f"function:{module_name}.{node.name}"
                    self.concepts[func_id] = Concept(
                        id=func_id,
                        name=node.name,
                        file_path=file_path,
                        concept_type='function',
                        description=ast.get_docstring(node) or f"Function {node.name}"
                    )

        except Exception as e:
            logger.debug(f"Failed to parse {file_path}: {e}")

    async def _extract_doc_concepts(self, file_path: str):
        """Extract topics from markdown/text documents."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract markdown headers as concepts
            import re
            headers = re.findall(r'^#{1,3}\s+(.+)$', content, re.MULTILINE)

            doc_name = Path(file_path).stem

            for idx, header in enumerate(headers):
                topic_id = f"topic:{doc_name}.{header.lower().replace(' ', '_')}"
                self.concepts[topic_id] = Concept(
                    id=topic_id,
                    name=header,
                    file_path=file_path,
                    concept_type='topic',
                    description=f"Topic: {header}"
                )

        except Exception as e:
            logger.debug(f"Failed to extract concepts from {file_path}: {e}")

    async def _extract_all_code_dependencies(
        self,
        vetka_tree: Dict[str, Any]
    ) -> List[KnowledgeEdge]:
        """
        Extract code dependencies from all code files.

        Returns:
            List of KnowledgeEdge objects
        """
        edges = []

        for node_id, node in vetka_tree.items():
            file_path = node.get('path') if isinstance(node, dict) else getattr(node, 'path', None)

            if file_path and file_path.endswith('.py'):
                file_edges = await self._extract_code_dependencies(file_path)
                edges.extend(file_edges)

        return edges

    async def _extract_code_dependencies(self, file_path: str) -> List[KnowledgeEdge]:
        """
        Extract dependencies from Python code using AST.

        Extracts:
        - Import statements → dependency edges
        - Function calls → dependency edges
        - Class inheritance → dependency edges

        Args:
            file_path: Path to Python file

        Returns:
            List of KnowledgeEdge objects
        """
        edges = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)
            module_name = Path(file_path).stem

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        source_id = f"module:{alias.name}"
                        target_id = f"module:{module_name}"

                        edges.append(KnowledgeEdge(
                            source=source_id,
                            target=target_id,
                            edge_type='imports',
                            confidence=1.0
                        ))

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            source_id = f"module:{node.module}"
                            target_id = f"module:{module_name}"

                            edges.append(KnowledgeEdge(
                                source=source_id,
                                target=target_id,
                                edge_type='imports',
                                confidence=1.0
                            ))

                elif isinstance(node, ast.ClassDef):
                    # Class inheritance
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            source_id = f"class:{module_name}.{base.id}"
                            target_id = f"class:{module_name}.{node.name}"

                            edges.append(KnowledgeEdge(
                                source=source_id,
                                target=target_id,
                                edge_type='inherits',
                                confidence=1.0
                            ))

        except Exception as e:
            logger.debug(f"Failed to extract dependencies from {file_path}: {e}")

        return edges

    async def _extract_all_doc_relations(
        self,
        vetka_tree: Dict[str, Any]
    ) -> List[KnowledgeEdge]:
        """
        Extract document relations from all documentation files.

        Returns:
            List of KnowledgeEdge objects
        """
        edges = []

        for node_id, node in vetka_tree.items():
            file_path = node.get('path') if isinstance(node, dict) else getattr(node, 'path', None)

            if file_path and file_path.endswith(('.md', '.txt')):
                file_edges = await self._extract_doc_relations(file_path)
                edges.extend(file_edges)

        return edges

    async def _extract_doc_relations(self, file_path: str) -> List[KnowledgeEdge]:
        """
        Extract concept relations from documentation using LLM.

        Uses Ollama to identify prerequisites and relationships.

        Args:
            file_path: Path to document

        Returns:
            List of KnowledgeEdge objects
        """
        if not HAS_OLLAMA:
            logger.debug("Ollama not available - skipping doc relation extraction")
            return []

        edges = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Truncate to avoid token limits
            content = content[:3000]

            # LLM extraction prompt
            extraction_prompt = f"""Analyze this document and extract concept relationships.

Return ONLY a valid JSON object with this structure:
{{
    "concepts": ["concept1", "concept2", ...],
    "prerequisites": [
        {{"concept": "concept_name", "requires": ["prereq1", "prereq2"]}}
    ]
}}

Document:
{content}

JSON:"""

            try:
                result = ollama.generate(
                    model=self.llm_model,
                    prompt=extraction_prompt
                )

                response_text = result.get('response', '{}')

                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    extracted = json.loads(json_match.group(0))
                else:
                    extracted = {}

                doc_name = Path(file_path).stem

                # Build edges from prerequisites
                for prereq_info in extracted.get('prerequisites', []):
                    concept = prereq_info.get('concept', '')
                    requires = prereq_info.get('requires', [])

                    target_id = f"topic:{doc_name}.{concept.lower().replace(' ', '_')}"

                    for required in requires:
                        source_id = f"topic:{doc_name}.{required.lower().replace(' ', '_')}"

                        edges.append(KnowledgeEdge(
                            source=source_id,
                            target=target_id,
                            edge_type='prerequisite',
                            confidence=0.7  # LLM-based, lower confidence
                        ))

            except Exception as e:
                logger.debug(f"LLM extraction failed for {file_path}: {e}")

        except Exception as e:
            logger.debug(f"Failed to read {file_path}: {e}")

        return edges

    def _build_dag(self) -> nx.DiGraph:
        """
        Build directed acyclic graph from concepts and edges.

        Ensures no cycles using topological sort.

        Returns:
            NetworkX DiGraph
        """
        G = nx.DiGraph()

        # Add all concepts as nodes
        for concept_id, concept in self.concepts.items():
            G.add_node(concept_id, **{
                'name': concept.name,
                'type': concept.concept_type,
                'file_path': concept.file_path
            })

        # Add edges (only if both nodes exist)
        for edge in self.edges:
            if edge.source in self.concepts and edge.target in self.concepts:
                G.add_edge(
                    edge.source,
                    edge.target,
                    edge_type=edge.edge_type,
                    confidence=edge.confidence
                )

        # Check for cycles and remove if necessary
        if not nx.is_directed_acyclic_graph(G):
            logger.warning("Graph contains cycles - removing edges to create DAG")
            # Remove edges to break cycles
            while not nx.is_directed_acyclic_graph(G):
                try:
                    cycle = nx.find_cycle(G)
                    # Remove the edge with lowest confidence in the cycle
                    edge_to_remove = min(
                        cycle,
                        key=lambda e: G.edges[e[0], e[1]].get('confidence', 0.5)
                    )
                    G.remove_edge(edge_to_remove[0], edge_to_remove[1])
                except nx.NetworkXNoCycle:
                    break

        return G

    def _compute_all_knowledge_levels(self) -> Dict[str, float]:
        """
        Compute knowledge levels for all concepts.

        Uses Grok's formula:
        knowledge_level = out_degree / (in_degree + out_degree)

        Interpretation:
        - 0.0 = foundational (many depend on this)
        - 0.5 = intermediate
        - 1.0 = advanced (depends on many things)

        Returns:
            Dictionary of concept_id -> knowledge_level
        """
        if not self.graph:
            return {}

        levels = {}

        for node_id in self.graph.nodes():
            level = self._compute_knowledge_level(node_id)
            levels[node_id] = level

            # Update concept
            if node_id in self.concepts:
                self.concepts[node_id].knowledge_level = level

        return levels

    def _compute_knowledge_level(self, node_id: str) -> float:
        """
        Compute knowledge level for a single concept.

        Formula (from Grok Topic 2):
        knowledge_level = out_degree / (in_degree + out_degree)

        Args:
            node_id: Concept ID

        Returns:
            Knowledge level (0.0 to 1.0)
        """
        if not self.graph or node_id not in self.graph:
            return 0.5

        in_degree = self.graph.in_degree(node_id)
        out_degree = self.graph.out_degree(node_id)

        total = in_degree + out_degree

        if total == 0:
            # Isolated concept - assign intermediate level
            return 0.5

        # Basic concepts: high in_degree, low out_degree → low knowledge_level
        # Advanced concepts: low in_degree, high out_degree → high knowledge_level
        knowledge_level = out_degree / total

        return knowledge_level

    def get_prerequisites(self, concept_id: str) -> List[str]:
        """
        Get all prerequisites for a concept.

        Args:
            concept_id: Concept ID

        Returns:
            List of prerequisite concept IDs
        """
        if not self.graph or concept_id not in self.graph:
            return []

        return list(self.graph.predecessors(concept_id))

    def get_dependents(self, concept_id: str) -> List[str]:
        """
        Get all concepts that depend on this concept.

        Args:
            concept_id: Concept ID

        Returns:
            List of dependent concept IDs
        """
        if not self.graph or concept_id not in self.graph:
            return []

        return list(self.graph.successors(concept_id))


# Example usage
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test_kg_extraction():
        extractor = KGExtractor()

        # Create test tree
        test_tree = {
            'node1': {
                'path': 'src/orchestration/cam_engine.py'
            },
            'node2': {
                'path': 'src/visualizer/procrustes_interpolation.py'
            },
            'node3': {
                'path': 'docs/PHASE_16_SUMMARY.md'
            }
        }

        # Extract KG
        kg = await extractor.extract_knowledge_graph(test_tree)

        print(f"\nKnowledge Graph Summary:")
        print(f"  Concepts: {kg['stats']['num_concepts']}")
        print(f"  Edges: {kg['stats']['num_edges']}")
        print(f"  Average level: {kg['stats']['avg_level']:.2f}")

        # Show some concepts
        print(f"\nSample concepts:")
        for concept in list(kg['concepts'])[:5]:
            print(f"  - {concept.name} (level: {concept.knowledge_level:.2f})")

    asyncio.run(test_kg_extraction())
