"""Offline behavioural tests for the three bundled skill tools."""

import json

import pytest

RESULTS = json.dumps([
    {
        "title": "Quantum hardware milestone",
        "url": "https://example.com/a",
        "snippet": "Quantum computing hardware reached a new milestone this year with better error correction across labs.",
        "source": "example.com",
    },
    {
        "title": "Unrelated cooking article",
        "url": "https://example.com/b",
        "snippet": "How to bake bread at home with minimal equipment.",
        "source": "example.com",
    },
])


@pytest.fixture(scope="module")
def tools(request):
    from skill_runtime import SkillRegistry
    from tests.conftest import SKILLS_DIR

    reg = SkillRegistry(SKILLS_DIR).load_all()
    return {name: reg.tools_for(skill)[0] for skill, name in [
        ("web-search", "search_web"),
        ("data-analysis", "analyze_results"),
        ("report-writer", "generate_report"),
    ]}


class TestAnalyzeResults:
    def test_happy_path(self, tools):
        out = json.loads(tools["analyze_results"](
            results_json=RESULTS, topic="quantum computing", focus_areas="hardware"))
        assert 0.0 <= out["confidence"] <= 1.0
        assert out["sources"][0]["relevance"] >= out["sources"][-1]["relevance"]
        assert any("quantum" in f.lower() for f in out["key_findings"])

    def test_malformed_json_returns_error_object(self, tools):
        out = json.loads(tools["analyze_results"](results_json="{oops", topic="x"))
        assert "error" in out

    def test_empty_topic_rejected(self, tools):
        out = json.loads(tools["analyze_results"](results_json=RESULTS, topic="  "))
        assert "error" in out

    def test_empty_results_yield_zero_confidence(self, tools):
        out = json.loads(tools["analyze_results"](results_json="[]", topic="anything"))
        assert out["confidence"] == 0.0

    def test_upstream_error_propagates(self, tools):
        upstream = json.dumps({"error": "rate limited", "query": "q"})
        out = json.loads(tools["analyze_results"](results_json=upstream, topic="x"))
        assert "upstream" in out["error"]

    def test_uncovered_focus_area_reported_as_gap(self, tools):
        out = json.loads(tools["analyze_results"](
            results_json=RESULTS, topic="quantum computing", focus_areas="pricing"))
        assert any("pricing" in g for g in out["gaps"])


class TestGenerateReport:
    def _analysis(self, tools):
        return tools["analyze_results"](
            results_json=RESULTS, topic="quantum computing", focus_areas="hardware")

    def test_happy_path_markdown(self, tools):
        report = tools["generate_report"](
            topic="Quantum computing", analysis_json=self._analysis(tools))
        assert report.startswith("# Research Report: Quantum computing")
        assert "## Key Findings" in report and "## Sources" in report

    def test_plain_format_strips_markup(self, tools):
        report = tools["generate_report"](
            topic="Quantum computing", analysis_json=self._analysis(tools), format="plain")
        assert "##" not in report

    def test_invalid_format_rejected(self, tools):
        out = tools["generate_report"](topic="x", analysis_json="{}", format="pdf")
        assert out.startswith("REPORT ERROR")

    def test_malformed_analysis_rejected(self, tools):
        out = tools["generate_report"](topic="x", analysis_json="nope")
        assert out.startswith("REPORT ERROR")

    def test_upstream_error_propagates(self, tools):
        out = tools["generate_report"](
            topic="x", analysis_json=json.dumps({"error": "upstream broke"}))
        assert "upstream" in out


class TestSearchWeb:
    def test_empty_query_returns_error_without_network(self, tools):
        out = json.loads(tools["search_web"](query="   "))
        assert "error" in out

    def test_network_failure_returns_error_object(self, tools, monkeypatch):
        import sys
        mod = [m for n, m in sys.modules.items()
               if n.endswith("_web_search_search")][0]
        def boom(q, n):
            raise ConnectionError("offline")
        monkeypatch.setattr(mod, "_run_search", boom)
        out = json.loads(tools["search_web"](query="anything"))
        assert "search failed" in out["error"]
