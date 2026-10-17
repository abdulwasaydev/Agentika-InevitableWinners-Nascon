"""The manually reviewed SQL keeps Veritas records off Supabase's Data API."""

from pathlib import Path


def test_initial_sql_protects_every_backend_table():
    sql = (Path(__file__).resolve().parents[1] / "initial_schema.sql").read_text().lower()
    tables = (
        "alembic_version", "verification_jobs", "supplied_documents", "claims", "evidence",
        "agent_assessments", "human_reviews", "claim_dependencies", "audit_events",
    )
    for table in tables:
        assert f"alter table {table} enable row level security;" in sql
    for role in ("anon", "authenticated"):
        assert f"from {role};" in sql
    assert sql.index("alter table audit_events enable row level security") < sql.index("commit;")
