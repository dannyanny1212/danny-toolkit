"""
ENV VAULT — Versleutelde opslag voor .env secrets.

Gebruikt Windows DPAPI (Data Protection API) om het .env bestand
te versleutelen. Alleen het huidige Windows user account kan de
data ontsleutelen — geen master password nodig.

Workflow:
    1. seal()   — Leest .env, versleutelt naar .env.vault, verwijdert .env
    2. unseal() — Ontsleutelt .env.vault naar geheugen, injecteert in os.environ
    3. rotate() — Unseal + reseal (voor key updates)

De plaintext .env bestaat alleen tijdens bewerking.
In productie draait het systeem uitsluitend op de vault.

Gebruik:
    from danny_toolkit.core.env_vault import seal_env, unseal_env

    # Eenmalig: versleutel .env
    seal_env()

    # Bij elke boot: laad secrets in geheugen
    unseal_env()
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import os
import struct
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
_VAULT_FILE = _PROJECT_ROOT / "data" / ".env.vault"

# ── Windows DPAPI bindings ──

_crypt32 = ctypes.windll.crypt32
_kernel32 = ctypes.windll.kernel32


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _dpapi_encrypt(plaintext: bytes) -> bytes:
    """Versleutel bytes met Windows DPAPI (user scope)."""
    blob_in = _DATA_BLOB(
        len(plaintext),
        ctypes.cast(
            ctypes.create_string_buffer(plaintext, len(plaintext)),
            ctypes.POINTER(ctypes.c_char),
        ),
    )
    blob_out = _DATA_BLOB()

    # CryptProtectData — versleutelt met user credentials
    success = _crypt32.CryptProtectData(
        ctypes.byref(blob_in),    # pDataIn
        "DannyToolkitEnvVault",    # szDataDescr (UTF-16)
        None,                      # pOptionalEntropy
        None,                      # pvReserved
        None,                      # pPromptStruct
        0x01,                      # dwFlags: CRYPTPROTECT_UI_FORBIDDEN
        ctypes.byref(blob_out),    # pDataOut
    )
    if not success:
        raise OSError(
            f"DPAPI encrypt failed: {ctypes.get_last_error()}"
        )

    encrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    _kernel32.LocalFree(blob_out.pbData)
    return encrypted


def _dpapi_decrypt(ciphertext: bytes) -> bytes:
    """Ontsleutel bytes met Windows DPAPI (user scope)."""
    blob_in = _DATA_BLOB(
        len(ciphertext),
        ctypes.cast(
            ctypes.create_string_buffer(ciphertext, len(ciphertext)),
            ctypes.POINTER(ctypes.c_char),
        ),
    )
    blob_out = _DATA_BLOB()

    success = _crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),    # pDataIn
        None,                      # ppszDataDescr
        None,                      # pOptionalEntropy
        None,                      # pvReserved
        None,                      # pPromptStruct
        0x01,                      # dwFlags: CRYPTPROTECT_UI_FORBIDDEN
        ctypes.byref(blob_out),    # pDataOut
    )
    if not success:
        raise OSError(
            f"DPAPI decrypt failed: {ctypes.get_last_error()}. "
            "Verkeerd user account of corrupte vault."
        )

    decrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    _kernel32.LocalFree(blob_out.pbData)
    return decrypted


# ── Vault header voor integriteitscontrole ──
_VAULT_MAGIC = b"DTVAULT1"  # Danny Toolkit Vault v1


def seal_env() -> Path:
    """Versleutel .env naar .env.vault en verwijder plaintext.

    Returns:
        Pad naar het vault-bestand.

    Raises:
        FileNotFoundError: Als .env niet bestaat.
    """
    if not _ENV_FILE.exists():
        raise FileNotFoundError(
            f".env niet gevonden: {_ENV_FILE}"
        )

    plaintext = _ENV_FILE.read_bytes()
    encrypted = _dpapi_encrypt(plaintext)

    # Schrijf vault: magic + length + ciphertext
    _VAULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_VAULT_FILE, "wb") as f:
        f.write(_VAULT_MAGIC)
        f.write(struct.pack("<I", len(encrypted)))
        f.write(encrypted)

    # Verwijder plaintext .env
    _ENV_FILE.unlink()

    logger.info(
        "ENV VAULT: .env versleuteld naar %s "
        "(%d bytes → %d bytes encrypted). "
        "Plaintext .env verwijderd.",
        _VAULT_FILE, len(plaintext), len(encrypted),
    )
    return _VAULT_FILE


def unseal_env() -> int:
    """Ontsleutel .env.vault en injecteer in os.environ.

    Laadt NIET naar een bestand — secrets bestaan alleen
    in process memory.

    Returns:
        Aantal geladen environment variables.

    Raises:
        FileNotFoundError: Als .env.vault niet bestaat.
        OSError: Als DPAPI decrypt faalt (verkeerd account).
    """
    if not _VAULT_FILE.exists():
        # Geen vault — probeer plain .env als fallback
        if _ENV_FILE.exists():
            logger.warning(
                "ENV VAULT: geen vault gevonden, "
                "gebruik plaintext .env. "
                "Run seal_env() om te beveiligen."
            )
            return _load_dotenv_plain()
        raise FileNotFoundError(
            f"Geen vault ({_VAULT_FILE}) en geen .env "
            f"({_ENV_FILE}) gevonden."
        )

    with open(_VAULT_FILE, "rb") as f:
        magic = f.read(len(_VAULT_MAGIC))
        if magic != _VAULT_MAGIC:
            raise ValueError(
                "Corrupt vault: ongeldige header"
            )
        (length,) = struct.unpack("<I", f.read(4))
        ciphertext = f.read(length)

    plaintext = _dpapi_decrypt(ciphertext)

    # Parse .env format en injecteer in os.environ
    count = 0
    for line in plaintext.decode("utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
            count += 1

    logger.info(
        "ENV VAULT: %d secrets geladen in os.environ "
        "(alleen in geheugen, geen disk).",
        count,
    )
    return count


def _load_dotenv_plain() -> int:
    """Fallback: laad plain .env."""
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_FILE, override=False)
        return -1  # unknown count
    except ImportError:
        count = 0
        for line in _ENV_FILE.read_text("utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
                count += 1
        return count


def rotate_env() -> Path:
    """Unseal → exporteer naar temp .env → seal opnieuw.

    Gebruik dit na het toevoegen/wijzigen van keys.
    """
    if _VAULT_FILE.exists():
        # Ontsleutel naar .env
        with open(_VAULT_FILE, "rb") as f:
            magic = f.read(len(_VAULT_MAGIC))
            if magic != _VAULT_MAGIC:
                raise ValueError("Corrupt vault")
            (length,) = struct.unpack("<I", f.read(4))
            ciphertext = f.read(length)
        plaintext = _dpapi_decrypt(ciphertext)
        _ENV_FILE.write_bytes(plaintext)
        _VAULT_FILE.unlink()
        logger.info(
            "ENV VAULT: vault ontsleuteld naar .env "
            "voor bewerking."
        )

    if not _ENV_FILE.exists():
        raise FileNotFoundError("Geen .env om te roteren")

    print(
        f"[ENV VAULT] .env is nu beschikbaar voor bewerking: "
        f"{_ENV_FILE}\n"
        f"Bewerk je keys en run seal_env() als je klaar bent."
    )
    return _ENV_FILE
