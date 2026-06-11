# Web Search Guidelines

## Writing Effective Queries

- Use specific, concrete terms rather than vague phrases.
- Include a year (e.g., "2025") for time-sensitive topics.
- For comparisons, use "vs" or "compared to" (e.g., "Python vs Go performance 2025").
- For technical lookups, include the product/library name and version.

## Interpreting Results

- `snippet` may be truncated; always fetch the full page for citation-critical work.
- `source` domain can hint at credibility (.gov, .edu, established news domains).
- Cross-reference multiple results before treating a fact as confirmed.

## Rate Limits

DuckDuckGo enforces informal rate limits. If you receive empty results:
1. Wait 5–10 seconds between calls.
2. Reduce `max_results`.
3. Consider switching to Google Custom Search API for production workloads.
