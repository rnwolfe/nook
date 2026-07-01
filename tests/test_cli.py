import json

import pytest

from nook.cli import Runtime, run
from nook.client import Client
from nook.errors import ExitCode
from nook.output import Writer


@pytest.fixture(autouse=True)
def _no_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")


# --- read commands emit the stable envelope --------------------------------

def test_search_envelope_and_scope(capsys):
    code = run(["search", "Lisbon", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["schemaVersion"] == 1
    assert out["scope"] == {"auth": "none", "corpus": "public-logged-out"}
    assert isinstance(out["data"], list) and out["data"]
    assert out["meta"]["count"] == len(out["data"])


def test_availability_days(capsys):
    code = run(["availability", "12345678", "--months", "3", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    day = out["data"][0]
    for field in ("date", "available", "minNights", "price"):
        assert field in day


def test_listing_get_found(capsys):
    code = run(["listing", "get", "12345678", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["data"]["id"] == "12345678"


def test_listing_get_not_found(capsys):
    code = run(["listing", "get", "does-not-exist", "--json"])
    cap = capsys.readouterr()
    assert code == ExitCode.NOT_FOUND  # 5
    assert "NOT_FOUND" in cap.err
    assert cap.out.strip() == ""


def test_availability_not_found(capsys):
    code = run(["availability", "does-not-exist", "--json"])
    assert code == ExitCode.NOT_FOUND
    assert "NOT_FOUND" in capsys.readouterr().err


def test_place_search(capsys):
    code = run(["place", "search", "Lisbon", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["data"][0]["placeId"]


# --- token economy: --select / --limit apply to the data payload -----------

def test_select_projects_data_items(capsys):
    code = run(["search", "Lisbon", "--json", "--select", "id"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert list(out["data"][0].keys()) == ["id"]


# --- schema / conformance / read-only ---------------------------------------

def test_schema_has_safety_conformance_and_drift_code(capsys):
    code = run(["schema"])
    out = capsys.readouterr().out
    assert code == 0
    s = json.loads(out)
    assert s["readOnly"] is True
    assert s["conformance"]["version"] == "0.4.0"
    assert s["conformance"]["level"] == "Full"
    assert "safety" in s
    assert s["exit_codes"]["mutation_blocked"] == 12
    assert s["exit_codes"]["upstream_drift"] == 20
    assert s["exit_codes"]["rate_limited"] == 7


# --- the mutation gate machinery exists even though no command wires it ------

def test_read_only_gate_machinery():
    """nook has no mutations, but the gate must still function (contract uniformity)."""
    rt = Runtime(fmt="json", allow_mutations=False, dry_run=False, yes=False, force=False,
                 no_input=False, out=Writer(), client=Client())
    with pytest.raises(Exception) as ei:
        rt.guard("hypothetical mutation")
    assert ei.value.exit == ExitCode.MUTATION_BLOCKED  # 12
    # With mutations allowed, the gate is transparent.
    rt.allow_mutations = True
    rt.guard("hypothetical mutation")  # no raise


def test_did_you_mean(capsys):
    code = run(["serch", "Lisbon"])
    err = capsys.readouterr().err
    assert code == 2
    assert "did you mean" in err and "search" in err


def test_agent_prints_skill(capsys):
    code = run(["agent"])
    out = capsys.readouterr().out
    assert code == 0
    assert "nook" in out.lower()


# --- version --check (update awareness + SSRF guard) ------------------------

def test_version_check(capsys, monkeypatch):
    import http.server
    import threading

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"tag_name": "v999.0.0"}')

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        monkeypatch.setenv("NOOK_RELEASES_URL", f"http://127.0.0.1:{srv.server_address[1]}/latest")
        code = run(["version", "--check", "--json"])
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["latest"] == "v999.0.0"
        assert "upgrade" in out
    finally:
        srv.shutdown()


def test_version_check_rejects_unsafe_scheme():
    from nook.cli import _safe_release_url

    assert _safe_release_url("file:///etc/passwd") is None
    assert _safe_release_url("http://169.254.169.254/latest") is None
    assert _safe_release_url("ftp://example.com/") is None
    assert _safe_release_url("https://example.com/r") == "https://example.com/r"
    assert _safe_release_url("http://127.0.0.1:8080/x") == "http://127.0.0.1:8080/x"


def test_version_check_fail_silent(capsys, monkeypatch):
    monkeypatch.setenv("NOOK_RELEASES_URL", "http://127.0.0.1:0")  # unreachable → fail-silent
    code = run(["version", "--check", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["updateAvailable"] is False
