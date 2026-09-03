FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# No pip dependencies (pyproject.toml declares none -- pure stdlib), so no install step.
COPY src ./src
COPY prototype ./prototype

# .workbench/ (the SQLite DB) is volume-mounted in docker-compose, not baked into the image,
# so real ticket/run/verification history survives container rebuilds.
RUN mkdir -p /app/.workbench

EXPOSE 8088

CMD ["python", "prototype/ui_server.py"]
