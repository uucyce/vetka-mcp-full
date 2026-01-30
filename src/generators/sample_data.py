# src/generators/sample_data.py
"""
Sample data generator for VETKA workflows.

Generates demo/test data representing a complete workflow execution
including PM, Architect, Dev, QA results and ARC suggestions.

@status: active
@phase: 96
@depends: datetime
@used_by: src.generators.__init__, tests
"""

from datetime import datetime


class SampleDataGenerator:
    """Generate demo data."""

    def generate(self) -> dict:
        return {
            "workflow_id": "demo_001",
            "timestamp": datetime.now().isoformat(),
            "source": "demo",

            "pm_result": {
                "plan": "Build project management system with AI assistant",
                "risks": ["Technical complexity", "Limited time"],
                "milestones": ["Research", "Design", "Development", "Testing"],
                "eval_score": 0.92
            },

            "architect_result": {
                "diagram": "graph TD\n  A[Frontend] --> B[API]\n  B --> C[Database]",
                "description": "Microservices architecture with React frontend",
                "tech_stack": ["React", "Node.js", "PostgreSQL", "Redis"],
                "eval_score": 0.88
            },

            "dev_result": {
                "files": [
                    {"name": "auth.ts", "path": "src/auth.ts", "language": "typescript"},
                    {"name": "api.ts", "path": "src/api.ts", "language": "typescript"},
                    {"name": "database.ts", "path": "src/database.ts", "language": "typescript"},
                    {"name": "schema.sql", "path": "db/schema.sql", "language": "sql"},
                    {"name": "docker-compose.yml", "path": "docker-compose.yml", "language": "yaml"}
                ],
                "eval_score": 0.85
            },

            "qa_result": {
                "coverage": 82,
                "passed": 156,
                "failed": 12,
                "tests": ["test_auth.ts", "test_api.ts", "test_database.ts"],
                "eval_score": 0.81
            },

            "arc_suggestions": [
                {"transformation": "Add Redis caching for sessions", "success": 0.94},
                {"transformation": "Implement rate limiting middleware", "success": 0.87},
                {"transformation": "Add OpenTelemetry tracing", "success": 0.75}
            ],

            "metrics": {"total_time_ms": 42000}
        }
