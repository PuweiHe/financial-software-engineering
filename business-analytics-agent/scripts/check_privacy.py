"""Scan publishable files without printing matched private values."""
from pathlib import Path
import ast
import ipaddress
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", "test-results", ".ruff_cache", ".mypy_cache"}
patterns = {
    "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "literal provider key": r"\bsk-[A-Za-z0-9_-]{16,}",
    "personal home path": r"/(?:Users|home)/[A-Za-z0-9_.-]+/",
    "credential URL": r"[a-z]+://[^\s/:]+:[^\s/@]+@",
}

def inspect():
    findings = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP for part in path.relative_to(ROOT).parts) or path == Path(__file__).resolve():
            continue
        rel = str(path.relative_to(ROOT))
        if path.name == ".env" or path.suffix in {".log", ".pem", ".key", ".xlsx", ".xls", ".chm", ".zip"}:
            findings.append((rel, "excluded file type"))
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            findings.append((rel, "unreviewed binary"))
            continue
        for label, pattern in patterns.items():
            if re.search(pattern, text): findings.append((rel, label))
        for value in re.findall(r"[\w.+-]+@([\w.-]+\.[A-Za-z]{2,})", text):
            if value not in {"example.invalid", "example.com"}: findings.append((rel, "email address"))
        for value in re.findall(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])", text):
            try:
                address = ipaddress.ip_address(value)
            except ValueError:
                continue
            if not address.is_loopback and not address.is_unspecified:
                findings.append((rel, "nonlocal IP address"))
        if path.suffix == ".py":
            try: ast.parse(text)
            except SyntaxError: findings.append((rel, "Python syntax error"))
    return sorted(set(findings))

if __name__ == "__main__":
    findings = inspect()
    for path, category in findings:
        print(f"{path}: {category}")
    print(f"Privacy pattern findings: {len(findings)}")
    sys.exit(bool(findings))
