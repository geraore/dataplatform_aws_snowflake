-- This script must be run manually after V1.1.8__cortex_analyst_setup runs.
-- It cannot be scripted because it requires the ACCOUNTADMIN role to create
-- the database role and grant it to CORTEX_ROLE.

GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE CORTEX_ROLE;
