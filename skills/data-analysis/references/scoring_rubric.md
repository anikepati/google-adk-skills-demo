# Scoring Rubric

## Source relevance (per source, 0.0–1.0)

Fraction of topic keywords appearing in the source's title + snippet, capped
at 1.0. A score of 1.0 means every topic word matched; 0.0 means none did.

| Score     | Interpretation                          |
|-----------|------------------------------------------|
| 0.8–1.0   | Directly on-topic                        |
| 0.4–0.79  | Related; verify before citing            |
| < 0.4     | Tangential; excluded from top sources    |

## Confidence (analysis-level, 0.0–1.0)

Weighted blend:

```
confidence = 0.6 × mean(source relevance) + 0.4 × min(findings / 5, 1.0)
```

- The relevance term rewards on-topic sources.
- The findings term rewards extraction density, saturating at 5 findings.

| Score     | Report behaviour                                  |
|-----------|----------------------------------------------------|
| ≥ 0.75    | "High confidence" banner                            |
| 0.50–0.74 | "Medium confidence — cross-verify" banner           |
| < 0.50    | "Low confidence — refine the search query" banner   |
