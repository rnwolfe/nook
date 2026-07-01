"""nook — agent-friendly Airbnb search + availability CLI (read-only; booking excluded).

Scaffolded by cli-scaffold from the Python (Click) reference template. The contract surface
(output, errors, safety gate, schema, agent, version-check) is correct as-is; client.py is a
placeholder that cli-implement replaces with the real Airbnb GraphQL client (curl_cffi).
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
