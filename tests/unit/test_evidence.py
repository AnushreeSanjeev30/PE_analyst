from uuid import UUID

from pe_analyst.domain.evidence import Evidence


def test_create_evidence(document_id: UUID) -> None:
    evidence = Evidence(
        document_id=document_id,
        claim="Revenue increased.",
        page_number=12,
        confidence=0.98,
    )

    assert evidence.confidence == 0.98
