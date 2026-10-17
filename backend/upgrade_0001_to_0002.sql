BEGIN;

-- Running upgrade 0001_initial -> 0002_supplied_documents

CREATE TABLE supplied_documents (
    id UUID NOT NULL,
    job_id UUID NOT NULL,
    document_id VARCHAR(120) NOT NULL,
    title VARCHAR(200) NOT NULL,
    version VARCHAR(80),
    effective_date VARCHAR(80),
    text TEXT NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_supplied_document_job_id UNIQUE (job_id, document_id),
    FOREIGN KEY(job_id) REFERENCES verification_jobs (id) ON DELETE CASCADE
);

CREATE INDEX ix_supplied_documents_job_id ON supplied_documents (job_id);

ALTER TABLE supplied_documents ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON TABLE supplied_documents FROM anon;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON TABLE supplied_documents FROM authenticated;
    END IF;
END $$;

UPDATE alembic_version SET version_num='0002_supplied_documents' WHERE alembic_version.version_num = '0001_initial';

COMMIT;
