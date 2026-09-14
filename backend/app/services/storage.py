"""Evidence file storage, hashing and integrity verification.

Files are written under a per-case directory with a generated name. The name the
investigator uploaded is kept in the database only - it is never used as a path, so a
filename like `../../etc/passwd` cannot escape the storage root.
"""

import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.models.enums import IntegrityStatus

CHUNK = 1024 * 1024

# Types that can be stored. Anything executable is refused outright: evidence is
# something to read, never something to run.
ALLOWED_CONTENT_TYPES = {
    "text/plain",
    "text/csv",
    "text/markdown",
    "application/json",
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "video/mp4",
}

# Types whose bytes are text the engine can actually compare against statements.
TEXT_CONTENT_TYPES = {"text/plain", "text/csv", "text/markdown", "application/json"}

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")


class StorageError(Exception):
    pass


@dataclass(frozen=True)
class StoredFile:
    storage_path: str
    sha256: str
    size_bytes: int


def safe_display_name(filename: str) -> str:
    """Keep a readable name for display, stripped of anything path-like."""
    cleaned = _SAFE_NAME.sub("_", Path(filename).name).strip("._")
    return cleaned[:255] or "unnamed"


def _case_dir(case_id: int) -> Path:
    path = Path(settings.evidence_dir) / f"case_{case_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def store(case_id: int, source, content_type: str) -> StoredFile:
    """Stream `source` to disk, hashing as it goes.

    Hashing during the write means the digest describes the bytes that were actually
    stored - not a separate read that could differ.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise StorageError(f"Unsupported file type: {content_type}")

    limit = settings.max_evidence_mb * 1024 * 1024
    target = _case_dir(case_id) / f"{uuid.uuid4().hex}.bin"
    digest = hashlib.sha256()
    size = 0

    try:
        with target.open("wb") as out:
            while chunk := source.read(CHUNK):
                size += len(chunk)
                if size > limit:
                    raise StorageError(f"File exceeds the {settings.max_evidence_mb} MB limit")
                digest.update(chunk)
                out.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise

    if size == 0:
        target.unlink(missing_ok=True)
        raise StorageError("File is empty")

    return StoredFile(str(target), digest.hexdigest(), size)


def digest_of(storage_path: str) -> str | None:
    path = Path(storage_path)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def verify(storage_path: str, expected_sha256: str) -> tuple[IntegrityStatus, str | None]:
    """Recompute the digest and compare it with the one recorded at upload.

    `verified` means the stored bytes are unchanged since upload. It does not mean the
    file's contents are accurate, nor that the file was authentic when it arrived.
    """
    actual = digest_of(storage_path)
    if actual is None:
        return IntegrityStatus.missing_file, None
    if actual != expected_sha256:
        return IntegrityStatus.altered, actual
    return IntegrityStatus.verified, actual


def read_text(storage_path: str) -> str:
    return Path(storage_path).read_text(encoding="utf-8", errors="replace")
