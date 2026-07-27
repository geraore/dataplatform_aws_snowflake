-- S3 Storage Integration for the events bucket.
--
-- Prerequisites (one-time manual steps before running schemachange):
--   1. Deploy the CDK IngestStack — the SnowflakeS3RoleArn output gives you the
--      IAM role ARN to paste below.
--   2. Run this migration (schemachange will execute it as SCHEMACHANGE_ROLE,
--      which has GRANT CREATE INTEGRATION from bootstrap/00_bootstrap.sql).
--   3. After the migration runs, execute in Snowflake:
--        DESC INTEGRATION EVENTS_S3_INT;
--      Copy STORAGE_AWS_IAM_USER_ARN → SNOWFLAKE_IAM_USER_ARN in .env
--      Copy STORAGE_AWS_EXTERNAL_ID  → SNOWFLAKE_EXTERNAL_ID  in .env
--      Then redeploy CDK to lock the trust policy.
--
-- STORAGE_AWS_ROLE_ARN and STORAGE_ALLOWED_LOCATIONS are templated from the
-- CDK_DEFAULT_ACCOUNT env var (set in .env). Run schemachange with .env sourced.
USE ROLE SCHEMACHANGE_ROLE;

CREATE STORAGE INTEGRATION IF NOT EXISTS EVENTS_S3_INT
TYPE = EXTERNAL_STAGE
STORAGE_PROVIDER = 'S3'
ENABLED = TRUE
STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::{{ env_var("CDK_DEFAULT_ACCOUNT") }}:role/dataplatform-snowflake-s3-role'  -- noqa: LT05
STORAGE_ALLOWED_LOCATIONS = ('s3://dataplatform-events-{{ env_var("CDK_DEFAULT_ACCOUNT") }}/');

-- After DESC INTEGRATION you will see the two values needed to lock the IAM
-- trust policy (see step 3 in the header comment):
--   DESC INTEGRATION EVENTS_S3_INT;
--   → STORAGE_AWS_IAM_USER_ARN   ← add to .env as SNOWFLAKE_IAM_USER_ARN
--   → STORAGE_AWS_EXTERNAL_ID    ← add to .env as SNOWFLAKE_EXTERNAL_ID

-- Grant DBT_ROLE the ability to use this integration when creating stages.
GRANT USAGE ON INTEGRATION EVENTS_S3_INT TO ROLE DBT_ROLE;
