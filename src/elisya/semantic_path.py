"""
SemanticPathGenerator: Generate dynamic semantic paths like projects/python/ml/sklearn.

@status: active
@phase: 96
@depends: typing, dataclasses, re
@used_by: middleware, orchestrator
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import re


@dataclass
class PathComponent:
    """Single component of semantic path"""
    level: int  # 0=projects, 1=language, 2=domain, 3=tool
    value: str
    confidence: float  # 0-1 how confident we are about this component


class SemanticPathGenerator:
    """
    Generates semantic paths from task context and conversation history.
    
    Format: projects/LANGUAGE/DOMAIN/TOOL
    Examples:
    - projects/python/ml/sklearn
    - projects/typescript/backend/express
    - projects/rust/system/tokio
    - projects/go/devops/kubernetes
    """
    
    # Known programming languages
    LANGUAGES = {
        "python": ["py", "python3", "pip", "conda", "django", "flask"],
        "typescript": ["ts", "typescript", "ts", "node", "npm", "react", "angular"],
        "javascript": ["js", "javascript", "node", "npm", "react", "vue"],
        "rust": ["rs", "rust", "cargo", "tokio"],
        "go": ["go", "golang", "goroutine"],
        "java": ["java", "jvm", "maven", "gradle", "spring"],
        "csharp": ["cs", "csharp", "dotnet", ".net"],
        "cpp": ["cpp", "c++", "cmake", "boost"],
        "c": ["c", "gcc", "clang"],
        "ruby": ["rb", "ruby", "rails", "gem"],
        "php": ["php", "laravel", "symfony"],
    }
    
    # Known domains
    DOMAINS = {
        "ml": ["machine learning", "ml", "neural", "tensorflow", "pytorch", "sklearn", "model", "training"],
        "backend": ["backend", "api", "server", "database", "query", "orm", "rest"],
        "frontend": ["frontend", "ui", "react", "vue", "angular", "css", "html", "component"],
        "devops": ["devops", "docker", "kubernetes", "ci/cd", "pipeline", "deployment", "terraform"],
        "system": ["system", "os", "kernel", "memory", "thread", "process", "concurrency"],
        "security": ["security", "crypto", "auth", "encryption", "permission", "token"],
        "database": ["database", "sql", "nosql", "postgres", "mongodb", "redis", "cache"],
        "testing": ["testing", "test", "pytest", "unittest", "jest", "mocha", "tdd"],
    }
    
    # Known tools
    TOOLS = {
        # ML
        "sklearn": ["sklearn", "scikit-learn", "scikit"],
        "tensorflow": ["tensorflow", "tf"],
        "pytorch": ["pytorch", "torch"],
        "pandas": ["pandas", "pd"],
        
        # Backend
        "express": ["express", "expressjs"],
        "django": ["django"],
        "fastapi": ["fastapi"],
        "spring": ["spring", "springboot"],
        
        # Frontend
        "react": ["react", "reactjs"],
        "vue": ["vue", "vuejs"],
        "angular": ["angular", "angularjs"],
        
        # DevOps
        "docker": ["docker"],
        "kubernetes": ["kubernetes", "k8s"],
        "terraform": ["terraform"],
        
        # Database
        "postgresql": ["postgres", "postgresql"],
        "mongodb": ["mongodb", "mongo"],
        "redis": ["redis"],
    }
    
    def __init__(self):
        self.path_cache: Dict[str, str] = {}
        self.extraction_log: List[Dict] = []
    
    def generate(self, task: str, history: Optional[List[str]] = None, context: str = "") -> str:
        """
        Generate semantic path from task + history.
        
        Returns: projects/LANGUAGE/DOMAIN/TOOL or projects/unknown if cannot determine
        """
        combined_text = f"{task} {context}"
        
        if history:
            combined_text += " " + " ".join(history[-3:])
        
        # Check cache first
        cache_key = combined_text[:100]
        if cache_key in self.path_cache:
            return self.path_cache[cache_key]
        
        # Extract components
        language = self._extract_language(combined_text)
        domain = self._extract_domain(combined_text)
        tool = self._extract_tool(combined_text, language)
        
        # Fallback to unknown if key parts missing
        if not language:
            language = "unknown"
        if not domain:
            domain = "unknown"
        
        path = f"projects/{language}/{domain}/{tool or language}"
        
        # Validate format
        if self._is_valid_path(path):
            self.path_cache[cache_key] = path
            self._log_extraction(task, path, language, domain, tool)
            return path
        else:
            return "projects/unknown/unknown/unknown"
    
    def _extract_language(self, text: str) -> Optional[str]:
        """Extract programming language from text"""
        text_lower = text.lower()
        
        for language, keywords in self.LANGUAGES.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return language
        
        return None
    
    def _extract_domain(self, text: str) -> Optional[str]:
        """Extract domain from text"""
        text_lower = text.lower()
        
        for domain, keywords in self.DOMAINS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return domain
        
        return None
    
    def _extract_tool(self, text: str, language: Optional[str] = None) -> Optional[str]:
        """Extract specific tool from text"""
        text_lower = text.lower()
        
        for tool, keywords in self.TOOLS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return tool
        
        # If language matches a tool name, use that
        if language and language in self.TOOLS:
            return language
        
        return None
    
    def _is_valid_path(self, path: str) -> bool:
        """Validate path format"""
        if not path.startswith("projects/"):
            return False
        
        parts = path.split("/")
        
        # Must have exactly 4 parts: projects/lang/domain/tool
        if len(parts) != 4:
            return False
        
        # Each part must be alphanumeric (allow hyphens and underscores)
        for part in parts[1:]:
            if not re.match(r"^[a-z0-9_-]+$", part):
                return False
        
        return True
    
    def _log_extraction(self, task: str, path: str, language: str, domain: str, tool: str):
        """Log extraction for debugging"""
        self.extraction_log.append({
            "task": task[:100],
            "path": path,
            "components": {
                "language": language,
                "domain": domain,
                "tool": tool,
            }
        })
    
    def get_extraction_stats(self) -> Dict:
        """Get statistics of path extractions"""
        if not self.extraction_log:
            return {"total": 0}
        
        return {
            "total_extractions": len(self.extraction_log),
            "cache_size": len(self.path_cache),
            "latest_paths": [entry["path"] for entry in self.extraction_log[-5:]],
        }


# Singleton instance
_generator_instance: Optional[SemanticPathGenerator] = None


def get_path_generator() -> SemanticPathGenerator:
    """Get or create singleton instance"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = SemanticPathGenerator()
    return _generator_instance
