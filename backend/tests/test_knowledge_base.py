import asyncio
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.knowledge_base import (
    EmbeddingServiceError,
    KnowledgeChunk,
    KnowledgeDocument,
    delete_document,
    generate_embeddings,
    ingest_file,
    ingest_document,
    search_knowledge,
    split_text,
)
from app.ingest_labour_data import build_series_document, build_specialties_document


def test_split_text_applies_configured_overlap_and_rejects_bad_sizes() -> None:
    chunks = split_text("one two three four five six", chunk_size=14, chunk_overlap=4)

    assert len(chunks) > 1
    assert "three" in chunks[0] + chunks[1]
    with pytest.raises(ValueError, match="Chunk size"):
        split_text("text", chunk_size=10, chunk_overlap=10)


def test_document_ingestion_is_idempotent_and_keyword_search_filters_metadata(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MAHARA_EMBEDDING_BASE_URL", raising=False)
    document = asyncio.run(
        ingest_document(
            session,
            external_id="tn-labor-2025",
            title="Tunisia unemployment",
            content="Tunisia youth unemployment remains a key labor market indicator.",
            source="World Bank WDI",
            source_url="https://data.worldbank.org/indicator/SL.UEM.1524.ZS?locations=TN",
            category="labor_market",
            country="TN",
            language="en",
        )
    )
    repeated = asyncio.run(
        ingest_document(
            session,
            external_id="tn-labor-2025",
            title="Tunisia unemployment updated title",
            content="Tunisia youth unemployment remains a key labor market indicator.",
            source="World Bank WDI",
            category="labor_market",
            country="TN",
            language="en",
        )
    )

    assert repeated.id == document.id
    assert repeated.title == "Tunisia unemployment updated title"
    assert repeated.status == "ready"
    assert session.scalar(
        select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.document_id == document.id
        )
    ) == 1

    hits = asyncio.run(
        search_knowledge(session, "youth unemployment labor", country="TN")
    )
    assert [hit.document_id for hit in hits] == ["tn-labor-2025"]
    assert hits[0].source == "World Bank WDI"
    assert hits[0].source_url is None
    assert asyncio.run(
        search_knowledge(session, "youth unemployment", country="FR")
    ) == []


def test_changed_document_replaces_chunks_and_delete_cascades(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MAHARA_EMBEDDING_BASE_URL", raising=False)
    first = asyncio.run(
        ingest_document(
            session,
            external_id="changing-source",
            title="Initial",
            content="First source text.",
            source="Test source",
        )
    )
    second = asyncio.run(
        ingest_document(
            session,
            external_id="changing-source",
            title="Updated",
            content="Revised source text with additional information.",
            source="Test source",
        )
    )
    assert first.id == second.id
    assert session.scalar(
        select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.document_id == first.id
        )
    ) == 1
    assert delete_document(session, "changing-source")
    assert session.scalar(
        select(KnowledgeDocument).where(KnowledgeDocument.external_id == "changing-source")
    ) is None
    assert not delete_document(session, "changing-source")


def test_embedding_failure_is_recorded_and_propagated(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.knowledge_base.embedding_service_configured", lambda: True)

    async def fail_embeddings(texts: Any) -> tuple[list[list[float]], str]:
        raise EmbeddingServiceError("embedding unavailable")

    monkeypatch.setattr("app.knowledge_base.generate_embeddings", fail_embeddings)
    with pytest.raises(EmbeddingServiceError, match="unavailable"):
        asyncio.run(
            ingest_document(
                session,
                external_id="failed-ingestion",
                title="Embedding failure",
                content="This content must be embedded and the error preserved.",
                source="Test source",
            )
        )

    document = session.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.external_id == "failed-ingestion"
        )
    )
    assert document is not None
    assert document.status == "failed"
    assert document.ingestion_error == "embedding unavailable"
    assert session.scalar(
        select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.document_id == document.id
        )
    ) == 0


def test_embedding_failure_falls_back_to_keyword_retrieval(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MAHARA_EMBEDDING_BASE_URL", raising=False)
    asyncio.run(
        ingest_document(
            session,
            external_id="keyword-fallback",
            title="Tunisia labor market",
            content="Tunisia youth unemployment is an important labor market indicator.",
            source="World Bank WDI",
            category="labor_market",
            country="Tunisia",
        )
    )
    monkeypatch.setattr("app.knowledge_base.embedding_service_configured", lambda: True)

    async def fail_embeddings(texts: Any) -> tuple[list[list[float]], str]:
        raise EmbeddingServiceError("embedding service is down")

    monkeypatch.setattr("app.knowledge_base.generate_embeddings", fail_embeddings)
    hits = asyncio.run(search_knowledge(session, "Tunisia youth unemployment"))

    assert len(hits) == 1
    assert hits[0].document_id == "keyword-fallback"


def test_embedding_client_validates_service_vectors(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0] + [0.0] * 382},
                    {"index": 0, "embedding": [1.0, 0.0] + [0.0] * 382},
                ]
            }

    class Client:
        def __init__(self, *, timeout: float) -> None:
            assert timeout == 30

        async def __aenter__(self) -> "Client":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def post(self, *args: Any, **kwargs: Any) -> Response:
            return Response()

    monkeypatch.setenv("MAHARA_EMBEDDING_BASE_URL", "http://localhost:1234")
    monkeypatch.setenv("MAHARA_EMBEDDING_MODEL", "test-embeddings")
    monkeypatch.setattr("app.knowledge_base.httpx.AsyncClient", Client)

    vectors, model = asyncio.run(generate_embeddings(["first", "second"]))

    assert model == "test-embeddings"
    assert len(vectors) == 2
    assert all(len(vector) == 384 for vector in vectors)
    assert vectors[0][:2] == [1.0, 0.0]
    assert vectors[1][:2] == [0.0, 1.0]


def test_embedding_client_rejects_dimensions_incompatible_with_pgvector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAHARA_EMBEDDING_BASE_URL", "http://localhost:1234")
    monkeypatch.setenv("MAHARA_EMBEDDING_MODEL", "test-embeddings")
    monkeypatch.setenv("MAHARA_EMBEDDING_DIMENSIONS", "768")

    with pytest.raises(EmbeddingServiceError, match="384 to match the pgvector schema"):
        asyncio.run(generate_embeddings(["first"]))


def test_document_file_reader_supports_markdown_and_rejects_unknown_types(
    tmp_path: Path,
) -> None:
    from app.knowledge_base import KnowledgeBaseError, ingest_file_content

    markdown_file = tmp_path / "career.md"
    markdown_file.write_text("# Career paths\n", encoding="utf-8")
    assert ingest_file_content(markdown_file) == "# Career paths\n"
    with pytest.raises(KnowledgeBaseError, match="Only UTF-8"):
        ingest_file_content(tmp_path / "data.csv")


def test_file_ingestion_preserves_file_metadata(
    session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MAHARA_EMBEDDING_BASE_URL", raising=False)
    document_path = tmp_path / "data.md"
    document_path.write_text("# Tunisia jobs\nTrusted source text.", encoding="utf-8")

    document = asyncio.run(
        ingest_file(
            session,
            document_path,
            external_id="markdown-data",
            source="INS",
            category="labor_market",
            country="Tunisia",
            language="fr",
        )
    )

    assert document.content.startswith("# Tunisia jobs")
    assert document.document_metadata["filename"] == "data.md"
    assert len(document.document_metadata["file_sha256"]) == 64


def test_labour_series_document_preserves_country_provenance_and_years() -> None:
    document = build_series_document(
        {
            "source_id": "worldbank-tn-unemployment",
            "title": "Unemployment — Tunisia",
            "provider": "World Bank, World Development Indicators",
            "landing_page": "https://data.worldbank.org/indicator/example?locations=TN",
            "data_last_updated": "2026-10-08",
            "retrieved_at": "2026-11-07T08:30:00+00:00",
            "license": "World Bank Terms of Use for Datasets",
            "license_url": "https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets",
        },
        [
            {"country": "TN", "period": "2024", "value": 15.3, "unit": "percent"},
            {"country": "TN", "period": "2025", "value": 15.1, "unit": "percent"},
        ],
    )

    assert document["country"] == "Tunisia"
    assert document["source"] == "World Bank, World Development Indicators"
    assert document["source_url"].endswith("locations=TN")
    assert document["metadata"]["period_start"] == "2024"
    assert document["metadata"]["period_end"] == "2025"
    assert document["metadata"]["license"] == "World Bank Terms of Use for Datasets"
    assert document["metadata"]["license_url"].startswith("https://")
    assert "modelled ILO estimates" in document["content"]


def test_vocational_specialty_document_is_historical_not_current_catalogue() -> None:
    document = build_specialties_document(
        {
            "source_id": "tunisia-vocational-specialties",
            "title": "Liste des spécialités en Tunisie en 2017",
            "provider": "Ministère de l'Emploi et de la Formation professionnelle",
            "landing_page": "https://catalog.data.gov.tn/dataset/specialties",
            "license": "cc-by",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "resource_modified_at": "2023-03-14T18:04:03.369347",
        },
        [
            {
                "country": "TN",
                "specialty_code": "301204",
                "specialty_fr": "Ferrailleur",
                "specialty_ar": "حدائدي",
                "sector": "BTP",
                "subsector": "Building",
                "certificate": "ش ك م",
                "training_duration_years": 1.0,
            }
        ],
    )

    assert document["category"] == "formation"
    assert document["country"] == "Tunisia"
    assert document["language"] == "ar+fr"
    assert document["metadata"]["current_course_catalogue"] is False
    assert document["metadata"]["license_url"].startswith("https://")
    assert "not a current course availability catalogue" in document["content"]
    assert "Ferrailleur" in document["content"]
