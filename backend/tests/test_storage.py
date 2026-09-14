import hashlib
import io
from pathlib import Path

import pytest

from app.core.config import settings
from app.models.enums import IntegrityStatus
from app.services import storage


@pytest.fixture(autouse=True)
def storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "evidence_dir", str(tmp_path))
    return tmp_path


def store_bytes(data: bytes, content_type: str = "text/plain"):
    return storage.store(1, io.BytesIO(data), content_type)


def test_digest_matches_the_stored_bytes():
    data = b"The subject arrived at 10:30 PM."
    stored = store_bytes(data)

    assert stored.sha256 == hashlib.sha256(data).hexdigest()
    assert stored.size_bytes == len(data)
    assert Path(stored.storage_path).read_bytes() == data


def test_verify_detects_a_changed_file():
    stored = store_bytes(b"The subject arrived at 10:30 PM.")
    assert storage.verify(stored.storage_path, stored.sha256)[0] is IntegrityStatus.verified

    Path(stored.storage_path).write_bytes(b"The subject arrived at 8:00 PM.")
    status, computed = storage.verify(stored.storage_path, stored.sha256)

    assert status is IntegrityStatus.altered
    assert computed != stored.sha256


def test_verify_reports_a_deleted_file_rather_than_claiming_success():
    stored = store_bytes(b"evidence")
    Path(stored.storage_path).unlink()

    status, computed = storage.verify(stored.storage_path, stored.sha256)
    assert status is IntegrityStatus.missing_file
    assert computed is None


def test_executable_types_are_refused():
    with pytest.raises(storage.StorageError):
        store_bytes(b"MZ\x90\x00", "application/x-msdownload")


def test_oversized_file_is_refused_and_leaves_nothing_behind(storage_root, monkeypatch):
    monkeypatch.setattr(settings, "max_evidence_mb", 1)
    with pytest.raises(storage.StorageError):
        store_bytes(b"x" * (2 * 1024 * 1024))

    # A partially written file must not survive a rejected upload.
    assert list(storage_root.rglob("*.bin")) == []


def test_empty_file_is_refused():
    with pytest.raises(storage.StorageError):
        store_bytes(b"")


@pytest.mark.parametrize(
    "filename",
    ["../../etc/passwd", "..\\..\\windows\\system32\\cmd.exe", "/etc/shadow", "a/b/c.txt"],
)
def test_uploaded_filename_cannot_walk_out_of_storage(filename):
    """The stored path is generated, never taken from the upload."""
    safe = storage.safe_display_name(filename)
    assert "/" not in safe and "\\" not in safe and ".." not in safe


def test_stored_file_stays_under_the_configured_root(storage_root):
    stored = store_bytes(b"evidence")
    assert Path(stored.storage_path).resolve().is_relative_to(storage_root.resolve())


def test_two_identical_files_get_separate_paths_and_the_same_digest():
    first = store_bytes(b"identical evidence")
    second = store_bytes(b"identical evidence")

    assert first.storage_path != second.storage_path
    assert first.sha256 == second.sha256
