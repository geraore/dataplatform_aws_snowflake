-- S3 Storage Integration for the events bucket.
--
-- Prerequisites (one-time manual steps before running schemachange):
--   1. Deploy the CDK IngestStack — the SnowflakeS3RoleArn output gives you the
--      IAM role ARN to paste below.
--   2. Run this migration (schemachange will execute it as SCHEMACHANGE_ROLE,
--      which has GRANT CREATE INTEGRATION from bootstrap/00_bootstrap.sql).
--   3. After the migration runs, execute in Snowflake:
--        DESC INTEGRATION EVENTS_S3_INT;
--      Copy STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID, then pass
--      them as CDK context on the next deploy to lock the trust policy:
--        cdk deploy -c snowflake_iam_user_arn=<value> -c snowflake_external_id=<value>
--
-- STORAGE_ALLOWED_LOCATIONS: replace <prefix> and <aws-account-id> with the
-- values from CDK outputs (EventsBucketName  →  <prefix>-events-<aws-account-id>).
USE ROLE SCHEMACHANGE_ROLE;

CREATE STORAGE INTEGRATION IF NOT EXISTS EVENTS_S3_INT
TYPE = EXTERNAL_STAGE
STORAGE_PROVIDER = 'S3'
ENABLED = TRUE
STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::190855935274:role/dataplatform-snowflake-s3-role'
STORAGE_ALLOWED_LOCATIONS = ('s3://dataplatform-events-190855935274/');

-- After DESC INTEGRATION you will see the two values needed to lock the IAM
-- trust policy (see step 3 in the header comment):
--   DESC INTEGRATION EVENTS_S3_INT;
--   → STORAGE_AWS_IAM_USER_ARN   ← paste as CDK context snowflake_iam_user_arn
--   → STORAGE_AWS_EXTERNAL_ID    ← paste as CDK context snowflake_external_id

-- Grant DBT_ROLE the ability to use this integration when creating stages.
GRANT USAGE ON INTEGRATION EVENTS_S3_INT TO ROLE DBT_ROLE;
