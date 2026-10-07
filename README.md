# rahuloo7.github.io

## Hypewire

`hypewire/` is a trending-news page for AI, entertainment, gaming and tech: https://rahuloo7.github.io/hypewire/

- `hypewire/index.html` is the whole site (no build step).
- `hypewire/stories.json` is the feed. A daily scheduled task rewrites it with new stories.

Each story has `id`, `title`, `summary`, `why`, `category` (`ai`, `entertainment`, `gaming`, `tech`), `hype` (0-100), `source`, `url` and `published` (YYYY-MM-DD).
