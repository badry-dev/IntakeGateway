"""Tests for atomic, locked connections-file storage (v1.4 H4)."""

import threading

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
        """If the process dies mid-write, the old store remains intact."""
        storage.create_connection(_conn("survivor"))

        def explode(self, data):
            raise RuntimeError("simulated crash mid-write")

        monkeypatch.setattr(ConnectionStorageService, "_write_file", explode)
        with pytest.raises(RuntimeError):
            storage.create_connection(_conn("lost"))

        # Original connection still readable
        names = [c["name"] for c in storage.list_connections()["connections"]]
        assert names == ["survivor"]


class TestConcurrentWrites:
    def test_interleaved_read_modify_write_preserves_both(self, storage):
        """Two processes' read-modify-write cycles must not lose writes."""
        storage.create_connection(_conn("first"))

        errors = []

        def add(name):
            svc = ConnectionStorageService(str(storage.file_path))
            try:
                svc.create_connection(_conn(name))
            except Exception as e:  # pragma: no cover
                errors.append(e)

        threads = [threading.Thread(target=add, args=(f"conn-{i}",)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        names = [c["name"] for c in storage.list_connections()["connections"]]
        assert len(names) == 9  # first + 8 concurrent
        assert len(set(names)) == 9


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
