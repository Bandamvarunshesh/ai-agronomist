"""knowledge and intelligence platform

Revision ID: 20260708_0010
Revises: 20260708_0009
Create Date: 2026-07-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260708_0010"
down_revision = "20260708_0009"
branch_labels = None
depends_on = None


def uuid_pk_column() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def timestamp_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "knowledge_documents",
        uuid_pk_column(),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_uri", sa.String(length=2048), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("language", sa.String(length=16), server_default=sa.text("'en'"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column("current_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("duplicate_of_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ingested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["duplicate_of_document_id"],
            ["knowledge_documents.id"],
            name=op.f("fk_knowledge_documents_duplicate_of_document_id_knowledge_documents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["ingested_by_user_id"],
            ["users.id"],
            name=op.f("fk_knowledge_documents_ingested_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_documents")),
    )
    for column in [
        "title",
        "source_type",
        "source_uri",
        "content_type",
        "language",
        "status",
        "checksum",
        "duplicate_of_document_id",
        "ingested_by_user_id",
    ]:
        op.create_index(
            op.f(f"ix_knowledge_documents_{column}"),
            "knowledge_documents",
            [column],
            unique=False,
        )

    op.create_table(
        "knowledge_document_versions",
        uuid_pk_column(),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("storage_path", sa.String(length=2048), nullable=True),
        sa.Column("parser", sa.String(length=64), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge_documents.id"],
            name=op.f("fk_knowledge_document_versions_document_id_knowledge_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_document_versions")),
        sa.UniqueConstraint(
            "document_id",
            "version_number",
            name=op.f("uq_knowledge_document_versions_document_version"),
        ),
    )
    op.create_index(op.f("ix_knowledge_document_versions_document_id"), "knowledge_document_versions", ["document_id"])
    op.create_index(op.f("ix_knowledge_document_versions_checksum"), "knowledge_document_versions", ["checksum"])
    op.create_index(op.f("ix_knowledge_document_versions_indexed_at"), "knowledge_document_versions", ["indexed_at"])

    op.create_table(
        "knowledge_chunks",
        uuid_pk_column(),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("citation_label", sa.String(length=255), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge_documents.id"],
            name=op.f("fk_knowledge_chunks_document_id_knowledge_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["knowledge_document_versions.id"],
            name=op.f("fk_knowledge_chunks_version_id_knowledge_document_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_chunks")),
        sa.UniqueConstraint(
            "version_id",
            "chunk_index",
            name=op.f("uq_knowledge_chunks_version_chunk"),
        ),
    )
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(768) USING embedding::vector")
    op.execute(
        "ALTER TABLE knowledge_chunks ADD COLUMN search_vector tsvector "
        "GENERATED ALWAYS AS (to_tsvector('simple', coalesce(content, ''))) STORED"
    )
    op.create_index(op.f("ix_knowledge_chunks_document_id"), "knowledge_chunks", ["document_id"])
    op.create_index(op.f("ix_knowledge_chunks_version_id"), "knowledge_chunks", ["version_id"])
    op.create_index(op.f("ix_knowledge_chunks_content_hash"), "knowledge_chunks", ["content_hash"])
    op.create_index(op.f("ix_knowledge_chunks_is_active"), "knowledge_chunks", ["is_active"])
    op.create_index("ix_knowledge_chunks_search_vector", "knowledge_chunks", ["search_vector"], postgresql_using="gin")
    op.create_index("ix_knowledge_chunks_embedding", "knowledge_chunks", ["embedding"], postgresql_using="ivfflat", postgresql_with={"lists": 100}, postgresql_ops={"embedding": "vector_cosine_ops"})

    op.create_table(
        "intelligence_sources",
        uuid_pk_column(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_format", sa.String(length=32), server_default=sa.text("'rss'"), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("language", sa.String(length=16), server_default=sa.text("'en'"), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("crop_tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("credibility_score", sa.Numeric(precision=5, scale=4), server_default=sa.text("0.5000"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intelligence_sources")),
        sa.UniqueConstraint("url", name=op.f("uq_intelligence_sources_url")),
    )
    for column in ["source_type", "language", "state", "district", "is_active"]:
        op.create_index(op.f(f"ix_intelligence_sources_{column}"), "intelligence_sources", [column])

    op.create_table(
        "news_articles",
        uuid_pk_column(),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("article_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("language", sa.String(length=16), server_default=sa.text("'en'"), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("crop_tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("state_tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("district_tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("credibility_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["source_id"], ["intelligence_sources.id"], name=op.f("fk_news_articles_source_id_intelligence_sources"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_news_articles")),
        sa.UniqueConstraint("url", name=op.f("uq_news_articles_url")),
    )
    op.execute(
        "ALTER TABLE news_articles ADD COLUMN search_vector tsvector "
        "GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(summary, '') || ' ' || coalesce(content, ''))) STORED"
    )
    for column in ["source_id", "article_type", "title", "language", "category", "content_hash", "published_at", "fetched_at"]:
        op.create_index(op.f(f"ix_news_articles_{column}"), "news_articles", [column])
    op.create_index("ix_news_articles_search_vector", "news_articles", ["search_vector"], postgresql_using="gin")
    op.create_index("ix_news_articles_crop_tags", "news_articles", ["crop_tags"], postgresql_using="gin")
    op.create_index("ix_news_articles_state_tags", "news_articles", ["state_tags"], postgresql_using="gin")
    op.create_index("ix_news_articles_district_tags", "news_articles", ["district_tags"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_news_articles_district_tags", table_name="news_articles")
    op.drop_index("ix_news_articles_state_tags", table_name="news_articles")
    op.drop_index("ix_news_articles_crop_tags", table_name="news_articles")
    op.drop_index("ix_news_articles_search_vector", table_name="news_articles")
    for column in ["fetched_at", "published_at", "content_hash", "category", "language", "title", "article_type", "source_id"]:
        op.drop_index(op.f(f"ix_news_articles_{column}"), table_name="news_articles")
    op.drop_table("news_articles")
    for column in ["is_active", "district", "state", "language", "source_type"]:
        op.drop_index(op.f(f"ix_intelligence_sources_{column}"), table_name="intelligence_sources")
    op.drop_table("intelligence_sources")
    op.drop_index("ix_knowledge_chunks_embedding", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_search_vector", table_name="knowledge_chunks")
    op.drop_index(op.f("ix_knowledge_chunks_is_active"), table_name="knowledge_chunks")
    op.drop_index(op.f("ix_knowledge_chunks_content_hash"), table_name="knowledge_chunks")
    op.drop_index(op.f("ix_knowledge_chunks_version_id"), table_name="knowledge_chunks")
    op.drop_index(op.f("ix_knowledge_chunks_document_id"), table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index(op.f("ix_knowledge_document_versions_indexed_at"), table_name="knowledge_document_versions")
    op.drop_index(op.f("ix_knowledge_document_versions_checksum"), table_name="knowledge_document_versions")
    op.drop_index(op.f("ix_knowledge_document_versions_document_id"), table_name="knowledge_document_versions")
    op.drop_table("knowledge_document_versions")
    for column in [
        "ingested_by_user_id",
        "duplicate_of_document_id",
        "checksum",
        "status",
        "language",
        "content_type",
        "source_uri",
        "source_type",
        "title",
    ]:
        op.drop_index(op.f(f"ix_knowledge_documents_{column}"), table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
