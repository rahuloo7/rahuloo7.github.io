# rahuloo7.github.io

## Hypewire

`hypewire/` is a trending-news page for AI, entertainment, gaming and tech: https://rahuloo7.github.io/hypewire/

- `hypewire/index.html` is the whole site (no build step).
- `hypewire/stories.json` is the feed. A daily scheduled task rewrites it with new stories.
- `hypewire/tools/build_pages.py` turns the feed into shareable pages. Run `python3 hypewire/tools/build_pages.py` after changing `stories.json`; it writes `hypewire/s/<id>/` (a static page and a 1200x630 preview image per story, kept for 60 days after a story leaves the feed), `hypewire/og.jpg`, `hypewire/feed.xml` (RSS) and `hypewire/sitemap.xml`. Needs Pillow for the images. Fonts in `hypewire/tools/fonts/` are Latin subsets of Inter (SIL Open Font License).

The file also has a top-level `briefing` list of five `{id, text}` lines. Each story has `id`, `title`, `summary`, `why`, `happened`, `next`, `prevHype` (yesterday's score, or null if new), `drivers` (why the hype: a list of `{label, text}`), `meme` (`{top, bottom, take}` for Meme mode), `stats` (key numbers as `{value, label}` for Data mode), `motif` (which picture to draw: network, chip, money, power, agent, voice, globe, film, screen, game, phone, home, shield, bag, rocket or doc), `background`, `entities` (companies, people and themes; stories that share one are linked on the map), `category` (`ai`, `entertainment`, `gaming`, `tech`), `hype` (0-100), `source`, `url` and `published` (YYYY-MM-DD).
