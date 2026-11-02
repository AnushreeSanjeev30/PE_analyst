from pathlib import Path

from pe_analyst.rag.models import Chunk
from pe_analyst.rag.vector_store import LocalVectorStore


def _chunk(id_: str, document_id: str, page: int, text: str) -> Chunk:
    return Chunk(id_, document_id, page, text)


def test_query_ranks_by_cosine_similarity(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    chunks = [
        _chunk("a", "doc-1", 1, "matches"),
        _chunk("b", "doc-1", 2, "opposite"),
        _chunk("c", "doc-1", 3, "partial"),
    ]
    vectors = [[1.0, 0.0], [-1.0, 0.0], [0.7, 0.7]]

    store.add(chunks, vectors)
    results = store.query([1.0, 0.0], top_k=2)

    assert [item.chunk.id for item in results] == ["a", "c"]
    assert results[0].score > results[1].score


def test_query_respects_document_id_filter(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    store.add([_chunk("a", "doc-1", 1, "x")], [[1.0, 0.0]])
    store.add([_chunk("b", "doc-2", 1, "y")], [[1.0, 0.0]])

    results = store.query([1.0, 0.0], top_k=10, document_id="doc-2")

    assert [item.chunk.id for item in results] == ["b"]


def test_store_persists_and_reloads_from_disk(tmp_path: Path) -> None:
    path = tmp_path / "vectors.json"
    LocalVectorStore(path).add([_chunk("a", "doc-1", 1, "hello")], [[1.0, 0.0]])

    reloaded = LocalVectorStore(path)
    results = reloaded.query([1.0, 0.0], top_k=1)

    assert len(results) == 1
    assert results[0].chunk.text == "hello"


def test_query_on_empty_store_returns_nothing(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")

    assert store.query([1.0, 0.0], top_k=5) == []
