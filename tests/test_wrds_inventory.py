from pathlib import Path

from crypto_mlsystem.wrds_inventory import (
    credential_status,
    discover_wrds_inventory,
    load_env_file,
    merged_environment,
    prompt_for_credentials,
    write_wrds_reports,
)


class FakeWRDSConnection:
    def __init__(self):
        self.closed = False

    def list_libraries(self):
        return ["crsp", "optionm", "ravenpack", "datastream", "comp"]

    def list_tables(self, library):
        return {
            "crsp": ["dsi", "stocknames", "etf_holdings"],
            "optionm": ["opprcd", "vix_surface"],
            "ravenpack": ["entity_sentiment"],
            "datastream": ["btc_usd", "dxy_index", "sp500_index", "gold_spot"],
            "comp": ["fundq"],
        }[library]

    def close(self):
        self.closed = True


def test_missing_credentials_do_not_fail_or_import_wrds():
    result = discover_wrds_inventory(env={}, scan_all_tables=True)
    assert result.status == "credentials_missing"
    assert not result.credential_status.ready
    assert result.libraries == []
    assert result.candidates


def test_credential_status_reports_presence_only():
    status = credential_status({"WRDS_USERNAME": "alice", "WRDS_PASSWORD": "secret"})
    assert status.ready
    assert status.label == "available"


def test_fake_connection_discovers_relevant_tables_and_closes():
    fake = FakeWRDSConnection()
    result = discover_wrds_inventory(
        env={"WRDS_USERNAME": "alice", "WRDS_PASSWORD": "secret"},
        connection_factory=lambda: fake,
        scan_all_tables=True,
    )
    assert result.status == "queried"
    assert fake.closed
    assert "datastream" in result.libraries
    assert any(match.table == "btc_usd" and match.category == "crypto market data" for match in result.table_matches)
    assert any(match.category == "options / OptionMetrics" for match in result.table_matches)
    assert any(match.category == "news / RavenPack" for match in result.table_matches)


def test_reports_do_not_write_credential_values(tmp_path):
    result = discover_wrds_inventory(
        env={"WRDS_USERNAME": "alice", "WRDS_PASSWORD": "super-secret-password"},
        connection_factory=FakeWRDSConnection,
        scan_all_tables=True,
    )
    output = write_wrds_reports(result, tmp_path / "wrds_inventory")
    assert (output / "access_setup.md").exists()
    combined = "\n".join(Path(path).read_text(encoding="utf-8") for path in output.glob("*.md"))
    assert "super-secret-password" not in combined
    assert "alice" not in combined
    assert "Macro-Conditioned Crypto Exposure Strategy" in (output / "next_strategy_spec.md").read_text(encoding="utf-8")


def test_prompt_for_credentials_uses_memory_only(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "alice")
    monkeypatch.setattr("crypto_mlsystem.wrds_inventory.getpass", lambda prompt: "secret")
    env = prompt_for_credentials(env={})
    assert env["WRDS_USERNAME"] == "alice"
    assert env["WRDS_PASSWORD"] == "secret"


def test_load_env_file_reads_only_wrds_keys(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "WRDS_USERNAME=alice\nWRDS_PASSWORD='secret'\nOTHER=value\n",
        encoding="utf-8",
    )
    loaded = load_env_file(env_file)
    assert loaded == {"WRDS_USERNAME": "alice", "WRDS_PASSWORD": "secret"}


def test_merged_environment_prefers_env_file_values(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("WRDS_USERNAME=file_user\nWRDS_PASSWORD=file_secret\n", encoding="utf-8")
    env = merged_environment(env={"WRDS_USERNAME": "explicit_user"}, env_file=env_file)
    assert env["WRDS_USERNAME"] == "explicit_user"
    assert env["WRDS_PASSWORD"] == "file_secret"
