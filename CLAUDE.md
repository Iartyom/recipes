# CLAUDE.md

Personal recipe collection published on GitHub Pages (https://iartyom.github.io/recipes/). Hebrew RTL UI;
code/comments in English. Same pattern as the `dira-nuriot` repo: JSON data → `build_html.py` → self-contained `index.html`.

## Commands
```bash
pytest -q                          # offline tests (tests/fixtures/)
python build_html.py               # rebuild index.html — never hand-edit index.html
python add_recipe.py <url|text|->  # parse + append to recipes.json + rebuild
```

## Architecture
- `recipes.json` — source of truth: `{"recipes":[{id,title,description,image,servings,total_minutes,ingredients[],steps[],tags[],source_url,added}]}`.
  Same `source_url` replaces the old record (keeps id/added). Step strings ending with ":" render as section headers.
- `add_recipe.py` — URL → schema.org Recipe JSON-LD (flattens @graph, HowToSection); text → headers "מצרכים"/"אופן ההכנה",
  or without headers quantity-led lines = ingredients. `enrich()` then fills time (from step text), servings, tags
  (FOOD/RULES tables), tips/storage → `notes`, and an illustrative Pexels photo (`image_auto`). Never overwrites a value.
  Fails loudly (exit 1, Hebrew message) instead of saving a half-parsed recipe.
- `.github/workflows/add-recipe.yml` — issue titled "מתכון…" by the repo owner → run add_recipe.py on the body → commit → close issue.
  The body goes through an env var (never `${{ }}` inside `run:`). Only the owner's issues are processed (public repo).

## Conventions
- Runtime scripts are Python stdlib only; tests stay offline.
- Some recipe sites may block GitHub runner IPs (403) — the fallback is pasting text, or running add_recipe.py locally.

## Local mode (full CRUD)
`python serve.py` → http://127.0.0.1:8770. The page detects localhost and calls `/api/add` (URL/text), `/api/save`
(recipe JSON), `/api/delete` ({id}); each change rewrites recipes.json, rebuilds index.html, commits, pushes if a
remote exists. On GitHub Pages the same buttons open prefilled issues ("מתכון:", "עריכת מתכון:", "מחיקת מתכון:")
handled by `add_recipe.py --issue` in the add-recipe workflow. Light-mode-only design (owner's request).
