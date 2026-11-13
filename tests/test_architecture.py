"""分层守卫：依赖方向与文件规模。"""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "a_share_brief"

# 只允许向内依赖：domain ← application ← infrastructure / interfaces
FORBIDDEN = {
    "domain": ("application", "infrastructure", "interfaces"),
    "application": ("infrastructure", "interfaces"),
    "infrastructure": ("interfaces",),
}

MAX_SRC_LINES = 160
MAX_SERVICE_LINES = 120


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
        elif isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
    return out


def test_dependency_direction():
    violations = []
    for layer, banned in FORBIDDEN.items():
        for py in (SRC / layer).rglob("*.py"):
            for mod in _imports(py):
                for bad in banned:
                    if f"a_share_brief.{bad}" in mod:
                        violations.append(f"{py.relative_to(SRC)} -> {mod}")
    assert not violations, "依赖方向违规: " + "; ".join(violations)


def test_source_files_stay_small():
    offenders = []
    for py in SRC.rglob("*.py"):
        lines = len(py.read_text(encoding="utf-8").splitlines())
        limit = MAX_SERVICE_LINES if "domain/services" in str(py) else MAX_SRC_LINES
        if lines > limit:
            offenders.append(f"{py.relative_to(SRC)}={lines}>{limit}")
    assert not offenders, "文件过大，需拆分: " + "; ".join(offenders)


def test_domain_and_services_are_pure():
    banned = ("requests", "httpx", "urllib", "socket", "psycopg", "redis", "logging")
    violations = []
    for sub in ("domain/aggregates", "domain/services"):
        for py in (SRC / sub).rglob("*.py"):
            src = py.read_text(encoding="utf-8")
            for word in banned:
                if word in src:
                    violations.append(f"{py.relative_to(SRC)} -> {word}")
    assert not violations, "领域层出现 IO 依赖: " + "; ".join(violations)
