"""Tests for atomic, locked connections-file storage (v1.4 H4)."""

import os

import pytest

from app.services.connection_storage import ConnectionStorageService


@pytest.fixture
def storage(tmp_path):
    return ConnectionStorageService(str(tmp_path / "connections.enc"))


def _conn(name: str) -> dict:
    return {
        "name": name,
        "db_type": "oracle",
        "host": "db.example.com",
        "port": 1521,
        "username": "scott",
        "password": "tiger",
    }


class TestAtomicWrite:
    def test_write_replaces_file_atomically(self, storage):
        storage.create_connection(_conn("one"))
        assert storage.file_path.exists()
        # No temp leftovers
        leftovers = [p for p in storage.file_path.parent.iterdir() if p.suffix == ".tmp"]
        assert leftovers == []

    def test_no_truncated_store_on_crash(self, storage, monkeypatch):
        """A failure AFTER the temp file is created but BEFORE os.replace()
        leaves the old store intact and removes the temp file."""
        storage.create_connection(_conn("survivor"))

        real_replace = os.replace

        def exploding_replace(src, dst):
            # Temp file exists at this point; simulate a crash before rename.
            raise RuntimeError("simulated crash before replace")

        monkeypatch.setattr("app.services.connection_storage.os.replace", exploding_replace)
        # _write_file wraps the failure in ValueError; state is what matters.
        with pytest.raises((RuntimeError, ValueError)):
            storage.create_connection(_conn("lost"))

        monkeypatch.setattr("app.services.connection_storage.os.replace", real_replace)

        # Original connection still readable
        names = [c["name"] for c in storage.list_connections()["connections"]]
        assert names == ["survivor"]
        # No temp leftovers
        leftovers = [p for p in storage.file_path.parent.iterdir() if p.suffix == ".tmp"]
        assert leftovers == []


class TestConcurrentWrites:
    def test_interleaved_read_modify_write_preserves_both(self, tmp_path):
        """Separate PROCESSES' read-modify-write cycles must not lose writes.

        Threads share one GIL and would not exercise the cross-process flock;
        spawn independent interpreter processes synchronized via marker files
        (no multiprocessing primitives: they need /dev/shm). Skipped on
        platforms without fcntl.
        """
        import subprocess
        import sys

        if os.name == "nt":
            pytest.skip("interprocess lock test requires fcntl")

        store_path = tmp_path / "connections.enc"
        seed = ConnectionStorageService(str(store_path))
        seed.create_connection(_conn("first"))

        worker_code = """
import sys, time, os
# Run with cwd=backend so `import app` resolves via sys.path[0] == ""
from app.services.connection_storage import ConnectionStorageService

path, name, ready_dir, total = (
    sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]))
svc = ConnectionStorageService(path)
conn = {
    "name": name, "db_type": "oracle", "host": "db.example.com",
    "port": 1521, "username": "scott", "password": "tiger",
}
open(os.path.join(ready_dir, name), "w").close()
deadline = time.time() + 30
while len(os.listdir(ready_dir)) < total and time.time() < deadline:
    time.sleep(0.02)
svc.create_connection(conn)
"""

        ready_dir = tmp_path / "ready"
        ready_dir.mkdir()
        n = 6
        procs = []
        for i in range(n):
            procs.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-c",
                        worker_code,
                        str(store_path),
                        f"conn-{i}",
                        str(ready_dir),
                        str(n),
                    ],
                    cwd=os.getcwd(),
                )
            )
        for p in procs:
            p.wait(timeout=60)

        assert all(p.returncode == 0 for p in procs)

        names = [
            c["name"]
            for c in ConnectionStorageService(str(store_path)).list_connections()["connections"]
        ]
        assert len(names) == n + 1  # first + n concurrent processes
        assert len(set(names)) == n + 1


class TestCorruptFileHandling:
    def test_corrupt_file_backed_up_not_silently_discarded(self, storage):
        storage.create_connection(_conn("precious"))
        # Corrupt the store
        storage.file_path.write_text("NOT-A-VALID-STORE", encoding="utf-8")

        data = storage._read_file()
        assert data == {"version": 1, "connections": []}

        backup_path = storage.file_path.with_suffix(storage.file_path.suffix + ".bak")
        assert backup_path.exists()
        assert backup_path.read_text(encoding="utf-8") == "NOT-A-VALID-STORE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
