"""nook — agent-friendly Airbnb search + availability CLI (read-only; booking excluded).

Reads Airbnb's public, logged-out data over its internal /api/v3 GraphQL (client.py, via
curl_cffi TLS-match), with cross-process throttle + circuit-breaker and untrusted-text fencing.
The contract surface (output, errors, safety gate, schema, agent, version-check) lives in cli.py
/ output.py / errors.py.
"""

from importlib import metadata


def _version() -> str:
    try:
        return metadata.version("nook")
    except metadata.PackageNotFoundError:
        return "dev"


__version__ = _version()

# Agent CLI Guidelines version this tool conforms to (declared in `schema`). Born pinned.
SPEC = "0.4.0"

# Declared in every read envelope so an agent never mistakes the logged-out public view for a
# complete/authenticated corpus (contract §1 — declare partial/narrowed results).
SCOPE = {"auth": "none", "corpus": "public-logged-out"}
