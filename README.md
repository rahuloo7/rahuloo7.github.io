# rahuloo7.github.io

## Hypewire

`hypewire/` is a trending-news page for AI, entertainment, gaming and tech: https://rahuloo7.github.io/hypewire/

- `hypewire/index.html` is the whole site (no build step).
- `hypewire/stories.json` is the feed. A daily scheduled task rewrites it with new stories.

The file also has a top-level `briefing` list of five `{id, text}` lines. Each story has `id`, `title`, `summary`, `why`, `happened`, `next`, `prevHype` (yesterday's score, or null if new), `drivers` (why the hype: a list of `{label, text}`), `meme` (`{top, bottom, take}` for Meme mode), `stats` (key numbers as `{value, label}` for Data mode), `background`, `entities` (companies, people and themes; stories that share one are linked on the map), `category` (`ai`, `entertainment`, `gaming`, `tech`), `hype` (0-100), `source`, `url` and `published` (YYYY-MM-DD).
