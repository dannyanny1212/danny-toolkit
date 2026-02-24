"""
Security Scanners — Audit patronen en RAG zoektermen.

Constanten-only bestand. Scan-methoden blijven in engine.py.
"""

from danny_toolkit.brain.security.config import Ernst


# Code audit patronen (uitgebreid van SentinelValidator)
AUDIT_PATRONEN = [
    (Ernst.KRITIEK, "private_key",
     r"(?i)(private[_\s]?key|secret[_\s]?key|seed[_\s]?"
     r"phrase)\s*[=:]\s*['\"][^'\"]{10,}"),
    (Ernst.KRITIEK, "hardcoded_api_key",
     r"(?i)(api[_\s]?key|token|bearer)\s*[=:]\s*"
     r"['\"][A-Za-z0-9_\-]{20,}['\"]"),
    (Ernst.HOOG, "eval_exec",
     r"\b(eval|exec)\s*\("),
    (Ernst.HOOG, "shell_true",
     r"subprocess\.(?:call|run|Popen)\s*\("
     r".*shell\s*=\s*True"),
    (Ernst.HOOG, "os_system",
     r"\bos\.system\s*\("),
    (Ernst.MEDIUM, "http_url",
     r"['\"]http://[^'\"]+['\"]"),
    (Ernst.MEDIUM, "rm_rf",
     r"\brm\s+-rf\b"),
    (Ernst.MEDIUM, "shutil_rmtree",
     r"\bshutil\.rmtree\s*\("),
    (Ernst.LAAG, "import_dunder",
     r"\b__import__\s*\("),
    (Ernst.LAAG, "open_write",
     r"\bopen\s*\(.*['\"]w['\"]\s*\)"),
    # v2.0 — forensische patronen
    (Ernst.KRITIEK, "hardcoded_wallet",
     r"0x[a-fA-F0-9]{40}"),
    (Ernst.KRITIEK, "base64_secret",
     r"base64\.(b64)?decode\s*\("),
    (Ernst.HOOG, "c2_callback",
     r"requests\.(get|post)\s*\(.*"
     r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
    (Ernst.HOOG, "reverse_shell",
     r"socket\.socket\s*\(.*SOCK_STREAM"),
    (Ernst.HOOG, "crypto_mining",
     r"(stratum|mining[_\-]?pool|hashrate)"),
    (Ernst.MEDIUM, "dns_exfil",
     r"socket\.gethost(byname|name)\s*\("),
    (Ernst.MEDIUM, "pickle_load",
     r"pickle\.loads?\s*\("),
    (Ernst.LAAG, "temp_file_write",
     r"tempfile\.(Named)?Temp"),
]

# RAG zoektermen
RAG_ZOEKTERMEN = [
    "CVE", "exploit", "hack", "vulnerability",
    "kwetsbaarheid", "aanval", "breach", "malware",
]
