# Sites service image: the read-only dive site catalogue. Built from services/sites/ only.

# Small Debian image with Python 3.13 (same version as .python-version).
FROM python:3.13-slim

# uv, copied from its official image at a pinned version (same as used locally).
COPY --from=ghcr.io/astral-sh/uv:0.9.15 /uv /usr/local/bin/uv

# Print logs straight away instead of buffering them.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first: exactly the versions in uv.lock (--frozen), no test tools
# (--no-dev). Docker reuses this layer until pyproject.toml or uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Then the code, folder by folder (no "COPY . ." so tests, .venv and local files stay out).
COPY app.py config.py db.py migrate.py health.py ./
COPY sites/ sites/
COPY migrations/ migrations/

# Run as an ordinary user, not root.
RUN useradd --create-home app
USER app

EXPOSE 8000
CMD [".venv/bin/python", "app.py"]
