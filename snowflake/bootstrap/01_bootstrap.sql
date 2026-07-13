-- This script should be run once the V1.1.8__cortex_analyst setp is run, this can not be scripted and needs to be published manually
-- this is needed as account admin role is needed to create the database role and grant it to the cortex_role

GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE CORTEX_ROLE;
