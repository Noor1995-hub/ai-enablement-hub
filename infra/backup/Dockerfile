# Image for the ai-enablement-hub database backup/restore jobs.
# Base is the official postgres 18 image so pg_dump/pg_restore match the
# server's major version (pg_dump refuses to dump from a NEWER server).
# Build context is this directory: `az acr build ... infra/backup`.
FROM postgres:18

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3-minimal python3-pip \
 && pip3 install --no-cache-dir --break-system-packages azure-identity azure-storage-blob \
 && apt-get purge -y python3-pip \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY dumpcheck.py backup.py restore.py ./
USER postgres
ENTRYPOINT ["python3", "backup.py"]
