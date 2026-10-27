"""Meta-only enforcement: fail if competitor SDKs or banned frameworks appear.

Mirrors `.github/workflows/secret-scan.yml` (meta-only step) and the Makefile
`verify-meta-only` target so the rule is checked locally, not just in CI.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]

BANNED_IMPORTS = (
    "import openai",
    "from openai",
    "import anthropic",
    "from anthropic",
    "import cohere",
    "from cohere",
)
# requirements.txt package names (lowercase, no extras/markers/versions).
BANNED_DEPS = ("openai", "anthropic", "cohere")
# ANTI_PROJECT_COMPLIANCE.md checklist: no Streamlit, no vector-DB/RAG libs.
BANNED_FRAMEWORKS = ("streamlit", "chromadb", "faiss-cpu", "faiss-gpu", "pinecone")


# This guard file contains the banned strings as test data by construction,
# so it is excluded from its own scan. tests/ is otherwise scanned: AGENTS.md
# §10 bans competitor SDKs "even for quick test".
_GUARD_FILE = "test_no_openai.py"


def _python_files() -> list[pathlib.Path]:
    app = ROOT / "app"
    tests = ROOT / "tests"
    files: list[pathlib.Path] = []
    if app.exists():
        files.extend(sorted(app.rglob("*.py")))
    if tests.exists():
        files.extend(sorted(tests.rglob("*.py")))
    return [f for f in files if f.name != _GUARD_FILE]


def _offending_files(snippets: tuple[str, ...]) -> list[str]:
    offenders = []
    for path in _python_files():
        text = path.read_text(encoding="utf-8")
        if any(s in text for s in snippets):
            offenders.append(str(path.relative_to(ROOT)))
    return offenders


def test_no_banned_imports() -> None:
    offenders = _offending_files(BANNED_IMPORTS)
    assert not offenders, f"competitor SDK import in: {offenders}"


def test_no_banned_frameworks() -> None:
    offenders = _offending_files(BANNED_FRAMEWORKS)
    assert not offenders, f"banned framework import in: {offenders}"


def _required_packages() -> dict[str, list[str]]:
    """Map requirements file -> cleaned package names (no comments/options)."""
    found: dict[str, list[str]] = {}
    for name in ("requirements.txt", "requirements-dev.txt"):
        path = ROOT / name
        if not path.exists():
            continue
        packages = []
        for line in path.read_text(encoding="utf-8").splitlines():
            spec = line.split("#", 1)[0].strip()
            if not spec or spec.startswith("-"):
                continue
            pkg = re.split(r"[<>=!;\s\[]", spec, 1)[0].strip().lower()
            if pkg:
                packages.append(pkg)
        found[name] = packages
    return found


def test_no_banned_dependencies() -> None:
    offenders = []
    for name, packages in _required_packages().items():
        for pkg in packages:
            if pkg in BANNED_DEPS or pkg in BANNED_FRAMEWORKS:
                offenders.append(f"{name}: {pkg}")
    assert not offenders, f"banned dependency: {offenders}"
