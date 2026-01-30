# ========================================
# MARKER: Phase 72.2 Test Fixture
# File: tests/scanners/fixtures/python/absolute_imports.py
# Purpose: Test standard library + third-party imports
# ========================================
"""
Test fixture: Absolute imports (stdlib + third-party).

From VETKA audit:
- 1,156 absolute imports total
- Most common: os, sys, json, typing, pathlib
"""

# Standard library imports
import os
import sys
import json
import logging
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from io import StringIO

# These would be third-party in real project (here just for pattern testing)
# import httpx
# import requests
# import numpy as np
# from PIL import Image
# from bs4 import BeautifulSoup

# Usage to make linters happy
_ = (os, sys, json, logging, subprocess, Dict, List, Optional, Any, Tuple,
     Path, datetime, Enum, auto, dataclass, field, asdict, ABC, abstractmethod,
     defaultdict, deque, ThreadPoolExecutor, StringIO)
