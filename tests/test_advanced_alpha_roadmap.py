import json

from crypto_mlsystem import advanced_alpha_roadmap as aar


def test_advanced_alpha_roadmap_writes_reports_without_strategy_changes(tmp_path):
    roadmap = aar.write_advanced_alpha_roadmap(tmp_path)

    assert roadmap["status"]["baseline"] == aar.BASELINE_NAME
    assert aar.BASELINE_NAME in (tmp_path / "executive_summary.md").read_text(encoding="utf-8")
    assert "does **not** modify" in (tmp_path / "executive_summary.md").read_text(encoding="utf-8")
    assert "No best-cell selection" in (tmp_path / "validation_protocol.md").read_text(encoding="utf-8")
    assert "Level 4" in (tmp_path / "model_hierarchy.md").read_text(encoding="utf-8")
    assert "Institutional-flow expansion overlay" in (tmp_path / "study_templates.md").read_text(encoding="utf-8")

    expected = {
        "executive_summary.md",
        "data_acquisition_priorities.md",
        "model_hierarchy.md",
        "validation_protocol.md",
        "study_templates.md",
        "current_evidence_matrix.md",
        "final_recommendation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})

    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert payload["status"]["baseline"] == aar.BASELINE_NAME
    assert any(row["level"] == "LLM research" for row in payload["model_hierarchy"])
