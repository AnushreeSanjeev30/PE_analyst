from pe_analyst.core.config import Settings
from pe_analyst.rag.embeddings import (
    LocalHashingEmbeddingProvider,
    OpenAIEmbeddingProvider,
    build_embedding_provider,
)


def test_local_embedder_is_deterministic() -> None:
    provider = LocalHashingEmbeddingProvider()

    first = provider.embed(["Revenue increased in the fourth quarter."])
    second = provider.embed(["Revenue increased in the fourth quarter."])

    assert first == second
    assert len(first[0]) == LocalHashingEmbeddingProvider.dimension


def test_local_embedder_distinguishes_different_text() -> None:
    provider = LocalHashingEmbeddingProvider()

    vectors = provider.embed(["Revenue grew significantly.", "Risk factors include litigation."])

    assert vectors[0] != vectors[1]


def test_local_embedder_handles_empty_text() -> None:
    provider = LocalHashingEmbeddingProvider()

    vectors = provider.embed([""])

    assert vectors == [[0.0] * LocalHashingEmbeddingProvider.dimension]


def test_build_embedding_provider_uses_local_without_api_key(test_settings: Settings) -> None:
    provider = build_embedding_provider(test_settings)

    assert isinstance(provider, LocalHashingEmbeddingProvider)


def test_build_embedding_provider_uses_openai_with_api_key(test_settings: Settings) -> None:
    settings = test_settings.model_copy(update={"openai_api_key": "sk-test"})

    provider = build_embedding_provider(settings)

    assert isinstance(provider, OpenAIEmbeddingProvider)
