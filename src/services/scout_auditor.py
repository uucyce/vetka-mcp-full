# === PHASE 104.4: L2 SCOUT AUDITOR ===
"""
VETKA Phase 104.4 - L2 Scout Auditor for MYCELIUM Auto-Approval

MARKER_104_L2_AUDITOR
MARKER_104_NAMING_SCOUT - Renamed from Haiku to Scout for vendor abstraction

In MYCELIUM mode, L2 Scout reviews artifacts and auto-approves if:
1. Code compiles/parses (no syntax errors)
2. No security issues detected (no eval, exec, os.system abuse)
3. QA score >= 0.7
4. File paths are valid (not outside project)
5. Markers present (MARKER_104_*)

Flow:
SPORE -> HYPHA (Architect) -> FRUITING -> [L2 Scout Audit] -> Auto-approve or Flag

Modes:
- VETKA mode: User must approve artifacts (messenger-style modal)
- MYCELIUM mode: L2 Scout auto-approves based on criteria (autonomous pipeline)

Scout = Lightweight auditor for exploration/validation. Vendor-agnostic naming.

@status: active
@phase: 104.4
@depends: ast, re, dataclasses
@used_by: orchestrator_with_elisya.py, approval_service.py
"""

import re
import ast
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================

class AuditResult(Enum):
    """Result of artifact audit."""
    APPROVED = "approved"   # Safe to apply automatically
    FLAGGED = "flagged"     # Needs human review
    REJECTED = "rejected"   # Do not apply - critical issues


class AuditSeverity(Enum):
    """Severity of audit issues."""
    INFO = "info"           # Informational, no score impact
    WARNING = "warning"     # Minor issue, small score penalty
    ERROR = "error"         # Significant issue, major score penalty
    CRITICAL = "critical"   # Blocker, auto-reject


@dataclass
class AuditIssue:
    """Single audit issue found during review."""
    severity: AuditSeverity
    category: str
    message: str
    line_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'severity': self.severity.value,
            'category': self.category,
            'message': self.message,
            'line_number': self.line_number
        }


@dataclass
class ScoutAuditReport:
    """Complete audit report for artifact(s) from L2 Scout auditor."""
    result: AuditResult
    score: float  # 0.0-1.0
    issues: List[AuditIssue]
    recommendations: List[str]
    auto_approved: bool
    audit_timestamp: datetime = field(default_factory=datetime.now)
    audit_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'result': self.result.value,
            'score': round(self.score, 3),
            'issues': [i.to_dict() for i in self.issues],
            'recommendations': self.recommendations,
            'auto_approved': self.auto_approved,
            'audit_timestamp': self.audit_timestamp.isoformat(),
            'audit_duration_ms': round(self.audit_duration_ms, 2)
        }

    @property
    def has_critical_issues(self) -> bool:
        return any(i.severity == AuditSeverity.CRITICAL for i in self.issues)

    @property
    def issue_summary(self) -> str:
        """Human-readable summary of issues."""
        if not self.issues:
            return "No issues found"
        counts = {}
        for issue in self.issues:
            counts[issue.severity.value] = counts.get(issue.severity.value, 0) + 1
        return ", ".join(f"{v} {k}" for k, v in counts.items())


# ============================================================================
# SECURITY PATTERNS
# ============================================================================

SECURITY_PATTERNS = [
    # Code execution
    (r'\beval\s*\(', 'Dangerous: eval() can execute arbitrary code'),
    (r'\bexec\s*\(', 'Dangerous: exec() can execute arbitrary code'),
    (r'__import__\s*\(', 'Dynamic import can be dangerous'),

    # System commands
    (r'os\.system\s*\(', 'os.system() is vulnerable to shell injection'),
    (r'os\.popen\s*\(', 'os.popen() is vulnerable to shell injection'),
    (r'subprocess\.call.*shell\s*=\s*True', 'shell=True is vulnerable to injection'),
    (r'subprocess\.run.*shell\s*=\s*True', 'shell=True is vulnerable to injection'),
    (r'subprocess\.Popen.*shell\s*=\s*True', 'shell=True is vulnerable to injection'),

    # File operations (risky in certain contexts)
    (r'open\s*\([^)]*["\']w["\']', 'Write mode file operation - verify path'),
    (r'shutil\.rmtree\s*\(', 'Recursive delete - verify path carefully'),

    # Network (potential data exfiltration)
    (r'requests\.(get|post|put|delete)\s*\([^)]*(?!localhost|127\.0\.0\.1)', 'External network request detected'),
    (r'urllib\.request\.urlopen', 'Network request detected'),

    # Pickle (deserialization vulnerability)
    (r'pickle\.loads?\s*\(', 'Pickle deserialization can execute arbitrary code'),
    (r'cPickle\.loads?\s*\(', 'cPickle deserialization can execute arbitrary code'),
]

# Patterns that are suspicious but not critical
SUSPICIOUS_PATTERNS = [
    (r'import\s+ctypes', 'ctypes can access low-level system functions'),
    (r'from\s+ctypes\s+import', 'ctypes can access low-level system functions'),
    (r'import\s+pty', 'pty module can spawn terminals'),
    (r'import\s+socket', 'Direct socket access - verify usage'),
]


# ============================================================================
# L2 SCOUT AUDITOR CLASS
# ============================================================================

class L2ScoutAuditor:
    """
    Lightweight auditor for MYCELIUM auto-approval.

    MARKER_104_L2_AUDITOR_CLASS

    Uses simple heuristics (no LLM call) for speed.
    Designed to run in < 100ms for typical artifacts.

    Scoring:
    - Start at 1.0
    - Deduct based on issue severity
    - Final score determines result:
      - >= 0.7: APPROVED (auto-approve in MYCELIUM mode)
      - >= 0.5: FLAGGED (needs human review)
      - < 0.5:  REJECTED (do not apply)
    """

    # Score penalties by severity
    SEVERITY_PENALTIES = {
        AuditSeverity.INFO: 0.0,
        AuditSeverity.WARNING: 0.05,
        AuditSeverity.ERROR: 0.15,
        AuditSeverity.CRITICAL: 0.5,
    }

    # Thresholds
    APPROVE_THRESHOLD = 0.7
    FLAG_THRESHOLD = 0.5

    # Size limits
    MAX_FILE_SIZE = 100_000  # 100KB
    LARGE_FILE_WARNING = 50_000  # 50KB

    def __init__(
        self,
        strict_mode: bool = False,
        project_root: Optional[str] = None,
        allowed_extensions: Optional[List[str]] = None
    ):
        """
        Initialize auditor.

        Args:
            strict_mode: If True, treat warnings as errors
            project_root: Root directory for path validation
            allowed_extensions: List of allowed file extensions
        """
        self.strict_mode = strict_mode
        self.project_root = project_root or "/Users/danilagulin/Documents/VETKA_Project"
        self.allowed_extensions = allowed_extensions or [
            '.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.yaml', '.yml',
            '.md', '.txt', '.html', '.css', '.scss', '.sql', '.sh'
        ]

        # Compile regex patterns for performance
        self._security_patterns = [
            (re.compile(pattern, re.IGNORECASE), desc)
            for pattern, desc in SECURITY_PATTERNS
        ]
        self._suspicious_patterns = [
            (re.compile(pattern, re.IGNORECASE), desc)
            for pattern, desc in SUSPICIOUS_PATTERNS
        ]

        logger.info(f"[L2ScoutAuditor] Initialized (strict_mode={strict_mode})")

    def audit_artifact(self, artifact: Dict) -> ScoutAuditReport:
        """
        Audit single artifact for auto-approval.

        MARKER_104_AUDIT_ARTIFACT

        Args:
            artifact: Dict with keys: content, language, filename, type

        Returns:
            ScoutAuditReport with result, score, and issues
        """
        start_time = datetime.now()
        issues: List[AuditIssue] = []
        recommendations: List[str] = []
        score = 1.0

        content = artifact.get('content', '')
        language = artifact.get('language', 'text')
        filename = artifact.get('filename', '')
        artifact_type = artifact.get('type', 'code')

        # 1. Basic validation
        if not content:
            issues.append(AuditIssue(
                severity=AuditSeverity.WARNING,
                category='validation',
                message='Empty content'
            ))
            score -= 0.1

        # 2. Size check
        size_issues, size_penalty = self._check_size(content)
        issues.extend(size_issues)
        score -= size_penalty

        # 3. Syntax check (language-specific)
        syntax_issues, syntax_penalty = self._check_syntax(content, language)
        issues.extend(syntax_issues)
        score -= syntax_penalty

        # 4. Security scan
        security_issues, security_penalty = self._check_security(content)
        issues.extend(security_issues)
        score -= security_penalty

        # 5. Path validation
        if filename:
            path_issues, path_penalty = self._check_path(filename)
            issues.extend(path_issues)
            score -= path_penalty

        # 6. Marker check (traceability)
        if 'MARKER_' not in content and language == 'python':
            recommendations.append("Consider adding MARKER_104_* for traceability")
            score -= 0.02

        # 7. Code quality hints
        quality_recs = self._check_quality_hints(content, language)
        recommendations.extend(quality_recs)

        # Apply strict mode
        if self.strict_mode:
            warnings = [i for i in issues if i.severity == AuditSeverity.WARNING]
            for w in warnings:
                w.severity = AuditSeverity.ERROR
                score -= 0.1  # Additional penalty

        # Clamp score
        score = max(0.0, min(1.0, score))

        # Determine result
        has_critical = any(i.severity == AuditSeverity.CRITICAL for i in issues)

        if has_critical or score < self.FLAG_THRESHOLD:
            result = AuditResult.REJECTED
            auto_approved = False
        elif score >= self.APPROVE_THRESHOLD and not has_critical:
            result = AuditResult.APPROVED
            auto_approved = True
        else:
            result = AuditResult.FLAGGED
            auto_approved = False

        # Calculate duration
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        report = ScoutAuditReport(
            result=result,
            score=score,
            issues=issues,
            recommendations=recommendations,
            auto_approved=auto_approved,
            audit_duration_ms=duration_ms
        )

        logger.info(
            f"[L2ScoutAuditor] Audited artifact: {filename or 'unnamed'} | "
            f"result={result.value} score={score:.2f} issues={len(issues)} "
            f"duration={duration_ms:.1f}ms"
        )

        return report

    def audit_batch(
        self,
        artifacts: List[Dict]
    ) -> Tuple[ScoutAuditReport, List[ScoutAuditReport]]:
        """
        Audit batch of artifacts, return overall + individual reports.

        MARKER_104_AUDIT_BATCH

        Args:
            artifacts: List of artifact dicts

        Returns:
            Tuple of (overall_report, individual_reports)
        """
        start_time = datetime.now()

        if not artifacts:
            return ScoutAuditReport(
                result=AuditResult.APPROVED,
                score=1.0,
                issues=[],
                recommendations=["No artifacts to audit"],
                auto_approved=True
            ), []

        # Audit each artifact
        reports = [self.audit_artifact(a) for a in artifacts]

        # Calculate overall score (minimum of all)
        min_score = min(r.score for r in reports)

        # Collect all issues
        all_issues = [issue for r in reports for issue in r.issues]
        all_recommendations = list(set(
            rec for r in reports for rec in r.recommendations
        ))

        # Determine overall result
        all_approved = all(r.result == AuditResult.APPROVED for r in reports)
        any_rejected = any(r.result == AuditResult.REJECTED for r in reports)

        if any_rejected:
            overall_result = AuditResult.REJECTED
            auto_approved = False
        elif all_approved:
            overall_result = AuditResult.APPROVED
            auto_approved = True
        else:
            overall_result = AuditResult.FLAGGED
            auto_approved = False

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        overall = ScoutAuditReport(
            result=overall_result,
            score=min_score,
            issues=all_issues,
            recommendations=all_recommendations,
            auto_approved=auto_approved,
            audit_duration_ms=duration_ms
        )

        logger.info(
            f"[L2ScoutAuditor] Batch audit: {len(artifacts)} artifacts | "
            f"result={overall_result.value} min_score={min_score:.2f} "
            f"total_issues={len(all_issues)}"
        )

        return overall, reports

    def should_auto_approve(self, artifacts: List[Dict]) -> Tuple[bool, ScoutAuditReport]:
        """
        Quick check if artifacts should be auto-approved in MYCELIUM mode.

        Args:
            artifacts: List of artifact dicts

        Returns:
            Tuple of (should_approve, overall_report)
        """
        overall, _ = self.audit_batch(artifacts)
        return overall.auto_approved, overall

    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================

    def _check_size(self, content: str) -> Tuple[List[AuditIssue], float]:
        """Check content size."""
        issues = []
        penalty = 0.0
        size = len(content)

        if size > self.MAX_FILE_SIZE:
            issues.append(AuditIssue(
                severity=AuditSeverity.ERROR,
                category='size',
                message=f'File too large: {size:,} bytes (max: {self.MAX_FILE_SIZE:,})'
            ))
            penalty = 0.2
        elif size > self.LARGE_FILE_WARNING:
            issues.append(AuditIssue(
                severity=AuditSeverity.WARNING,
                category='size',
                message=f'Large file: {size:,} bytes'
            ))
            penalty = 0.05

        return issues, penalty

    def _check_syntax(
        self,
        content: str,
        language: str
    ) -> Tuple[List[AuditIssue], float]:
        """Check syntax for supported languages."""
        issues = []
        penalty = 0.0

        if language == 'python':
            try:
                ast.parse(content)
            except SyntaxError as e:
                issues.append(AuditIssue(
                    severity=AuditSeverity.CRITICAL,
                    category='syntax',
                    message=f'Python syntax error: {e.msg}',
                    line_number=e.lineno
                ))
                penalty = 0.5

        elif language in ('json',):
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                issues.append(AuditIssue(
                    severity=AuditSeverity.CRITICAL,
                    category='syntax',
                    message=f'JSON parse error: {e.msg}',
                    line_number=e.lineno
                ))
                penalty = 0.5

        elif language in ('javascript', 'typescript', 'js', 'ts'):
            # Basic JS/TS checks (limited without full parser)
            if content.count('{') != content.count('}'):
                issues.append(AuditIssue(
                    severity=AuditSeverity.WARNING,
                    category='syntax',
                    message='Mismatched braces (may be false positive)'
                ))
                penalty = 0.1

        return issues, penalty

    def _check_security(self, content: str) -> Tuple[List[AuditIssue], float]:
        """Scan for security issues."""
        issues = []
        penalty = 0.0

        # Check critical security patterns
        for pattern, description in self._security_patterns:
            matches = list(pattern.finditer(content))
            for match in matches:
                # Find line number
                line_num = content[:match.start()].count('\n') + 1
                issues.append(AuditIssue(
                    severity=AuditSeverity.CRITICAL,
                    category='security',
                    message=description,
                    line_number=line_num
                ))
                penalty += 0.25

        # Check suspicious patterns (warnings only)
        for pattern, description in self._suspicious_patterns:
            if pattern.search(content):
                issues.append(AuditIssue(
                    severity=AuditSeverity.WARNING,
                    category='security',
                    message=description
                ))
                penalty += 0.05

        return issues, min(penalty, 0.8)  # Cap security penalty

    def _check_path(self, path: str) -> Tuple[List[AuditIssue], float]:
        """Validate file path."""
        issues = []
        penalty = 0.0

        # Path traversal attack
        if '..' in path:
            issues.append(AuditIssue(
                severity=AuditSeverity.CRITICAL,
                category='path',
                message=f'Path traversal detected: {path}'
            ))
            penalty = 0.5
            return issues, penalty

        # Absolute path outside project
        if path.startswith('/'):
            if not path.startswith(self.project_root):
                issues.append(AuditIssue(
                    severity=AuditSeverity.ERROR,
                    category='path',
                    message=f'Path outside project root: {path}'
                ))
                penalty = 0.3

        # Check extension
        ext = Path(path).suffix.lower()
        if ext and ext not in self.allowed_extensions:
            issues.append(AuditIssue(
                severity=AuditSeverity.WARNING,
                category='path',
                message=f'Unusual file extension: {ext}'
            ))
            penalty = 0.05

        # Dangerous paths
        dangerous_paths = ['/etc/', '/usr/', '/bin/', '/var/', '~/', '$HOME']
        for dangerous in dangerous_paths:
            if dangerous in path:
                issues.append(AuditIssue(
                    severity=AuditSeverity.CRITICAL,
                    category='path',
                    message=f'Dangerous path detected: {path}'
                ))
                penalty = 0.5
                break

        return issues, penalty

    def _check_quality_hints(
        self,
        content: str,
        language: str
    ) -> List[str]:
        """Generate quality improvement recommendations."""
        recommendations = []

        if language == 'python':
            # Check for docstrings
            if 'def ' in content and '"""' not in content and "'''" not in content:
                recommendations.append("Consider adding docstrings to functions")

            # Check for type hints
            if 'def ' in content and '->' not in content:
                recommendations.append("Consider adding type hints")

            # Check for logging
            if 'print(' in content and 'logging' not in content:
                recommendations.append("Consider using logging instead of print()")

        elif language in ('javascript', 'typescript', 'js', 'ts'):
            # Check for console.log
            if 'console.log(' in content:
                recommendations.append("Remove console.log() before production")

        return recommendations


# ============================================================================
# SINGLETON FACTORY
# ============================================================================

_scout_auditor: Optional[L2ScoutAuditor] = None


def get_scout_auditor(
    strict_mode: bool = False,
    project_root: Optional[str] = None
) -> L2ScoutAuditor:
    """
    Factory function for singleton auditor.

    MARKER_104_AUDITOR_FACTORY

    Args:
        strict_mode: If True, treat warnings as errors
        project_root: Root directory for path validation

    Returns:
        L2ScoutAuditor singleton instance
    """
    global _scout_auditor
    if _scout_auditor is None:
        _scout_auditor = L2ScoutAuditor(
            strict_mode=strict_mode,
            project_root=project_root
        )
    return _scout_auditor


def reset_scout_auditor():
    """Reset singleton (for testing)."""
    global _scout_auditor
    _scout_auditor = None


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("L2 SCOUT AUDITOR - TEST SUITE")
    print("MARKER_104_AUDITOR_TESTS")
    print("=" * 60)

    # Reset for fresh instance
    reset_scout_auditor()
    auditor = get_scout_auditor()

    # Test 1: Clean Python code
    print("\n[TEST 1] Clean Python code")
    clean_code = '''
"""Clean module with proper docstrings."""

MARKER_104_TEST

def greet(name: str) -> str:
    """Return greeting for name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(greet("World"))
'''
    report = auditor.audit_artifact({
        'content': clean_code,
        'language': 'python',
        'filename': 'src/clean.py'
    })
    print(f"  Result: {report.result.value}")
    print(f"  Score: {report.score:.2f}")
    print(f"  Auto-approved: {report.auto_approved}")
    print(f"  Issues: {report.issue_summary}")
    assert report.result == AuditResult.APPROVED, "Clean code should be approved"
    assert report.auto_approved, "Clean code should be auto-approved"
    print("  PASSED")

    # Test 2: Code with syntax error
    print("\n[TEST 2] Python code with syntax error")
    syntax_error_code = '''
def broken(
    return "missing parenthesis"
'''
    report = auditor.audit_artifact({
        'content': syntax_error_code,
        'language': 'python',
        'filename': 'src/broken.py'
    })
    print(f"  Result: {report.result.value}")
    print(f"  Score: {report.score:.2f}")
    print(f"  Issues: {[i.message for i in report.issues]}")
    assert report.result == AuditResult.REJECTED, "Syntax error should be rejected"
    assert not report.auto_approved, "Syntax error should not be auto-approved"
    print("  PASSED")

    # Test 3: Code with security issues
    print("\n[TEST 3] Python code with security issues")
    security_code = '''
MARKER_104_SECURITY_TEST

import os

def run_command(cmd: str) -> None:
    os.system(cmd)  # Dangerous!

def evaluate(expr: str) -> any:
    return eval(expr)  # Very dangerous!
'''
    report = auditor.audit_artifact({
        'content': security_code,
        'language': 'python',
        'filename': 'src/security.py'
    })
    print(f"  Result: {report.result.value}")
    print(f"  Score: {report.score:.2f}")
    print(f"  Issues: {len(report.issues)}")
    for issue in report.issues:
        print(f"    - [{issue.severity.value}] {issue.message}")
    assert report.result == AuditResult.REJECTED, "Security issues should be rejected"
    assert len(report.issues) >= 2, "Should detect multiple security issues"
    print("  PASSED")

    # Test 4: Path traversal
    print("\n[TEST 4] Path traversal detection")
    report = auditor.audit_artifact({
        'content': 'print("hello")',
        'language': 'python',
        'filename': '../../../etc/passwd'
    })
    print(f"  Result: {report.result.value}")
    print(f"  Issues: {[i.message for i in report.issues]}")
    assert report.result == AuditResult.REJECTED, "Path traversal should be rejected"
    print("  PASSED")

    # Test 5: Large file warning
    print("\n[TEST 5] Large file warning")
    large_content = "# " + "x" * 60000  # ~60KB
    report = auditor.audit_artifact({
        'content': large_content,
        'language': 'python',
        'filename': 'src/large.py'
    })
    print(f"  Result: {report.result.value}")
    print(f"  Score: {report.score:.2f}")
    has_size_warning = any('Large file' in i.message for i in report.issues)
    assert has_size_warning, "Should warn about large file"
    print("  PASSED")

    # Test 6: Batch audit
    print("\n[TEST 6] Batch audit")
    artifacts = [
        {'content': 'def good(): pass', 'language': 'python', 'filename': 'a.py'},
        {'content': 'def also_good(): pass', 'language': 'python', 'filename': 'b.py'},
    ]
    overall, reports = auditor.audit_batch(artifacts)
    print(f"  Overall result: {overall.result.value}")
    print(f"  Overall score: {overall.score:.2f}")
    print(f"  Individual results: {[r.result.value for r in reports]}")
    assert overall.result == AuditResult.APPROVED, "All good artifacts should be approved"
    print("  PASSED")

    # Test 7: Batch with one bad artifact
    print("\n[TEST 7] Batch with one bad artifact")
    artifacts = [
        {'content': 'def good(): pass', 'language': 'python', 'filename': 'a.py'},
        {'content': 'eval("bad")', 'language': 'python', 'filename': 'b.py'},
    ]
    overall, reports = auditor.audit_batch(artifacts)
    print(f"  Overall result: {overall.result.value}")
    print(f"  Individual results: {[r.result.value for r in reports]}")
    assert overall.result == AuditResult.REJECTED, "One bad artifact should reject batch"
    print("  PASSED")

    # Test 8: JSON validation
    print("\n[TEST 8] JSON validation")
    valid_json = '{"key": "value", "number": 42}'
    report = auditor.audit_artifact({
        'content': valid_json,
        'language': 'json',
        'filename': 'config.json'
    })
    print(f"  Valid JSON - Result: {report.result.value}")
    assert report.result == AuditResult.APPROVED, "Valid JSON should be approved"

    invalid_json = '{"key": value}'  # Missing quotes
    report = auditor.audit_artifact({
        'content': invalid_json,
        'language': 'json',
        'filename': 'config.json'
    })
    print(f"  Invalid JSON - Result: {report.result.value}")
    assert report.result == AuditResult.REJECTED, "Invalid JSON should be rejected"
    print("  PASSED")

    # Test 9: Strict mode
    print("\n[TEST 9] Strict mode")
    reset_scout_auditor()
    strict_auditor = L2ScoutAuditor(strict_mode=True)

    code_with_warning = '''
import ctypes  # This is suspicious
def foo():
    pass
'''
    report = strict_auditor.audit_artifact({
        'content': code_with_warning,
        'language': 'python',
        'filename': 'src/foo.py'
    })
    print(f"  Strict mode result: {report.result.value}")
    print(f"  Score: {report.score:.2f}")
    # In strict mode, warnings become errors with higher penalty
    assert report.score < 0.9, "Strict mode should penalize warnings more"
    print("  PASSED")

    # Test 10: should_auto_approve helper
    print("\n[TEST 10] should_auto_approve helper")
    reset_scout_auditor()
    auditor = get_scout_auditor()

    should_approve, report = auditor.should_auto_approve([
        {'content': 'print("safe")', 'language': 'python', 'filename': 'x.py'}
    ])
    print(f"  Should approve: {should_approve}")
    assert should_approve, "Safe code should be auto-approved"

    should_approve, report = auditor.should_auto_approve([
        {'content': 'eval("unsafe")', 'language': 'python', 'filename': 'x.py'}
    ])
    print(f"  Should NOT approve unsafe: {not should_approve}")
    assert not should_approve, "Unsafe code should not be auto-approved"
    print("  PASSED")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)

    sys.exit(0)
