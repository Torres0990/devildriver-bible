# DevilDriver — Design Bible

The structured source of truth for **DevilDriver**, Sebastian's 3v3 team action game:
two teams, two demons dueling in a vertical arena, souls as the tiebreaker.

**Live site:** https://devildriver-bible.pages.dev
**AI context:** https://devildriver-bible.pages.dev/llms.txt

## For AI contributors (Gemini, Muse, etc.)

`devildriver.json` is the single source of truth. **Notes are the unit of change.**

- **Add knowledge** (a new Style, mechanic, zone): append an object to `notes` with a unique
  kebab-case `id`, a `category` from the categories list (or add a new category — the site
  generates its page automatically), `status` of `locked` | `decided` | `open`, and an `updated` date.
- **Edit**: modify the note in place, bump `updated`.
- **Never** change the meaning of a `locked` note without Sebastian's explicit approval.
- Style kits live in category `styles`, one note per Style, following the style-kit schema
  in the `style-system` note.
- Body markup: blank line = paragraph, lines starting with `- ` = bullets.

After editing: `python3 build.py` regenerates the HTML + `llms.txt`; `python3 deploy.py`
publishes to Cloudflare Pages.

## Repo layout

| File | What it is |
|---|---|
| `devildriver.json` | The bible. Notes grouped by category. Edit this. |
| `build.py` | Generates the static site from the JSON. No dependencies. |
| `deploy.py` | Publishes `site/` to Cloudflare Pages (direct upload). |
| `assets/` | Concept art referenced by the demons page. |
