# ========================================
# MARKER: Phase 72.3 Python Scanner
# Date: 2026-01-19
# File: src/scanners/known_packages.py
# Purpose: Centralized known external packages registry
# Extracted from: import_resolver.py COMMON_THIRD_PARTY
# ========================================
"""
Known external packages registry for VETKA dependency scanning.

This module centralizes the knowledge of external packages (stdlib + third-party)
to avoid duplication across different scanners (Python, JS/TS in future).

Usage:
    from src.scanners.known_packages import (
        PYTHON_STDLIB,
        PYTHON_THIRD_PARTY,
        get_all_external_python,
    )

@status: active
@phase: 96
@depends: sys
@used_by: import_resolver, python_scanner
"""

import sys
from typing import FrozenSet, Set


def _get_stdlib_modules() -> FrozenSet[str]:
    """
    Get Python standard library module names.

    Uses sys.stdlib_module_names on Python 3.10+,
    falls back to hardcoded list for older versions.
    """
    if hasattr(sys, 'stdlib_module_names'):
        return frozenset(sys.stdlib_module_names)

    # Fallback for Python < 3.10
    return frozenset({
        'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio',
        'asyncore', 'atexit', 'audioop', 'base64', 'bdb', 'binascii',
        'binhex', 'bisect', 'builtins', 'bz2', 'calendar', 'cgi', 'cgitb',
        'chunk', 'cmath', 'cmd', 'code', 'codecs', 'codeop', 'collections',
        'colorsys', 'compileall', 'concurrent', 'configparser', 'contextlib',
        'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt', 'csv',
        'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm', 'decimal',
        'difflib', 'dis', 'distutils', 'doctest', 'email', 'encodings',
        'enum', 'errno', 'faulthandler', 'fcntl', 'filecmp', 'fileinput',
        'fnmatch', 'fractions', 'ftplib', 'functools', 'gc', 'getopt',
        'getpass', 'gettext', 'glob', 'graphlib', 'grp', 'gzip', 'hashlib',
        'heapq', 'hmac', 'html', 'http', 'idlelib', 'imaplib', 'imghdr',
        'imp', 'importlib', 'inspect', 'io', 'ipaddress', 'itertools',
        'json', 'keyword', 'lib2to3', 'linecache', 'locale', 'logging',
        'lzma', 'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes',
        'mmap', 'modulefinder', 'multiprocessing', 'netrc', 'nis',
        'nntplib', 'numbers', 'operator', 'optparse', 'os', 'ossaudiodev',
        'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil',
        'platform', 'plistlib', 'poplib', 'posix', 'posixpath', 'pprint',
        'profile', 'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr',
        'pydoc', 'queue', 'quopri', 'random', 're', 'readline', 'reprlib',
        'resource', 'rlcompleter', 'runpy', 'sched', 'secrets', 'select',
        'selectors', 'shelve', 'shlex', 'shutil', 'signal', 'site',
        'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver', 'spwd',
        'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep',
        'struct', 'subprocess', 'sunau', 'symtable', 'sys', 'sysconfig',
        'syslog', 'tabnanny', 'tarfile', 'telnetlib', 'tempfile',
        'termios', 'test', 'textwrap', 'threading', 'time', 'timeit',
        'tkinter', 'token', 'tokenize', 'trace', 'traceback', 'tracemalloc',
        'tty', 'turtle', 'turtledemo', 'types', 'typing', 'typing_extensions',
        'unicodedata', 'unittest', 'urllib', 'uu', 'uuid', 'venv',
        'warnings', 'wave', 'weakref', 'webbrowser', 'winreg', 'winsound',
        'wsgiref', 'xdrlib', 'xml', 'xmlrpc', 'zipapp', 'zipfile',
        'zipimport', 'zlib',
    })


# Python standard library modules
PYTHON_STDLIB: FrozenSet[str] = _get_stdlib_modules()


# Common third-party Python packages
# Organized by category for maintainability
PYTHON_THIRD_PARTY: FrozenSet[str] = frozenset({
    # === Data Science / ML ===
    'numpy', 'pandas', 'scipy', 'matplotlib', 'seaborn', 'plotly',
    'sklearn', 'scikit-learn', 'tensorflow', 'torch', 'keras',
    'xgboost', 'lightgbm', 'catboost', 'statsmodels',

    # === NLP / AI ===
    'nltk', 'spacy', 'transformers', 'huggingface_hub',
    'langchain', 'langchain_core', 'langchain_community',
    'langgraph', 'openai', 'anthropic', 'ollama', 'litellm',
    'autogen', 'composio', 'crewai',

    # === Vector DBs ===
    'chromadb', 'qdrant_client', 'pinecone', 'weaviate', 'milvus',
    'faiss', 'annoy', 'lancedb',

    # === Dimensionality Reduction / Clustering ===
    'umap', 'hdbscan', 'tsne',

    # === Web Frameworks ===
    'flask', 'django', 'fastapi', 'starlette', 'quart', 'sanic',
    'tornado', 'bottle', 'pyramid', 'aiohttp',

    # === HTTP Clients ===
    'requests', 'httpx', 'httpcore', 'urllib3', 'aiohttp',

    # === ASGI / Servers ===
    'uvicorn', 'gunicorn', 'hypercorn', 'daphne',

    # === Async ===
    'asyncio', 'anyio', 'trio', 'curio',

    # === Database ===
    'sqlalchemy', 'alembic', 'pymongo', 'motor', 'redis',
    'asyncpg', 'aiosqlite', 'psycopg2', 'mysql-connector',
    'peewee', 'tortoise-orm', 'databases',

    # === Task Queues ===
    'celery', 'rq', 'dramatiq', 'arq',

    # === Validation / Serialization ===
    'pydantic', 'marshmallow', 'attrs', 'cattrs',

    # === CLI ===
    'click', 'typer', 'argparse', 'fire', 'rich', 'tqdm',

    # === Testing ===
    'pytest', 'pytest_asyncio', 'pytest_cov', 'unittest', 'mock',
    'hypothesis', 'faker', 'factory_boy', 'responses', 'httpretty',

    # === Linting / Formatting ===
    'black', 'ruff', 'mypy', 'pylint', 'flake8', 'isort', 'autopep8',
    'pyright', 'bandit', 'safety',

    # === Image Processing ===
    'pillow', 'PIL', 'cv2', 'opencv', 'opencv-python', 'imageio',
    'scikit-image',

    # === Web Scraping ===
    'bs4', 'beautifulsoup4', 'lxml', 'scrapy', 'selenium',
    'playwright', 'pyppeteer',

    # === Config / Env ===
    'yaml', 'pyyaml', 'toml', 'tomli', 'tomllib', 'dotenv',
    'python-dotenv', 'dynaconf', 'hydra', 'omegaconf',

    # === File Watching ===
    'watchdog', 'watchfiles', 'inotify',

    # === System / Process ===
    'psutil', 'sh', 'plumbum', 'pexpect',

    # === Cloud / AWS ===
    'boto3', 'botocore', 'aiobotocore', 's3fs',

    # === Cloud / GCP ===
    'google', 'google-cloud', 'google-auth', 'google-api-python-client',

    # === Cloud / Azure ===
    'azure', 'azure-storage', 'azure-identity',

    # === SSH / Remote ===
    'paramiko', 'fabric', 'invoke',

    # === WebSocket ===
    'websocket', 'websockets', 'socketio', 'python-socketio',

    # === GraphQL ===
    'graphql', 'graphene', 'ariadne', 'strawberry',

    # === Logging ===
    'loguru', 'structlog',

    # === Crypto ===
    'cryptography', 'pycryptodome', 'nacl', 'bcrypt', 'passlib',

    # === Date / Time ===
    'arrow', 'pendulum', 'dateutil', 'python-dateutil', 'pytz',

    # === Misc ===
    'orjson', 'ujson', 'msgpack', 'cachetools', 'diskcache',
    'tenacity', 'backoff', 'retry', 'more-itertools',
    'toolz', 'cytoolz', 'funcy', 'boltons',
    'jinja2', 'mako', 'chevron',
    'packaging', 'setuptools', 'wheel', 'pip', 'poetry',
    'docutils', 'sphinx', 'mkdocs',
})


def get_all_external_python() -> Set[str]:
    """
    Get combined set of all external Python packages.

    Returns:
        Set of all known external package names (stdlib + third-party)
    """
    return set(PYTHON_STDLIB) | set(PYTHON_THIRD_PARTY)


def is_external_package(package_name: str) -> bool:
    """
    Check if a package name is external (stdlib or known third-party).

    Args:
        package_name: Base package name (e.g., 'numpy' not 'numpy.array')

    Returns:
        True if package is external, False otherwise
    """
    base = package_name.split('.')[0]
    return base in PYTHON_STDLIB or base in PYTHON_THIRD_PARTY


# === Future: JavaScript/TypeScript packages ===
# Uncomment when implementing JS/TS scanner

# JS_BUILTIN: FrozenSet[str] = frozenset({
#     'fs', 'path', 'os', 'crypto', 'http', 'https', 'url', 'util',
#     'stream', 'buffer', 'events', 'child_process', 'cluster',
#     'dgram', 'dns', 'net', 'readline', 'repl', 'tls', 'tty',
#     'v8', 'vm', 'zlib', 'assert', 'console', 'process', 'timers',
# })
#
# JS_THIRD_PARTY: FrozenSet[str] = frozenset({
#     'react', 'react-dom', 'next', 'vue', 'angular', 'svelte',
#     'express', 'fastify', 'koa', 'hapi', 'nest',
#     'axios', 'fetch', 'got', 'node-fetch',
#     'lodash', 'underscore', 'ramda',
#     'moment', 'dayjs', 'date-fns', 'luxon',
#     'jest', 'mocha', 'chai', 'vitest', 'cypress', 'playwright',
#     'webpack', 'vite', 'rollup', 'esbuild', 'parcel',
#     'typescript', 'babel', 'eslint', 'prettier',
#     'three', '@react-three/fiber', '@react-three/drei',
#     'socket.io', 'socket.io-client', 'ws',
#     'zustand', 'redux', 'mobx', 'recoil', 'jotai',
#     'tailwindcss', 'styled-components', 'emotion',
#     'lucide-react', 'heroicons', 'phosphor-react',
# })
