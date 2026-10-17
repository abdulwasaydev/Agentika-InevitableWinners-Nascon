BEGIN;

-- Running upgrade 0002_supplied_documents -> 0003_comparison

ALTER TABLE claims ADD COLUMN comparison_result VARCHAR(30);

ALTER TABLE claims ADD COLUMN comparison_explanation TEXT;

ALTER TABLE claims ADD COLUMN unresolved_questions JSON DEFAULT '[]' NOT NULL;

UPDATE alembic_version SET version_num='0003_comparison' WHERE alembic_version.version_num = '0002_supplied_documents';

COMMIT;
