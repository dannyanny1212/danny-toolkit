"""
Tests voor MRL truncatie in de embedding pipeline.
11 tests — standalone script (project conventie).
"""

import io
import math
import os
import sys
import hashlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Zorg dat project root op sys.path staat
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

passed = 0
failed = 0


def check(naam, voorwaarde, detail=""):
    global passed, failed
    if voorwaarde:
        passed += 1
        print(f"  [OK] {naam}")
    else:
        failed += 1
        print(f"  [FAIL] {naam}  {detail}")


# ── Test 1: mrl_truncate trunceert naar juiste dimensie ──
print("\n=== Test 1: mrl_truncate dimensie ===")
from danny_toolkit.core.embeddings import mrl_truncate

vecs = [[float(i) for i in range(1024)] for _ in range(3)]
out = mrl_truncate(vecs, 256)
check("output heeft 3 vectoren", len(out) == 3)
check("elke vector is 256d", all(len(v) == 256 for v in out))

# ── Test 2: Output is L2 genormaliseerd ──
print("\n=== Test 2: L2 normalisatie ===")
for i, v in enumerate(out):
    norm = math.sqrt(sum(x ** 2 for x in v))
    check(f"vector {i} norm ~1.0", abs(norm - 1.0) < 1e-6, f"got {norm}")

# ── Test 3: Noop als dim >= huidige dim ──
print("\n=== Test 3: Noop bij dim >= input dim ===")
small = [[1.0, 2.0, 3.0]]
out_noop = mrl_truncate(small, 3)
check("dim==input: ongewijzigd", out_noop == small)
out_noop2 = mrl_truncate(small, 999)
check("dim>input: ongewijzigd", out_noop2 == small)

# ── Test 4: Lege input → lege output ──
print("\n=== Test 4: Lege input ===")
check("lege lijst -> lege lijst", mrl_truncate([], 256) == [])

# ── Test 5: Nulvector crasht niet ──
print("\n=== Test 5: Nulvector ===")
zero_vec = [[0.0] * 1024]
try:
    out_zero = mrl_truncate(zero_vec, 256)
    check("geen ZeroDivisionError", True)
    check("output is 256d", len(out_zero[0]) == 256)
except ZeroDivisionError:
    check("geen ZeroDivisionError", False, "ZeroDivisionError raised")

# ── Test 6: Pure Python fallback produceert zelfde resultaat ──
print("\n=== Test 6: Numpy vs pure Python ===")
test_vecs = [[float(i + j * 0.1) for i in range(512)] for j in range(2)]

# Force numpy path
try:
    import numpy as np
    _has_numpy = True
except ImportError:
    _has_numpy = False

if _has_numpy:
    np_result = mrl_truncate(test_vecs, 128)

    # Pure Python path
    py_result = []
    for vec in test_vecs:
        trunc = vec[:128]
        norm = math.sqrt(sum(v ** 2 for v in trunc))
        if norm > 0:
            trunc = [v / norm for v in trunc]
        py_result.append(trunc)

    max_diff = max(
        abs(a - b)
        for v1, v2 in zip(np_result, py_result)
        for a, b in zip(v1, v2)
    )
    check("numpy vs python max diff < 1e-10", max_diff < 1e-10, f"diff={max_diff}")
else:
    check("numpy vs python (numpy not installed, skip)", True)

# ── Test 7: Config.EMBEDDING_DIM default == 256 ──
print("\n=== Test 7: Config.EMBEDDING_DIM ===")
from danny_toolkit.core.config import Config
check("EMBEDDING_DIM == 256", Config.EMBEDDING_DIM == 256, f"got {Config.EMBEDDING_DIM}")

# ── Test 8: Config.VOYAGE_NATIVE_DIM == 1024 ──
print("\n=== Test 8: Config.VOYAGE_NATIVE_DIM ===")
check("VOYAGE_NATIVE_DIM == 1024", Config.VOYAGE_NATIVE_DIM == 1024, f"got {Config.VOYAGE_NATIVE_DIM}")

# ── Test 9: Cache key verschilt per dimensie ──
print("\n=== Test 9: Cache key dimensie-afhankelijk ===")
from danny_toolkit.core.embeddings import EmbeddingCache

cache = EmbeddingCache.__new__(EmbeddingCache)

tekst = "test tekst voor hashing"
provider = "voyage"

# Simuleer hash met dim 256
content_256 = f"{provider}:256:{tekst}"
hash_256 = hashlib.sha256(content_256.encode()).hexdigest()

# Simuleer hash met dim 1024
content_1024 = f"{provider}:1024:{tekst}"
hash_1024 = hashlib.sha256(content_1024.encode()).hexdigest()

check("hash verschilt bij andere dimensie", hash_256 != hash_1024)

# Verifieer dat de echte _hash_tekst de dim bevat
cache_real = EmbeddingCache.__new__(EmbeddingCache)
real_hash = cache_real._hash_tekst(tekst, provider)
expected = hashlib.sha256(f"{provider}:{Config.EMBEDDING_DIM}:{tekst}".encode()).hexdigest()
check("_hash_tekst bevat Config.EMBEDDING_DIM", real_hash == expected)

# ── Test 10: VoyageEmbeddings.dimensies == Config.EMBEDDING_DIM ──
print("\n=== Test 10: VoyageEmbeddings.dimensies ===")
from unittest.mock import MagicMock
import importlib

# Mock voyageai zodat we geen echte API key nodig hebben
mock_voyageai = MagicMock()
sys.modules["voyageai"] = mock_voyageai

try:
    from danny_toolkit.core.embeddings import VoyageEmbeddings
    ve = VoyageEmbeddings(api_key="fake-key")
    check("VoyageEmbeddings.dimensies == EMBEDDING_DIM",
          ve.dimensies == Config.EMBEDDING_DIM,
          f"got {ve.dimensies}")
except Exception as e:
    check("VoyageEmbeddings.dimensies == EMBEDDING_DIM", False, str(e))

# ── Test 11: VoyageChromaEmbedding._target_dim == Config.EMBEDDING_DIM ──
print("\n=== Test 11: VoyageChromaEmbedding._target_dim ===")
try:
    from danny_toolkit.core.embeddings import VoyageChromaEmbedding
    vce = VoyageChromaEmbedding()
    check("VoyageChromaEmbedding._target_dim == EMBEDDING_DIM",
          vce._target_dim == Config.EMBEDDING_DIM,
          f"got {vce._target_dim}")
except Exception as e:
    check("VoyageChromaEmbedding._target_dim == EMBEDDING_DIM", False, str(e))
finally:
    # Cleanup mock
    del sys.modules["voyageai"]

# ── Resultaat ──
print(f"\n{'=' * 50}")
totaal = passed + failed
print(f"  MRL Truncation Tests: {passed}/{totaal} passed")
if failed:
    print(f"  {failed} FAILED")
else:
    print(f"  ALL PASSED")
print(f"{'=' * 50}")

sys.exit(0 if failed == 0 else 1)
