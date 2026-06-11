---
name: web-search
description: Searches the web for current information on a topic and returns structured JSON results with titles, URLs, snippets, and source domains. Use when the user needs up-to-date facts, news, or research on any subject, or as the first stage of a research pipeline before analysis and report writing.
license: MIT
compatibility: Requires Python 3.10+ and internet access. Uses DuckDuckGo (no API key needed).
metadata:
  author: google-adk-skills-demo
  version: "2.0.0"
  category: information-retrieval
allowed-tools: search_web
---

# Web Search Skill

You are performing the web-search stage of a research pipeline. Your job is to
find relevant, current sources for the given topic and hand the raw results to
the next stage unmodified.

## Instructions

1. Take the user's research topic and formulate a focused search query.
   Read [references/search_guidelines.md](references/search_guidelines.md) if
   the topic is ambiguous or time-sensitive.
2. Call the `search_web` tool:
   - `query` (string, required): the search query
   - `max_results` (integer, optional, default 5): how many results to return
3. The tool returns a JSON array of result objects. The exact schema is in
   [assets/result_template.json](assets/result_template.json):
   `[{"title": ..., "url": ..., "snippet": ..., "source": ...}]`
4. Return the complete JSON string verbatim. Do not summarise, reorder, or
   drop results — downstream analysis depends on the full payload.

## Edge cases

- **Empty results**: DuckDuckGo rate-limits informally. Retry once with a
  simplified query before reporting failure.
- **Ambiguous topics**: prefer adding a year or domain qualifier over guessing
  (e.g. "jaguar speed animal" not "jaguar speed").
- **Non-English topics**: search in the topic's language; do not translate.

## Example

Input topic: `AI trends in 2025`
Tool call: `search_web(query="AI trends 2025", max_results=5)`
Output: the raw JSON array returned by the tool, nothing else.
