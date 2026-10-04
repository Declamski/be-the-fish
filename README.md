# Be the Fish

A logbook web app for scuba divers, freedivers and spearfishers. Flask + SQLite, single
process. Design decisions are in [ADR.md](ADR.md), and AI use is in [AI_USAGE.md](AI_USAGE.md).

## Setup

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Declamski/be-the-fish.git
cd be-the-fish
uv sync
```

## Run

```bash
uv run python app.py
```

Then open http://localhost:8000 and sign up. No other setup is needed: the database and
its tables are created automatically on first start.

## Configuration

All settings are optional environment variables (no `.env` file needed).

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | Port to listen on (the app binds to `0.0.0.0`) |
| `DATA_DIR` | `./data` | Folder for the database, created if missing |
| `SECRET_KEY` | `dev-secret-key-change-me` | Signs the login cookie; set your own outside local use |

The SQLite database is stored at **`$DATA_DIR/divelog.db`**.

```bash
PORT=9000 DATA_DIR=/tmp/divelog uv run python app.py
```

## Tests and coverage

```bash
uv run pytest --cov=dives --cov=sites --cov=feed --cov-report=term-missing
```

Result: **128 passed, 74% total coverage.** The business logic (`service.py` files and
the CSV importer) is at 95–100%. The thin `routes.py` files make up most of the
uncovered lines; see ADR-4.
