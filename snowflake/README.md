# snowflake/ — schemachange

All Snowflake DDL is version-controlled and applied with
[schemachange](https://github.com/Snowflake-Labs/schemachange).

## Setup

```bash
uv sync          # creates .venv and installs schemachange
```

## Order of operations

1. **Bootstrap once** as `ACCOUNTADMIN` — creates the schemachange role/user/
   warehouse, the change-history table, and the Firehose ingestion user:

   ```sql
   -- review and run bootstrap/00_bootstrap.sql (replace the RSA public keys)
   ```

2. **Deploy versioned scripts** with schemachange:

   ```bash
   export SNOWFLAKE_ACCOUNT=abc-xy123
   export SNOWFLAKE_USER=SCHEMACHANGE_USER
   export SNOWFLAKE_PRIVATE_KEY_PATH=~/.snowflake/schemachange_key.p8
   uv run schemachange deploy --config-folder .
   ```

## Versioned scripts (`scripts/`)

| Script | Creates |
|--------|---------|
| `V1.1.1__databases.sql` | `BRONZE`, `SILVER`, `GOLD`, `GOVERNANCE` + default schemas |
| `V1.1.2__database_roles.sql` | `READ_ONLY` / `READ_WRITE` / `ADMIN` / `NO_PII` database roles per DB |
| `V1.1.3__dbt_user.sql` | `DBT_ROLE` + `DBT_USER` (RO silver, RW bronze + gold) |
| `V1.1.4__security_schema.sql` | `GOVERNANCE.SECURITY` schema + `ENTITLEMENTS` table |
| `V1.1.5__abac_policies.sql` | PII masking policy + region row-access policy (ABAC) |
| `V1.1.6__firehose_landing.sql` | `BRONZE.RAW.EVENTS` + grants to `FIREHOSE_ROLE` |

## Key-pair generation

```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
# paste rsa_key.pub (without the BEGIN/END lines) into the RSA_PUBLIC_KEY fields
```

Generate one key pair each for `SCHEMACHANGE_USER`, `FIREHOSE_USER`, and
`DBT_USER`. The Firehose private key also goes into the
`dataplatform/snowflake/firehose-connection` Secrets Manager secret.
