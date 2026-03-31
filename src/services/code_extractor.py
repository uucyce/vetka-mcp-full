"""
Code extractor for browser AI responses.

Extracts code from:
- DOM parsing: <pre>, <code>, markdown code blocks
- Multi-file detection (multiple code blocks = multiple files)
- Language detection (python, typescript, etc.)
- Syntax validation (ast.parse for Python, tsc for TS)
- File path matching against allowed_paths
- Minimum length check (>50 chars)

Fallback to OCR (Tesseract) if DOM parsing fails.

MARKER_196.BP1.4: Code extractor implementation
"""

import ast
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger("vetka.code_extractor")

# Language to file extension mapping
LANG_EXTENSIONS = {
    "python": ".py",
    "py": ".py",
    "typescript": ".ts",
    "ts": ".ts",
    "typescriptreact": ".tsx",
    "tsx": ".tsx",
    "javascript": ".js",
    "js": ".js",
    "javascriptreact": ".jsx",
    "jsx": ".jsx",
    "rust": ".rs",
    "go": ".go",
    "golang": ".go",
    "java": ".java",
    "cpp": ".cpp",
    "c++": ".cpp",
    "c": ".c",
    "html": ".html",
    "css": ".css",
    "scss": ".scss",
    "json": ".json",
    "yaml": ".yaml",
    "yml": ".yaml",
    "toml": ".toml",
    "bash": ".sh",
    "shell": ".sh",
    "sh": ".sh",
    "sql": ".sql",
    "ruby": ".rb",
    "php": ".php",
    "swift": ".swift",
    "kotlin": ".kt",
    "dart": ".dart",
    "r": ".r",
    "markdown": ".md",
    "md": ".md",
    "xml": ".xml",
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
}

# Minimum code block length to consider valid
MIN_CODE_LENGTH = 50

# File path patterns to detect from code block comments
FILE_PATH_PATTERN = re.compile(
    r"(?:^|\n)\s*[#/]*\s*(?:file|path|filename|save to|write to)\s*[:=]?\s*([^\n]+)",
    re.IGNORECASE,
)

# Shebang detection
SHEBANG_PATTERNS = {
    "python": re.compile(r"^#!/.*python"),
    "bash": re.compile(r"^#!/.*(?:bash|sh|zsh)"),
    "ruby": re.compile(r"^#!/.*ruby"),
    "perl": re.compile(r"^#!/.*perl"),
}


@dataclass
class ExtractedFile:
    """A single extracted code file."""

    content: str
    language: str
    extension: str
    suggested_path: str = ""
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    char_count: int = 0
    line_count: int = 0
    source: str = "dom"  # "dom", "markdown", "ocr"


@dataclass
class ExtractionResult:
    """Result of code extraction."""

    success: bool
    files: List[ExtractedFile] = field(default_factory=list)
    raw_text: str = ""
    error: Optional[str] = None
    source: str = "dom"  # "dom", "markdown", "ocr"
    total_blocks_found: int = 0
    total_blocks_valid: int = 0


class CodeExtractor:
    """
    Extracts and validates code from AI chat responses.

    Usage:
        extractor = CodeExtractor()
        result = extractor.extract_from_dom(html_content)
        # or
        result = extractor.extract_from_markdown(text_content)
    """

    def __init__(
        self,
        min_length: int = MIN_CODE_LENGTH,
        allowed_paths: Optional[List[str]] = None,
        enable_validation: bool = True,
        ocr_fallback: bool = True,
    ):
        self.min_length = min_length
        self.allowed_paths = allowed_paths or []
        self.enable_validation = enable_validation
        self.ocr_fallback = ocr_fallback

    def extract_from_dom(self, html_content: str) -> ExtractionResult:
        """
        Extract code from HTML/DOM content.

        Args:
            html_content: HTML string from the page

        Returns:
            ExtractionResult with extracted code files
        """
        try:
            files = []
            total_blocks = 0

            # Extract <pre> blocks
            pre_blocks = self._extract_tag_content(html_content, "pre")
            for block in pre_blocks:
                total_blocks += 1
                extracted = self._process_block(block, source="dom")
                if extracted:
                    files.append(extracted)

            # Extract <code> blocks (not inside <pre>)
            code_blocks = self._extract_tag_content(html_content, "code")
            for block in code_blocks:
                # Skip if already captured as part of <pre>
                if any(block.strip() in f.content for f in files):
                    continue
                total_blocks += 1
                extracted = self._process_block(block, source="dom")
                if extracted:
                    files.append(extracted)

            # If no structured blocks, try markdown parsing on full text
            if not files:
                text_content = self._strip_html(html_content)
                return self.extract_from_markdown(text_content, source="dom")

            return ExtractionResult(
                success=bool(files),
                files=files,
                raw_text=self._strip_html(html_content),
                source="dom",
                total_blocks_found=total_blocks,
                total_blocks_valid=len(files),
            )

        except Exception as e:
            logger.error(f"DOM extraction failed: {e}")
            return ExtractionResult(success=False, error=str(e), source="dom")

    def extract_from_markdown(
        self, text_content: str, source: str = "markdown"
    ) -> ExtractionResult:
        """
        Extract code blocks from markdown text.

        Args:
            text_content: Raw text with markdown code blocks
            source: Source type for tracking

        Returns:
            ExtractionResult with extracted code files
        """
        try:
            files = []
            total_blocks = 0

            # Find fenced code blocks: ```lang ... ```
            pattern = re.compile(r"```(\w+)?\s*\n(.*?)```", re.DOTALL)
            for match in pattern.finditer(text_content):
                total_blocks += 1
                lang = (match.group(1) or "").strip().lower()
                code = match.group(2).strip()
                extracted = self._process_code_string(code, lang, source=source)
                if extracted:
                    files.append(extracted)

            # If no fenced blocks, check for indented code blocks
            if not files:
                indented = self._extract_indented_blocks(text_content)
                for block in indented:
                    total_blocks += 1
                    extracted = self._process_block(block, source=source)
                    if extracted:
                        files.append(extracted)

            # If still no blocks, treat entire text as code if it looks like code
            if not files and self._looks_like_code(text_content):
                total_blocks = 1
                extracted = self._process_code_string(
                    text_content.strip(), "", source=source
                )
                if extracted:
                    files.append(extracted)

            return ExtractionResult(
                success=bool(files),
                files=files,
                raw_text=text_content,
                source=source,
                total_blocks_found=total_blocks,
                total_blocks_valid=len(files),
            )

        except Exception as e:
            logger.error(f"Markdown extraction failed: {e}")
            return ExtractionResult(success=False, error=str(e), source=source)

    def extract_from_ocr(self, image_path: str) -> ExtractionResult:
        """
        Fallback: extract code from screenshot via OCR.

        Args:
            image_path: Path to screenshot image

        Returns:
            ExtractionResult with OCR-extracted code
        """
        if not self.ocr_fallback:
            return ExtractionResult(
                success=False, error="OCR fallback disabled", source="ocr"
            )

        try:
            text = self._run_ocr(image_path)
            if not text:
                return ExtractionResult(
                    success=False, error="OCR returned no text", source="ocr"
                )

            # Parse the OCR text as markdown
            result = self.extract_from_markdown(text, source="ocr")
            result.source = "ocr"
            return result

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ExtractionResult(success=False, error=str(e), source="ocr")

    def validate_file(self, extracted: ExtractedFile) -> ExtractedFile:
        """
        Validate a single extracted file.

        Checks:
        - Syntax validation (language-specific)
        - Minimum length
        - Path matching against allowed_paths
        """
        errors = []

        # Length check
        if extracted.char_count < self.min_length:
            errors.append(f"Code too short: {extracted.char_count} < {self.min_length}")

        # Syntax validation
        if self.enable_validation:
            syntax_errors = self._validate_syntax(extracted.content, extracted.language)
            errors.extend(syntax_errors)

        # Path check
        if self.allowed_paths and extracted.suggested_path:
            if not self._path_allowed(extracted.suggested_path):
                errors.append(f"Path not in allowed_paths: {extracted.suggested_path}")

        extracted.is_valid = len(errors) == 0
        extracted.validation_errors = errors
        return extracted

    # ---- Private methods ----

    def _process_block(
        self, block: str, source: str = "dom"
    ) -> Optional[ExtractedFile]:
        """Process a raw code block string into an ExtractedFile."""
        # Try to detect language from block content
        lang, code = self._detect_language_from_block(block)
        return self._process_code_string(code, lang, source=source)

    def _process_code_string(
        self, code: str, language: str, source: str = "dom"
    ) -> Optional[ExtractedFile]:
        """Process a code string into an ExtractedFile with validation."""
        if not code or len(code.strip()) < 10:
            return None

        code = code.strip()
        lang = language.lower() if language else self._detect_language(code)
        ext = LANG_EXTENSIONS.get(lang, ".txt")

        # Detect file path from comments
        suggested_path = self._detect_file_path(code, lang, ext)

        extracted = ExtractedFile(
            content=code,
            language=lang or "text",
            extension=ext,
            suggested_path=suggested_path,
            char_count=len(code),
            line_count=code.count("\n") + 1,
            source=source,
        )

        # Validate
        if self.enable_validation:
            extracted = self.validate_file(extracted)

        return extracted

    def _detect_language_from_block(self, block: str) -> Tuple[str, str]:
        """Detect language from block metadata and return (lang, code)."""
        # Check for language comment at start
        first_lines = block.split("\n")[:3]
        for line in first_lines:
            stripped = line.strip().lstrip("#/").strip()
            if stripped.lower().startswith("language:"):
                lang = stripped.split(":", 1)[1].strip().lower()
                return lang, block

            if stripped.lower().startswith("lang:"):
                lang = stripped.split(":", 1)[1].strip().lower()
                return lang, block

        # Check for shebang
        if block.startswith("#!"):
            for lang, pattern in SHEBANG_PATTERNS.items():
                if pattern.match(block):
                    return lang, block

        # Check for language-specific patterns
        lang = self._detect_language(block)
        return lang, block

    def _detect_language(self, code: str) -> str:
        """Detect programming language from code content."""
        # Python indicators
        if re.search(r"\b(def |class |import |from \w+ import |if __name__)", code):
            return "python"

        # TypeScript/React indicators
        if re.search(
            r"\b(import .+ from |export (default |const |function|class)|interface \w+|type \w+ =)",
            code,
        ):
            if re.search(r"(<\w+>|React|JSX|\.tsx)", code):
                return "tsx"
            return "typescript"

        # JavaScript indicators
        if re.search(r"\b(const |let |var |function |=> |console\.)", code):
            if re.search(r"(<\w+>|React|ReactDOM)", code):
                return "jsx"
            return "javascript"

        # Rust
        if re.search(r"\b(fn \w+|let mut |impl \w+|pub (struct|fn|enum))", code):
            return "rust"

        # Go
        if re.search(r"\b(func \w+|package main|import \(|type \w+ struct)", code):
            return "go"

        # Java
        if re.search(
            r"\b(public class |private |protected |void main|System\.out)", code
        ):
            return "java"

        # HTML
        if re.search(r"<(!DOCTYPE|html|head|body|div|span)", code):
            return "html"

        # CSS
        if re.search(r"\{[^}]*\s+\w+:\s+[^}]+\}", code) and not re.search(
            r"\b(function|def |class )", code
        ):
            return "css"

        # JSON
        if code.strip().startswith("{") and code.strip().endswith("}"):
            try:
                import json

                json.loads(code)
                return "json"
            except (json.JSONDecodeError, ValueError):
                pass

        # YAML
        if re.search(r"^\w[\w\s]*:\s+\S", code, re.MULTILINE) and not re.search(
            r"[;{}()]", code
        ):
            return "yaml"

        # SQL
        if re.search(
            r"\b(SELECT |INSERT |UPDATE |DELETE |CREATE TABLE|FROM \w+)",
            code,
            re.IGNORECASE,
        ):
            return "sql"

        # Bash
        if code.startswith("#!/") or re.search(
            r"\b(echo |grep |sed |awk |curl |wget )", code
        ):
            return "bash"

        return "text"

    def _detect_file_path(self, code: str, language: str, default_ext: str) -> str:
        """Detect suggested file path from code comments or content."""
        # Check for file path comments
        match = FILE_PATH_PATTERN.search(code)
        if match:
            path = match.group(1).strip().strip("\"'`")
            if path and len(path) < 200:
                return path

        # Generate from language
        ext = LANG_EXTENSIONS.get(language, default_ext)
        if language == "python":
            # Try to find module/class name
            class_match = re.search(r"class\s+(\w+)", code)
            if class_match:
                return f"{class_match.group(1).lower()}{ext}"

        return f"extracted_{len(code)}{ext}"

    def _validate_syntax(self, code: str, language: str) -> List[str]:
        """Validate code syntax for supported languages."""
        errors = []

        if language in ("python", "py"):
            try:
                ast.parse(code)
            except SyntaxError as e:
                errors.append(f"Python syntax error: {e}")

        elif language in ("typescript", "ts", "tsx", "javascript", "js", "jsx"):
            errors.extend(self._validate_typescript(code))

        elif language in ("json",):
            try:
                import json

                json.loads(code)
            except json.JSONDecodeError as e:
                errors.append(f"JSON syntax error: {e}")

        elif language in ("yaml", "yml"):
            try:
                import yaml

                yaml.safe_load(code)
            except Exception:
                pass  # yaml may not be installed

        return errors

    def _validate_typescript(self, code: str) -> List[str]:
        """Validate TypeScript/JavaScript syntax."""
        errors = []
        try:
            # Try node --check for syntax validation
            result = subprocess.run(
                ["node", "--check", "-e", code],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                errors.append(f"JS syntax error: {result.stderr.strip()[:200]}")
        except FileNotFoundError:
            pass  # node not installed
        except subprocess.TimeoutExpired:
            pass  # validation timeout

        # Try tsc if available
        try:
            result = subprocess.run(
                [
                    "tsc",
                    "--noEmit",
                    "--strict",
                    "--target",
                    "ES2020",
                    "--lib",
                    "ES2020",
                    "-",
                ],
                input=code,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                errors.append(f"TS error: {result.stderr.strip()[:200]}")
        except FileNotFoundError:
            pass  # tsc not installed
        except subprocess.TimeoutExpired:
            pass

        return errors

    def _path_allowed(self, path: str) -> bool:
        """Check if a path is within allowed_paths."""
        if not self.allowed_paths:
            return True

        path_normalized = os.path.normpath(path)
        for allowed in self.allowed_paths:
            allowed_normalized = os.path.normpath(allowed)
            if path_normalized.startswith(allowed_normalized):
                return True
            # Check if the file matches a pattern
            if Path(path_normalized).match(allowed_normalized):
                return True

        return False

    def _looks_like_code(self, text: str) -> bool:
        """Heuristic: does this text look like code?"""
        code_indicators = [
            r"\b(def |function |class |import |from |const |let |var )",
            r"[{}();]",
            r"^\s*(if |else |for |while |return |try |catch )",
            r"// |# |/\* |\*/",
        ]
        score = 0
        for pattern in code_indicators:
            if re.search(pattern, text, re.MULTILINE):
                score += 1
        return score >= 2

    def _extract_tag_content(self, html: str, tag: str) -> List[str]:
        """Extract text content from HTML tags (simple regex-based)."""
        pattern = re.compile(
            rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}>",
            re.DOTALL | re.IGNORECASE,
        )
        results = []
        for match in pattern.finditer(html):
            content = match.group(1)
            # Decode common HTML entities
            content = content.replace("&lt;", "<").replace("&gt;", ">")
            content = content.replace("&amp;", "&").replace("&quot;", '"')
            content = content.replace("&#39;", "'").replace("&nbsp;", " ")
            results.append(content)
        return results

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags from string."""
        clean = re.sub(r"<[^>]+>", "", html)
        clean = clean.replace("&lt;", "<").replace("&gt;", ">")
        clean = clean.replace("&amp;", "&").replace("&quot;", '"')
        clean = clean.replace("&#39;", "'").replace("&nbsp;", " ")
        return clean

    def _extract_indented_blocks(self, text: str) -> List[str]:
        """Extract indented code blocks (4+ spaces or tab)."""
        blocks = []
        current_block = []
        for line in text.split("\n"):
            if line.startswith("    ") or line.startswith("\t"):
                current_block.append(line)
            elif current_block:
                if len(current_block) >= 2:
                    blocks.append("\n".join(current_block))
                current_block = []
        if current_block and len(current_block) >= 2:
            blocks.append("\n".join(current_block))
        return blocks

    def _run_ocr(self, image_path: str) -> str:
        """Run Tesseract OCR on an image."""
        try:
            # Try pytesseract first
            try:
                import pytesseract
                from PIL import Image

                img = Image.open(image_path)
                return pytesseract.image_to_string(img)
            except ImportError:
                pass

            # Fallback to tesseract CLI
            result = subprocess.run(
                ["tesseract", image_path, "stdout"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout

        except FileNotFoundError:
            logger.error("Tesseract not found")
        except subprocess.TimeoutExpired:
            logger.error("OCR timeout")
        except Exception as e:
            logger.error(f"OCR failed: {e}")

        return ""
