# Local Airflow image for the data platform demo.
#
# Two isolated Python environments, to avoid the pip dependency backtracking
# that happens when dbt and Airflow are installed together:
#   * the Airflow env gets the Snowflake provider + Cosmos, resolved against
#     Airflow's official constraints file (pinned tree -> no backtracking);
#   * dbt-snowflake lives in its own venv (/opt/dbt-venv), so its deps never
#     have to reconcile with Airflow's. Cosmos runs it as an external binary.
FROM apache/airflow:2.10.1-python3.11

ARG AIRFLOW_VERSION=2.10.1
ARG PYTHON_VERSION=3.11

# Airflow-env deps (provider + Cosmos), pinned via the matching constraints file.
COPY requirements.txt /requirements.txt
RUN PIP_CONSTRAINT="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt" \
    pip install --no-cache-dir -r /requirements.txt

# dbt in an isolated virtualenv (no constraints file -> dbt pins its own tree).
# /opt is root-owned, so build the venv as root; pip's default perms leave the
# `dbt` binary world-executable, then we drop back to the airflow user.
ENV DBT_VENV=/opt/dbt-venv
COPY dbt-requirements.txt /dbt-requirements.txt
USER root
RUN python -m venv "${DBT_VENV}" \
    && "${DBT_VENV}/bin/pip" install --no-cache-dir -r /dbt-requirements.txt
USER airflow

# Put the dbt venv on PATH so `dbt` resolves for Cosmos (rendering + deps + run).
# Cosmos also gets the path explicitly via DBT_EXECUTABLE_PATH.
ENV PATH="${DBT_VENV}/bin:${PATH}"
ENV DBT_EXECUTABLE_PATH="${DBT_VENV}/bin/dbt"
