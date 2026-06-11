---
name: report-writer
description: Renders a polished Markdown research report from a structured analysis JSON object, with an executive summary, numbered key findings, a cited-sources table, and a confidence assessment. Use as the final stage of a research pipeline after web-search and data-analysis have produced an analysis.
license: MIT
compatibility: Requires Python 3.10+ and Jinja2. No network access needed.
metadata:
  author: google-adk-skills-demo
  version: "2.0.0"
  category: document-generation
allowed-tools: generate_report
---

# Report Writer Skill

You are performing the final stage of a research pipeline. You receive a
structured analysis JSON and render it into the report the user will read.

## Instructions

1. Take the analysis JSON string from the previous stage exactly as given.
2. Call the `generate_report` tool:
   - `topic` (string, required): the original research question; becomes the
     report title
   - `analysis_json` (string, required): the analysis JSON from data-analysis
   - `format` (string, optional, default `markdown`): `markdown` or `plain`
3. The tool renders [assets/report_template.md](assets/report_template.md)
   (a Jinja2 template) with the analysis data. Style and length expectations
   are in [references/report_guidelines.md](references/report_guidelines.md).
4. Return the complete rendered report verbatim. Do not add commentary before
   or after it.

## Edge cases

- **Missing analysis fields**: the template tolerates absent optional fields
  (entities, gaps); never fabricate values to fill them.
- **Low confidence (< 0.5)**: the report flags this automatically — do not
  soften or remove the warning.
- **Plain format**: only use `format="plain"` when the user explicitly asked
  for plain text.

## Example

Tool call:
`generate_report(topic="AI trends in 2025", analysis_json="{...}")`
Output: the rendered Markdown report, nothing else.
