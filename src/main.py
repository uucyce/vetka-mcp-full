#!/usr/bin/env python3
"""
VETKA Phase 11 Entry Point.

Standalone visualization for Phase 9 workflow output.
Transforms Phase 9 data to VETKA-JSON v1.3 for 3D visualization.

@status: active
@phase: 96
@depends: transformers, generators, scanners, validators, visualizer
@used_by: CLI invocation

Usage:
    python src/main.py --demo                    # Demo mode with sample data
    python src/main.py --input workflow.json     # Transform Phase 9 JSON
    python src/main.py --scan ./my_project       # Scan local directory
    python src/main.py --interactive             # Interactive mode (future)
    python src/main.py --open                    # Auto-open in browser

Bug fixes included (from AI Council review):
    #1  BFS bottom-up completion (Haiku)
    #2  CatmullRomCurve3 for edges (Haiku)
    #3  Local RNG instance (Haiku)
    #4  Completion by branch type (Haiku)
    #5  Recursive focus mode (Haiku)
    #6  Scanner limits + symlinks (Haiku)
    #7  Logarithmic phylotaxis radius (Haiku)
    #8  isinstance validation (Haiku)
    #9  Skip entropy for leaves (Haiku)
    #10 Unified click handler (Haiku)
    #11 --interactive fix (Qwen)
    #12 LOD with entropy*evalScore (Qwen)
    #13 hidden_in_visualization mapping (Qwen)
"""

import argparse
import json
import logging
import os
import sys
import webbrowser
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.transformers import Phase11Transformer
from src.generators import SampleDataGenerator
from src.scanners import LocalProjectScanner
from src.validators import TheoryValidator
from src.visualizer import TreeRenderer


def setup_logging(debug: bool = False) -> logging.Logger:
    """Configure logging based on debug flag."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    return logging.getLogger("vetka.main")


def main():
    parser = argparse.ArgumentParser(
        description="VETKA Phase 11 - 3D Tree Visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python src/main.py --demo                    Demo with sample data
    python src/main.py --input workflow.json    Transform Phase 9 file
    python src/main.py --scan ./my_project      Scan local project
    python src/main.py --demo --open            Demo + open in browser

Principle: "ПРИРАСТАЕТ, НЕ ЛОМАЕТСЯ" (grows, doesn't break)
        """
    )

    # Input sources (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--demo",
        action="store_true",
        help="Use demo sample data"
    )
    input_group.add_argument(
        "--input", "-i",
        type=str,
        metavar="FILE",
        help="Path to Phase 9 workflow JSON file"
    )
    input_group.add_argument(
        "--scan", "-s",
        type=str,
        metavar="DIR",
        help="Scan local directory to generate tree"
    )

    # Output options
    parser.add_argument(
        "--output", "-o",
        type=str,
        metavar="FILE",
        help="Output HTML file path (default: output/vetka_tree.html)"
    )
    parser.add_argument(
        "--json",
        type=str,
        metavar="FILE",
        help="Also save VETKA-JSON to file"
    )

    # Behavior options
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open result in browser"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode (placeholder for future)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate output against Theory v1.2"
    )

    # Debug options
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="VETKA Phase 11 v3.1"
    )

    args = parser.parse_args()
    logger = setup_logging(args.debug)

    # Interactive mode notice (FIXED: Qwen #7)
    if args.interactive:
        logger.info("Interactive mode requested (not yet implemented)")
        logger.info("Falling back to standard mode...")

    try:
        # Step 1: Get Phase 9 data
        logger.info("=" * 60)
        logger.info("VETKA Phase 11 Visualization Pipeline")
        logger.info("=" * 60)

        if args.demo:
            logger.info("Mode: Demo (sample data)")
            generator = SampleDataGenerator()
            phase9_data = generator.generate()

        elif args.input:
            logger.info(f"Mode: Input file ({args.input})")
            input_path = Path(args.input)
            if not input_path.exists():
                logger.error(f"File not found: {args.input}")
                sys.exit(1)

            with open(input_path, "r", encoding="utf-8") as f:
                phase9_data = json.load(f)

        elif args.scan:
            logger.info(f"Mode: Scan directory ({args.scan})")
            scan_path = Path(args.scan)
            if not scan_path.exists():
                logger.error(f"Directory not found: {args.scan}")
                sys.exit(1)

            scanner = LocalProjectScanner()
            phase9_data = scanner.scan(str(scan_path.absolute()))

        # Step 2: Transform to VETKA-JSON v1.3
        logger.info("-" * 60)
        logger.info("Transforming to VETKA-JSON v1.3...")

        transformer = Phase11Transformer(debug=args.debug)
        vetka_json = transformer.transform(phase9_data)

        node_count = len(vetka_json.get("tree", {}).get("nodes", []))
        edge_count = len(vetka_json.get("tree", {}).get("edges", []))
        logger.info(f"Generated: {node_count} nodes, {edge_count} edges")

        # Step 3: Validate if requested
        if args.validate:
            logger.info("-" * 60)
            logger.info("Validating against Unified Theory v1.2...")

            validator = TheoryValidator()
            is_valid, errors = validator.validate(vetka_json)

            if is_valid:
                logger.info("Validation PASSED")
            else:
                logger.warning(f"Validation FAILED with {len(errors)} errors:")
                for err in errors[:10]:  # Show first 10 errors
                    logger.warning(f"  - {err}")
                if len(errors) > 10:
                    logger.warning(f"  ... and {len(errors) - 10} more")

        # Step 4: Save VETKA-JSON if requested
        if args.json:
            json_path = Path(args.json)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(vetka_json, f, indent=2)
            logger.info(f"Saved VETKA-JSON to: {json_path}")

        # Step 5: Render to HTML
        logger.info("-" * 60)
        logger.info("Rendering to HTML...")

        output_path = args.output or "output/vetka_tree.html"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        renderer = TreeRenderer()
        html = renderer.render(vetka_json, str(output_path))

        logger.info(f"Saved HTML to: {output_path}")

        # Step 6: Open in browser if requested
        if args.open:
            url = f"file://{output_path.absolute()}"
            logger.info(f"Opening in browser: {url}")
            webbrowser.open(url)

        # Summary
        logger.info("=" * 60)
        logger.info("VETKA Phase 11 Complete!")
        logger.info(f"  Nodes: {node_count}")
        logger.info(f"  Edges: {edge_count}")
        logger.info(f"  Output: {output_path}")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.debug)
        return 1


if __name__ == "__main__":
    sys.exit(main())
