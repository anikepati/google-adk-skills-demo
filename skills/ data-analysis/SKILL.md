---
name: data-analysis
description: Analyses a JSON array of web search results to extract key findings, named entities, source relevance scores, and a confidence rating. Use after web-search to turn raw search hits into a structured analysis before report writing, or whenever search-result JSON needs to be distilled into insights.
license: MIT
compatibility: Requires Python 3.10+. No network access needed.
metadata:
  author: google-adk-skills-demo
  version: "2.0.0"
  category: analytics
allowed-tools: analyze_results
---

# Data Analysis Skill

You are performing the analysis stage of a research pipeline. You receive raw
search results as JSON from the previous stage and produce a structured
analysis for the report writer.

## Instructions

1. Take the search-results JSON string from the previous stage exactly as
   given — do not re-serialise or prettify it first.
2. Call the `analyze_results` tool:
   - `results_json` (string, required): the JSON array of search results
   - `topic` (string, required): the original research topic, used for
     relevance scoring
   - `focus_areas` (string, optional): comma-separated aspects to emphasise,
     e.g. `"hardware,error correction"`
3. The tool returns an analysis JSON object. The full schema is in
   [references/analysis_schema.json](references/analysis_schema.json). How
   relevance and confidence are scored is documented in
   [references/scoring_rubric.md](references/scoring_rubric.md).
4. Return the complete analysis JSON verbatim — do not summarise or truncate.
   The report writer needs every field, including `gaps` and `confidence`.

## Edge cases

- **Malformed input JSON**: the tool raises a clear error. Report the error
  and ask the previous stage to re-emit its results; do not hand-repair JSON.
- **Empty results array**: the tool still returns a valid analysis with
  `confidence: 0.0` and an explanatory summary. Pass it through.
- **Focus areas with no coverage**: these appear in the `gaps` field — leave
  them in; the report surfaces them as research gaps.

## Example

Tool call:
`analyze_results(results_json="[...]", topic="quantum computing", focus_areas="hardware")`
Output: the raw analysis JSON object returned by the tool, nothing else.
