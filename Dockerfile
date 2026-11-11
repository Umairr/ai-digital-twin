FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    TWIN_DB_PATH=/data/twin.db

# Dependencies first (cached layer), then the app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .

# FAQs, captured leads and questions live in /data - mount a volume to keep them
RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 7860
CMD ["uv", "run", "--frozen", "app.py"]
