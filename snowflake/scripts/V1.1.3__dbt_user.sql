-- dbt materialization identity.
--
-- DBT_ROLE gets read-write on BRONZE, SILVER and GOLD. dbt seeds raw data into
-- BRONZE, builds conformed staging models in SILVER, and builds marts into GOLD.
USE ROLE SCHEMACHANGE_ROLE;

CREATE ROLE IF NOT EXISTS DBT_ROLE COMMENT = 'Role dbt uses to materialize models';

-- Database-scoped privileges via the database roles from V1.1.2.
GRANT DATABASE ROLE BRONZE.READ_WRITE TO ROLE DBT_ROLE;
GRANT DATABASE ROLE SILVER.READ_WRITE TO ROLE DBT_ROLE;
GRANT DATABASE ROLE GOLD.READ_WRITE TO ROLE DBT_ROLE;
-- Needs to read entitlements when attaching/maintaining governance policies.
GRANT DATABASE ROLE GOVERNANCE.READ_ONLY TO ROLE DBT_ROLE;

GRANT USAGE ON WAREHOUSE DBT_WH TO ROLE DBT_ROLE;

CREATE USER IF NOT EXISTS DBT_USER
    DEFAULT_ROLE = DBT_ROLE
    DEFAULT_WAREHOUSE = DBT_WH
    RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEApB2Xg3lx/h3un17ywKaLNZT+JHOYiw8HaWZu7K4la/d8/iUw3UPTWsfQ9BUr+K1S87ZZQtKhgGWdi3YpKaFchy7hAXU5UpcMI1Xtvma6Mln9EWFQ2mSTBQ3zAPaSThpNwZQRt2MeaOYyRbIIyNa/FEPHxoclJAK5lDK++CCS39BYblhJrB+TmFLZBwuP6h9jEsT3XFCsOPX6YcIvE4+5G46jsR+NtEkcwvxZQQniGRK3aoZQNp0PeKh3DWFTpEvFWg7Ani7yhuJssqtqZ50hkH7zlfleWRI3s9dNm/k2Wz4SCX9++yAtBAYa84qLvBkd5Cfg1mxdoYUdptKp3hJw+wIDAQAB'  -- noqa: LT05
    COMMENT = 'Service user for dbt';
GRANT ROLE DBT_ROLE TO USER DBT_USER;

-- Let the deploying role manage the user later if needed.
GRANT ROLE DBT_ROLE TO ROLE SYSADMIN;
