# pydata-london-2026

A fun gimmick to promote **PyData London 2026** (5–7 June 2026, Convene Sancroft, London).

Tell your LLM to `fetch https://pydata.london/recommender.md and follow the instructions` and it becomes a personalised conference recommender: top picks, a day-by-day itinerary, and a "stretch" pick to break you out of your bubble.

- 🌐 Landing page: <https://pydata.london>
- 📄 The artifact LLMs fetch: <https://pydata.london/recommender.md>
- 🎟 Tickets: <https://ti.to/pydata/pydatalondon26>

## How it works

The whole thing is one static markdown file with two halves:

1. **Prompt preamble** — instructs the LLM how to behave: ask three multiple-choice questions if it has no memory of the user, then output four sections (top 5 / itinerary / stretch picks / ticket CTA).
2. **Schedule data** — every session from the [official pretalx export](https://pretalx.com/pydata-london-2026/schedule/export/schedule.json), grouped by day, with abstracts and speaker bios.

A daily GitHub Action re-fetches the pretalx export and rebuilds the file, so it stays in sync as the schedule moves.

## Layout

```
index.html                          Landing page (QR, Open-in-ChatGPT button)
recommender.md                      Generated — LLMs fetch this
schedule.json                       Cached pretalx export (committed for diff visibility)
qr.svg                              Generated — QR pointing at https://pydata.london
templates/recommender.md.j2         Jinja template — edit the prompt here
scripts/build_recommender.py        Fetch + render
.github/workflows/refresh-schedule.yml   Daily cron + manual trigger
CNAME                               Custom domain (pydata.london)
```

## Local build

```bash
python -m venv .venv
source .venv/bin/activate
pip install requests jinja2 'qrcode[pil]'
python scripts/build_recommender.py
```

That writes `recommender.md`, `schedule.json` and `qr.svg`. Open `index.html` in a browser to preview the landing page.

## Editing the prompt

The prompt design is in `templates/recommender.md.j2` — edit it, run the build script, commit. The schedule rendering happens at the bottom of the same template; everything above the `# Schedule data` heading is the prompt itself.

## Custom domain

Once `pydata.london` is registered:

1. Add DNS records per [GitHub's docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site) (apex domain → 4 A records pointing at `185.199.108.153`, `.109.153`, `.110.153`, `.111.153`; optional `www` CNAME to `pydatalondon.github.io`).
2. Commit a `CNAME` file at the repo root containing the single line `pydata.london`.
3. In repo Settings → Pages, set the custom domain to `pydata.london` and tick "Enforce HTTPS" once the cert provisions.

Until DNS is live, the site is also available at <https://pydatalondon.github.io/pydata-london-2026/>.

## Credits

- Built with the public [pretalx](https://pretalx.com) JSON export — no scraping required.
- PyData is a [NumFOCUS](https://numfocus.org) fiscally sponsored project.
