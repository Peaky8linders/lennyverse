# LennyVerse Compilation Schema

## Node Types

### concept
Required frontmatter: title, domain, type, related, confidence
Optional: builds_on, contrasts_with, appears_in, taught_by, status

### guest
Required frontmatter: title, type, domains
Optional: known_for, episodes, frameworks_taught

### source
Required frontmatter: title, type, source_type (podcast|newsletter), date
Optional: guest, topics, word_count

### domain
Required frontmatter: title, type, color
Optional: description, top_concepts

## Edge Types

| Type | Direction | Source -> Target |
|------|-----------|------------------|
| teaches | directed | guest -> concept |
| appears_in | directed | guest -> source |
| belongs_to | directed | concept -> domain |
| builds_on | directed | concept -> concept |
| contrasts_with | undirected | concept <-> concept |
| debates | undirected | guest <-> guest |
| mentioned_in | directed | concept -> source |

## Edge Provenance Tags

- EXTRACTED: found directly in source content
- INFERRED: reasonable inference, confidence 0.0-1.0
- AMBIGUOUS: flagged for review

## Ingestion Rules

- Minimum confidence threshold: 0.6
- Duplicate detection: title similarity > 0.8 AND same domain -> enrich existing page
- Every wiki page must have at least 1 related link and a domain assignment
- New concepts without clear domain -> assign "Uncategorized", flag for review

## Domain Colors

| Domain | Color |
|--------|-------|
| Growth | #22c55e |
| Product Strategy | #3b82f6 |
| Leadership | #a855f7 |
| Career | #f59e0b |
| Engineering | #ef4444 |
| Design | #ec4899 |
| Uncategorized | #6b7280 |
