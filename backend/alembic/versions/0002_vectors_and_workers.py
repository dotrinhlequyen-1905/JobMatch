"""Preserve legacy embeddings, add worker status and active application uniqueness."""

import json
import struct

from alembic import op
from pgvector.sqlalchemy import VECTOR
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    postgres = connection.dialect.name == "postgresql"
    if postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    for table in ("cvs", "jobs"):
        op.add_column(table, sa.Column("embedding_new", VECTOR() if postgres else sa.JSON(), nullable=True))
        op.add_column(table, sa.Column("processing_status", sa.String(20), server_default="PENDING", nullable=False))
        op.add_column(table, sa.Column("embedding_revision", sa.Integer(), server_default="0", nullable=False))
        op.add_column(table, sa.Column("embedding_model", sa.String(300), server_default="", nullable=False))
        rows = connection.execute(sa.text(f"SELECT id, embedding FROM {table} WHERE embedding IS NOT NULL")).all()
        for row_id, blob in rows:
            blob = bytes(blob)
            vector = list(struct.unpack(f"<{len(blob) // 4}f", blob))
            expression = "CAST(:value AS vector)" if postgres else ":value"
            connection.execute(
                sa.text(
                    f"UPDATE {table} SET embedding_new = {expression}, "
                    "embedding_model = 'legacy', processing_status = 'READY' WHERE id = :id"
                ),
                {"id": row_id, "value": json.dumps(vector)},
            )
        op.drop_column(table, "embedding")
        op.alter_column(table, "embedding_new", new_column_name="embedding")
        if postgres:
            op.execute(
                f"CREATE INDEX ix_{table}_embedding_hnsw ON {table} USING hnsw "
                "((embedding::vector(768)) vector_cosine_ops) WHERE vector_dims(embedding) = 768"
            )
    uniques = sa.inspect(connection).get_unique_constraints("applications")
    unique = next((u for u in uniques if set(u["column_names"]) == {"job_id", "candidate_id"}), None)
    if unique:
        if postgres:
            op.drop_constraint(unique["name"], "applications", type_="unique")
        else:
            convention = {"uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s"}
            with op.batch_alter_table("applications", naming_convention=convention) as batch:
                batch.drop_constraint(unique["name"] or "uq_applications_job_id_candidate_id", type_="unique")
    condition = sa.text("status NOT IN ('REJECTED','WITHDRAWN')")
    op.create_index(
        "uq_application_active",
        "applications",
        ["job_id", "candidate_id"],
        unique=True,
        postgresql_where=condition,
        sqlite_where=condition,
    )


def downgrade():
    connection = op.get_bind()
    postgres = connection.dialect.name == "postgresql"
    duplicates = connection.execute(
        sa.text("SELECT job_id, candidate_id FROM applications GROUP BY job_id, candidate_id HAVING COUNT(*) > 1")
    ).first()
    if duplicates:
        raise RuntimeError("Cannot downgrade while historical reapplications exist; retain the new schema.")
    op.drop_index("uq_application_active", table_name="applications")
    with op.batch_alter_table("applications") as batch:
        batch.create_unique_constraint("uq_applications_job_candidate", ["job_id", "candidate_id"])
    for table in ("cvs", "jobs"):
        if postgres:
            op.drop_index(f"ix_{table}_embedding_hnsw", table_name=table)
        op.add_column(table, sa.Column("embedding_old", sa.LargeBinary(), nullable=True))
        for row_id, vector in connection.execute(
            sa.text(f"SELECT id, embedding FROM {table} WHERE embedding IS NOT NULL")
        ).all():
            vector = json.loads(vector) if isinstance(vector, str) else vector
            blob = struct.pack(f"<{len(vector)}f", *vector)
            connection.execute(
                sa.text(f"UPDATE {table} SET embedding_old = :value WHERE id = :id"), {"id": row_id, "value": blob}
            )
        op.drop_column(table, "embedding")
        op.alter_column(table, "embedding_old", new_column_name="embedding")
        for name in ("processing_status", "embedding_revision", "embedding_model"):
            op.drop_column(table, name)
