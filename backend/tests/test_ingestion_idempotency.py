from pathlib import Path

from app.rag.ingestion import service
from langchain_core.documents import Document


def test_point_ids_are_stable_for_same_document_version():
    first = service._build_point_ids("document-123", 1, 4)
    retry = service._build_point_ids("document-123", 1, 4)

    assert first == retry
    assert len(set(first)) == 4


def test_point_ids_change_for_a_new_document_version():
    version_one = service._build_point_ids("document-123", 1, 2)
    version_two = service._build_point_ids("document-123", 2, 2)

    assert set(version_one).isdisjoint(version_two)


def test_index_document_reuses_point_ids_on_retry(monkeypatch, tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("content", encoding="utf-8")
    captured_ids = []

    monkeypatch.setattr(
        service,
        "load_document",
        lambda path: [Document(page_content="A short document", metadata={})],
    )
    monkeypatch.setattr(
        service,
        "split_documents",
        lambda documents: [
            Document(page_content="chunk one", metadata=dict(documents[0].metadata)),
            Document(page_content="chunk two", metadata=dict(documents[0].metadata)),
        ],
    )

    def capture(chunks, ids=None):
        captured_ids.append(ids)
        assert [chunk.metadata["aura_chunk_id"] for chunk in chunks] == ids

    monkeypatch.setattr(service, "create_vector_store", capture)

    for _ in range(2):
        service.index_document(
            Path(source),
            job_id="job-123",
            tenant_id="tenant-a",
            document_id="document-123",
            checksum="abc",
        )

    assert captured_ids[0] == captured_ids[1]
    assert len(captured_ids[0]) == 2

def test_content_checksum_maps_to_stable_distinct_versions():
    first = service._version_from_checksum("checksum-a")
    retry = service._version_from_checksum("checksum-a")
    changed = service._version_from_checksum("checksum-b")

    assert first == retry
    assert first > 0
    assert changed != first


def test_reindex_does_not_delete_old_vectors_when_indexing_fails(monkeypatch, tmp_path):
    class Store:
        def get_by_id(self, job_id):
            return {
                "tenant_id": "tenant-a",
                "document_id": "document-123",
                "checksum": "checksum-a",
            }

        def begin_attempt(self, job_id):
            pass

        def update(self, job_id, status, error=None):
            self.status = status

    store = Store()
    cleanup_calls = []
    monkeypatch.setattr(
        service,
        "index_document",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("index failed")),
    )
    monkeypatch.setattr(
        service,
        "delete_obsolete_document_versions",
        lambda **kwargs: cleanup_calls.append(kwargs),
    )

    result = service.reindex_document(store, "job-123", tmp_path / "document.txt")

    assert result is False
    assert store.status == "failed"
    assert cleanup_calls == []
