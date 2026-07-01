# dbt/ — jaffle shop on Snowflake

The canonical [dbt-labs/jaffle_shop](https://github.com/dbt-labs/jaffle_shop)
project, retargeted to Snowflake with a medallion layout and native semantic
views. The models and seeds are unchanged; only project config + macros were
added.

## Medallion routing

| Resource | Location | Notes |
|----------|----------|-------|
| seeds (`raw_customers`, `raw_orders`, `raw_payments`) | `BRONZE.RAW` | raw landing |
| staging models (`stg_*`) | `SILVER.STAGING` | cleaned/conformed views |
| marts (`customers`, `orders`) | `GOLD.MARTS` | curated tables + semantic views |

Routing is set in `dbt_project.yml` and made literal by
`macros/get_custom_names.sql`. `DBT_ROLE` is **read-write on BRONZE, SILVER and
GOLD**, matching the seeds → staging → marts flow across the medallion layers.

## Run

```bash
cp profiles.example.yml ~/.dbt/profiles.yml     # then fill in env vars
export SNOWFLAKE_ACCOUNT=abc-xy123
export DBT_PRIVATE_KEY_PATH=~/.snowflake/dbt_key.p8

dbt deps
dbt seed                       # -> BRONZE.RAW
dbt build                      # staging -> SILVER, marts -> GOLD
dbt run-operation create_semantic_views   # -> GOLD.MARTS.SEM_JAFFLE
dbt run-operation apply_governance         # bind PII masking to gold marts
```

## Added macros

| Macro | Purpose |
|-------|---------|
| `get_custom_names.sql` | Literal `+database` / `+schema` resolution |
| `create_semantic_views.sql` | Builds `GOLD.MARTS.SEM_JAFFLE` semantic view |
| `apply_governance.sql` | Binds the ABAC masking policy to gold mart PII columns |
