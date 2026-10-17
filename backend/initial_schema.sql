BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_initial

CREATE TABLE verification_jobs (
    id UUID NOT NULL,
    mode VARCHAR(20) NOT NULL,
    input_text TEXT NOT NULL,
    policy VARCHAR(20) NOT NULL,
    origin VARCHAR(80) NOT NULL,
    parent_claim_ids JSON NOT NULL,
    status VARCHAR(20) NOT NULL,
    overall_action VARCHAR(30),
    error_code VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX ix_verification_jobs_status ON verification_jobs (status);

CREATE TABLE claims (
    id UUID NOT NULL,
    job_id UUID NOT NULL,
    text TEXT NOT NULL,
    start_offset INTEGER,
    end_offset INTEGER,
    checkability VARCHAR(30) NOT NULL,
    provisional_status VARCHAR(30) NOT NULL,
    effective_status VARCHAR(30) NOT NULL,
    reason_codes JSON NOT NULL,
    needs_review BOOLEAN NOT NULL,
    corrected_text TEXT,
    material BOOLEAN NOT NULL,
    high_risk BOOLEAN NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(job_id) REFERENCES verification_jobs (id) ON DELETE CASCADE
);

CREATE INDEX ix_claims_job_id ON claims (job_id);

CREATE INDEX ix_claims_effective_status ON claims (effective_status);

CREATE INDEX ix_claims_needs_review ON claims (needs_review);

CREATE INDEX ix_claim_job_status ON claims (job_id, effective_status);

CREATE TABLE evidence (
    id UUID NOT NULL,
    claim_id UUID NOT NULL,
    stance VARCHAR(20) NOT NULL,
    source_type VARCHAR(40) NOT NULL,
    provenance VARCHAR(40) NOT NULL,
    url TEXT,
    document_id VARCHAR(200),
    title TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    source_text TEXT NOT NULL,
    retrieved_at TIMESTAMP WITH TIME ZONE NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    validity_status VARCHAR(30) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(claim_id) REFERENCES claims (id) ON DELETE CASCADE
);

CREATE INDEX ix_evidence_claim_id ON evidence (claim_id);

CREATE TABLE agent_assessments (
    id UUID NOT NULL,
    claim_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL,
    position VARCHAR(30) NOT NULL,
    reasoning_summary TEXT NOT NULL,
    evidence_ids JSON NOT NULL,
    limitations TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(claim_id) REFERENCES claims (id) ON DELETE CASCADE
);

CREATE INDEX ix_agent_assessments_claim_id ON agent_assessments (claim_id);

CREATE TABLE human_reviews (
    id UUID NOT NULL,
    claim_id UUID NOT NULL,
    decision VARCHAR(40) NOT NULL,
    reviewer_id VARCHAR(120) NOT NULL,
    rationale TEXT NOT NULL,
    corrected_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(claim_id) REFERENCES claims (id) ON DELETE CASCADE
);

CREATE INDEX ix_human_reviews_claim_id ON human_reviews (claim_id);

CREATE TABLE claim_dependencies (
    id UUID NOT NULL,
    parent_claim_id UUID NOT NULL,
    child_claim_id UUID NOT NULL,
    relationship VARCHAR(40) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_claim_dependency UNIQUE (parent_claim_id, child_claim_id),
    FOREIGN KEY(parent_claim_id) REFERENCES claims (id) ON DELETE CASCADE,
    FOREIGN KEY(child_claim_id) REFERENCES claims (id) ON DELETE CASCADE
);

CREATE INDEX ix_claim_dependencies_parent_claim_id ON claim_dependencies (parent_claim_id);

CREATE INDEX ix_claim_dependencies_child_claim_id ON claim_dependencies (child_claim_id);

CREATE TABLE audit_events (
    id UUID NOT NULL,
    entity_type VARCHAR(40) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(80) NOT NULL,
    actor VARCHAR(120) NOT NULL,
    metadata_json JSON NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX ix_audit_events_entity_id ON audit_events (entity_id);

ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY;

ALTER TABLE verification_jobs ENABLE ROW LEVEL SECURITY;

ALTER TABLE claims ENABLE ROW LEVEL SECURITY;

ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;

ALTER TABLE agent_assessments ENABLE ROW LEVEL SECURITY;

ALTER TABLE human_reviews ENABLE ROW LEVEL SECURITY;

ALTER TABLE claim_dependencies ENABLE ROW LEVEL SECURITY;

ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON TABLE alembic_version, verification_jobs, claims, evidence, agent_assessments, human_reviews, claim_dependencies, audit_events FROM anon;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON TABLE alembic_version, verification_jobs, claims, evidence, agent_assessments, human_reviews, claim_dependencies, audit_events FROM authenticated;
    END IF;
END $$;

INSERT INTO alembic_version (version_num) VALUES ('0001_initial') RETURNING alembic_version.version_num;

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

-- Running upgrade 0002_supplied_documents -> 0003_comparison

ALTER TABLE claims ADD COLUMN comparison_result VARCHAR(30);

ALTER TABLE claims ADD COLUMN comparison_explanation TEXT;

ALTER TABLE claims ADD COLUMN unresolved_questions JSON DEFAULT '[]' NOT NULL;

UPDATE alembic_version SET version_num='0003_comparison' WHERE alembic_version.version_num = '0002_supplied_documents';

COMMIT;
