from pe_analyst.domain.company import Company


def test_create_company() -> None:
    company = Company(
        name="Tesla",
        industry="Automotive",
        headquarters="USA",
    )

    assert company.name == "Tesla"