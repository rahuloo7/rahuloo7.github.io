#!/usr/bin/env python3
"""Build Hypewire's shareable pages from hypewire/stories.json.

Writes, inside hypewire/:
  s/<id>/index.html   one static page per story, with share previews (Open Graph and Twitter cards)
  s/<id>/card.jpg     the 1200x630 preview image for that story
  s/archive.json      every story seen in the last KEEP_DAYS days, so shared links keep working after a story leaves the feed
  og.jpg              the home page preview image ("Today in five")
  feed.xml            RSS feed of today's stories
  sitemap.xml         home page plus every story page

Run from anywhere:  python3 hypewire/tools/build_pages.py
Needs Pillow for the images. Without it, pages, feed and sitemap are still written and existing images are kept.
"""
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
from email.utils import format_datetime

SITE = "https://rahuloo7.github.io/hypewire/"
KEEP_DAYS = 60
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # hypewire/
FONTS = os.path.join(HERE, "fonts")
S_DIR = os.path.join(ROOT, "s")
ARCHIVE = os.path.join(S_DIR, "archive.json")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")

CATS = {"ai": "AI", "entertainment": "Entertainment", "gaming": "Gaming", "tech": "Tech"}
# Light-mode art tokens from index.html: (tint a, tint b, ink, accent)
ART = {
    "ai": ("#EEEAFF", "#CFC8FB", "#4B3FC4", "#8E84F0"),
    "entertainment": ("#FFEEE4", "#FFCDD9", "#C2325F", "#FF8F6B"),
    "gaming": ("#E6F9EF", "#BFEEDA", "#0F7A5A", "#3CC79A"),
    "tech": ("#E8F3FF", "#C2DEFB", "#1D5FB8", "#5AA5F0"),
}
FG, MUTED, HEAT = "#1A1730", "#4E4A68", "#D81B66"
BANDS = [(90, "Everywhere"), (75, "Big"), (60, "Building"), (0, "On the radar")]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def band(h):
    return next(n for lo, n in BANDS if h >= lo)


def nice_date(iso):
    try:
        d = dt.date.fromisoformat(iso)
        return d.strftime("%b %-d, %Y")
    except Exception:
        return ""


# ---------------------------------------------------------------- images
def load_pil():
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter  # noqa: F401
        return True
    except Exception:
        return False


def font(name, size):
    from PIL import ImageFont
    for p in (os.path.join(FONTS, name + ".otf"), "/usr/share/fonts/opentype/inter/" + name + ".otf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def wrap(draw, text, fnt, width, max_lines):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textlength(last + "…", font=fnt) > width:
            last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
        lines[-1] = last.rstrip(",;:") + "…"
    return lines


def canvas(cat):
    """Soft pastel background with a glow and one diagonal band, echoing the site's artwork."""
    from PIL import Image, ImageDraw, ImageFilter
    W, H = 1200, 630
    a, b, ink, acc = (hexrgb(c) for c in ART.get(cat, ART["tech"]))
    sw, sh = 120, 63
    small = Image.new("RGB", (sw, sh))
    px = small.load()
    for y in range(sh):
        for x in range(sw):
            t = (x / sw) * .65 + (y / sh) * .35
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    img = small.resize((W, H), Image.BILINEAR)
    img = img.convert("RGBA")
    # Glows: blur only the alpha mask so the edges fade to the tint, not to grey.
    for box, col, alpha in (((-260, -320, 640, 520), (255, 255, 255), 150), ((760, 260, 1460, 900), acc, 60)):
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).ellipse(box, fill=alpha)
        mask = mask.filter(ImageFilter.GaussianBlur(90))
        img = Image.composite(Image.new("RGBA", (W, H), col + (255,)), img, mask)
    band_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(band_l).polygon([(880, 0), (980, 0), (820, H), (720, H)], fill=(255, 255, 255, 70))
    img = Image.alpha_composite(img, band_l)
    # faint dot texture
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    for y in range(12, H, 26):
        for x in range(12 + (y // 26 % 2) * 13, W, 26):
            dd.ellipse((x - 1.4, y - 1.4, x + 1.4, y + 1.4), fill=ink + (18,))
    return Image.alpha_composite(img, dots), ink


def wordmark(d, x, y, size=40):
    f = font("InterDisplay-Bold", size)
    d.text((x, y), "Hype", font=f, fill=FG)
    d.text((x + d.textlength("Hype", font=f), y), "wire", font=f, fill=HEAT)


def story_card(s, path):
    from PIL import ImageDraw
    img, ink = canvas(s["category"])
    d = ImageDraw.Draw(img)
    wordmark(d, 72, 60)
    cat = CATS.get(s["category"], "Tech").upper()
    fc = font("Inter-SemiBold", 24)
    d.text((1128 - d.textlength(cat, font=fc), 70), cat, font=fc, fill=ink)
    size, lines = 72, []
    for size in (72, 64, 56):
        ft = font("InterDisplay-Bold", size)
        lines = wrap(d, s["title"], ft, 1040, 3)
        if not lines[-1].endswith("…") or size == 56:
            break
    y = 168 if len(lines) == 3 else 196
    for ln in lines:
        d.text((72, y), ln, font=ft, fill=FG)
        y += int(size * 1.14)
    # footer: heat pill + source and date
    fh = font("Inter-SemiBold", 26)
    label = "Heat %d · %s" % (s["hype"], band(s["hype"]))
    w = d.textlength(label, font=fh)
    d.rounded_rectangle((72, 516, 72 + w + 44, 568), radius=26, fill=HEAT)
    d.text((94, 526), label, font=fh, fill="#FFFFFF")
    fm = font("Inter-Medium", 24)
    meta = " · ".join(x for x in ("via " + s["source"] if s.get("source") else "", nice_date(s.get("published", ""))) if x)
    d.text((72 + w + 68, 529), meta, font=fm, fill=MUTED)
    img.convert("RGB").save(path, "JPEG", quality=86, optimize=True, progressive=True)


def home_card(data, byid, path):
    from PIL import ImageDraw
    img, ink = canvas("ai")
    d = ImageDraw.Draw(img)
    wordmark(d, 72, 52, 44)
    ft = font("InterDisplay-Bold", 30)
    t = "Today in five"
    d.text((1128 - d.textlength(t, font=ft), 60), t, font=ft, fill=FG)
    fn, fl = font("InterDisplay-Bold", 30), font("Inter-SemiBold", 26)
    y, n = 140, 0
    for b in (data.get("briefing") or []):
        if b.get("id") not in byid or n == 5:
            continue
        n += 1
        d.text((72, y), str(n), font=fn, fill=HEAT)
        lines = wrap(d, b.get("text", ""), fl, 1000, 2)
        for i, ln in enumerate(lines):
            d.text((118, y + 3 + i * 33), ln, font=fl, fill=FG)
        y += 33 * len(lines) + 30
    img.convert("RGB").save(path, "JPEG", quality=86, optimize=True, progressive=True)


# ---------------------------------------------------------------- pages
CSS = """
:root{--bg:#FBFBFD;--surface:#FFF;--fg:#1A1730;--muted:#66627F;--line:#E7E5EF;--chip:#EEEDF4;--heat:#D81B66;--cool:#3B2FB5;
--display:"Bricolage Grotesque","Arial Narrow",system-ui,sans-serif;--body:"Figtree",system-ui,-apple-system,"Segoe UI",sans-serif;--mono:"JetBrains Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#131120;--surface:#1C1930;--fg:#EDEBF7;--muted:#A29EBD;--line:#2B2843;--chip:#221F38;--heat:#FF5C97;--cool:#A99FFF;color-scheme:dark}}
*,*::before,*::after{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 var(--body);-webkit-font-smoothing:antialiased}
a{color:inherit}
:focus-visible{outline:2px solid var(--cool);outline-offset:2px}
.wrap{max-width:720px;margin:0 auto;padding:20px 20px 64px}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;padding-bottom:16px;border-bottom:1px solid var(--line)}
.logo{font:800 1.5rem/1 var(--display);letter-spacing:-.03em;text-decoration:none}.logo span{color:var(--heat)}
.top a.home{font-size:.9rem;color:var(--muted);text-decoration:none}.top a.home:hover{color:var(--fg)}
.note{margin:20px 0 0;padding:10px 14px;border-radius:10px;background:var(--chip);color:var(--muted);font-size:.9rem}
.kick{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 10px;margin:28px 0 8px;font-size:.85rem;color:var(--muted)}
.kick b{color:var(--fg);font-weight:600}.heat{margin-left:auto;font:700 1rem var(--mono);color:var(--heat)}
h1{font:800 clamp(1.8rem,5vw,2.6rem)/1.1 var(--display);letter-spacing:-.025em;margin:0 0 12px;text-wrap:balance}
.lead{font-size:1.15rem;color:var(--muted);margin:0 0 20px}
.hero{display:block;width:100%;height:auto;border-radius:14px;margin:4px 0 8px;aspect-ratio:1200/630;object-fit:cover}
h2{font:700 1.1rem/1.3 var(--display);margin:28px 0 8px}
p{margin:0}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}
.stat{background:var(--chip);border-radius:12px;padding:10px 12px}.stat b{display:block;font:700 1.2rem var(--mono)}.stat span{font-size:.82rem;color:var(--muted)}
ul.drivers{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px}
ul.drivers li{display:grid;grid-template-columns:130px 1fr;gap:12px}ul.drivers b{font-weight:600}
.take{border-left:3px solid var(--heat);padding:4px 0 4px 14px;font:600 1.05rem/1.4 var(--display)}
.take small{display:block;margin-top:4px;font:400 .8rem var(--body);color:var(--muted)}
.acts{display:flex;flex-wrap:wrap;gap:10px;margin-top:28px}
.btn{display:inline-flex;align-items:center;gap:6px;padding:10px 18px;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--fg);font:600 .95rem var(--body);text-decoration:none;cursor:pointer}
.btn.primary{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.chips{display:flex;flex-wrap:wrap;gap:6px}.chip{background:var(--chip);border-radius:999px;padding:3px 10px;font-size:.82rem}
.rel{list-style:none;padding:0;margin:0;display:flex;flex-direction:column}
.rel li{border-top:1px solid var(--line)}.rel a{display:flex;gap:12px;padding:10px 0;text-decoration:none}.rel a:hover span{text-decoration:underline}
.rel b{font:700 .9rem var(--mono);color:var(--heat);min-width:28px}
footer{margin-top:48px;padding-top:16px;border-top:1px solid var(--line);font-size:.82rem;color:var(--muted)}
@media (max-width:560px){ul.drivers li{grid-template-columns:1fr;gap:0}.heat{margin-left:0}}
"""

SHARE_JS = """
document.getElementById('share').addEventListener('click',function(){var b=this,u=location.href.split('#')[0],t=document.title;
if(navigator.share){navigator.share({title:t,url:u}).catch(function(){});return;}
var done=function(){b.textContent='Link copied';setTimeout(function(){b.textContent='Share';},1800);};
if(navigator.clipboard){navigator.clipboard.writeText(u).then(done,function(){prompt('Copy this link',u);});}else{prompt('Copy this link',u);}});
"""


def head(title, desc, url, image, kind="article", extra=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:site_name" content="Hypewire">
<meta property="og:type" content="{kind}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{esc(image)}">
<link rel="alternate" type="application/rss+xml" title="Hypewire" href="{SITE}feed.xml">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23D81B66'/%3E%3Cpath d='M18 16h8v12h12V16h8v32h-8V36H26v12h-8z' fill='%23fff'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=Figtree:wght@400;600&family=JetBrains+Mono:wght@700&display=swap">
<style>{CSS}</style>
{extra}
</head>
"""


def story_page(s, live, by_entity, current):
    url = f"{SITE}s/{s['id']}/"
    img = f"{SITE}s/{s['id']}/card.jpg"
    title = s["title"]
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": title[:110], "description": s["summary"],
          "image": [img], "datePublished": s.get("published", ""), "url": url,
          "publisher": {"@type": "Organization", "name": "Hypewire"},
          "isBasedOn": s.get("url", ""), "about": [{"@type": "Thing", "name": e} for e in s.get("entities", [])]}
    out = [head(f"{title} | Hypewire", s["summary"], url, img,
                extra='<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>")]
    out.append('<body>\n<div class="wrap">\n<header class="top"><a class="logo" href="../../">Hype<span>wire</span></a>'
               '<a class="home" href="../../">Today\'s stories →</a></header>\n<main>\n')
    if not live:
        out.append(f'<p class="note">This story is from {esc(nice_date(s.get("published","")) or "an earlier day")} and has left today\'s feed. '
                   'Details were current when it was last updated.</p>\n')
    cat = CATS.get(s["category"], "Tech")
    out.append(f'<div class="kick"><b>{esc(cat)}</b><span>{esc(nice_date(s.get("published","")))}</span>'
               f'<span>{esc(band(s["hype"]))}</span><span class="heat" title="Heat: our estimate of how widely it is covered">{s["hype"]}</span></div>\n')
    out.append(f'<h1>{esc(title)}</h1>\n<p class="lead">{esc(s["summary"])}</p>\n')
    if s.get("stats"):
        out.append('<h2>By the numbers</h2>\n<div class="stats">' + "".join(
            f'<div class="stat"><b>{esc(x["value"])}</b><span>{esc(x["label"])}</span></div>' for x in s["stats"]) + "</div>\n")
    out.append(f'<h2>What happened</h2>\n<p>{esc(s.get("happened") or s["summary"])}</p>\n')
    if s.get("why"):
        out.append(f'<h2>Why it matters</h2>\n<p>{esc(s["why"])}</p>\n')
    if s.get("drivers"):
        out.append('<h2>Why the hype</h2>\n<ul class="drivers">' + "".join(
            f'<li><b>{esc(d["label"])}</b><span>{esc(d["text"])}</span></li>' for d in s["drivers"]) + "</ul>\n")
    if s.get("background"):
        out.append(f'<h2>Background</h2>\n<p>{esc(s["background"])}</p>\n')
    if s.get("next"):
        out.append(f'<h2>What to watch next</h2>\n<p>{esc(s["next"])}</p>\n')
    m = s.get("meme") or {}
    if m.get("take"):
        out.append(f'<h2>The take</h2>\n<p class="take">{esc(m["take"])}<small>A joke written by Claude. The facts above are unchanged.</small></p>\n')
    out.append('<div class="acts">')
    if str(s.get("url", "")).startswith("https://"):
        out.append(f'<a class="btn primary" href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">Read it at {esc(s.get("source") or "the source")} ↗</a>')
    out.append('<button class="btn" type="button" id="share">Share</button>')
    if live:
        out.append(f'<a class="btn" href="../../#s-{esc(s["id"])}">Open in Hypewire</a>')
    out.append("</div>\n")
    if s.get("entities"):
        out.append('<h2>Connections</h2>\n<div class="chips">' + "".join(f'<span class="chip">{esc(e)}</span>' for e in s["entities"]) + "</div>\n")
    rel, seen = [], {s["id"]}
    for e in s.get("entities", []):
        for x in by_entity.get(e, []):
            if x["id"] not in seen:
                seen.add(x["id"]); rel.append(x)
    for x in sorted((x for x in current if x["category"] == s["category"] and x["id"] not in seen), key=lambda x: -x["hype"]):
        if len(rel) >= 6:
            break
        seen.add(x["id"]); rel.append(x)
    if rel:
        out.append('<h2>Related on Hypewire</h2>\n<ul class="rel">' + "".join(
            f'<li><a href="../{esc(x["id"])}/"><b>{x["hype"]}</b><span>{esc(x["title"])}</span></a></li>' for x in rel[:6]) + "</ul>\n")
    out.append('</main>\n<footer>Hypewire summaries are short rewrites of published reports; follow the source link for the full story. '
               'The picture is generated, not a photo from the story. Heat is our estimate of how widely a story is covered.</footer>\n</div>\n')
    out.append(f"<script>{SHARE_JS}</script>\n</body>\n</html>\n")
    return "".join(out)


def rss(data, current):
    now = dt.datetime.now(dt.timezone.utc)
    try:
        now = dt.datetime.fromisoformat(str(data.get("refreshedAt", "")).replace("Z", "+00:00"))
    except Exception:
        pass
    items = []
    for s in current:
        try:
            pd = dt.datetime.combine(dt.date.fromisoformat(s["published"]), dt.time(12), dt.timezone.utc)
        except Exception:
            pd = now
        link = f"{SITE}s/{s['id']}/"
        items.append(f"<item><title>{esc(s['title'])}</title><link>{link}</link><guid isPermaLink=\"true\">{link}</guid>"
                     f"<description>{esc(s['summary'])}</description><category>{esc(CATS.get(s['category'], 'Tech'))}</category>"
                     f"<pubDate>{format_datetime(pd)}</pubDate></item>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
            f"<title>Hypewire</title><link>{SITE}</link><description>What people are talking about in AI, entertainment, gaming and tech, refreshed daily.</description>"
            f'<language>en</language><lastBuildDate>{format_datetime(now)}</lastBuildDate><atom:link href="{SITE}feed.xml" rel="self" type="application/rss+xml"/>'
            + "".join(items) + "</channel></rss>\n")


def sitemap(archive, today):
    urls = [f"<url><loc>{SITE}</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq></url>"]
    for sid, rec in sorted(archive.items()):
        urls.append(f"<url><loc>{SITE}s/{sid}/</loc><lastmod>{rec['lastSeen']}</lastmod></url>")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(urls) + "</urlset>\n"


def main():
    data = json.load(open(os.path.join(ROOT, "stories.json"), encoding="utf-8"))
    current = [s for s in data.get("stories", []) if ID_RE.match(str(s.get("id", ""))) and s.get("title")]
    today = str(data.get("refreshedAt", ""))[:10] or dt.date.today().isoformat()
    os.makedirs(S_DIR, exist_ok=True)
    try:
        archive = json.load(open(ARCHIVE, encoding="utf-8"))
    except Exception:
        archive = {}
    live_ids = set()
    for s in current:
        live_ids.add(s["id"])
        archive[s["id"]] = {"lastSeen": today, "story": s}
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=KEEP_DAYS)).isoformat()
    for sid in [k for k, v in archive.items() if v.get("lastSeen", "") < cutoff]:
        del archive[sid]
        shutil.rmtree(os.path.join(S_DIR, sid), ignore_errors=True)
    # remove page folders that are neither live nor archived
    for name in os.listdir(S_DIR):
        p = os.path.join(S_DIR, name)
        if os.path.isdir(p) and name not in archive:
            shutil.rmtree(p, ignore_errors=True)

    by_entity = {}
    for s in current:
        for e in s.get("entities", []):
            by_entity.setdefault(e, []).append(s)
    for v in by_entity.values():
        v.sort(key=lambda x: -x["hype"])

    pil = load_pil()
    if not pil:
        print("warning: Pillow not installed; keeping existing images", file=sys.stderr)
    for sid, rec in archive.items():
        s, live = rec["story"], sid in live_ids
        d = os.path.join(S_DIR, sid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(story_page(s, live, by_entity, current))
        img = os.path.join(d, "card.jpg")
        if pil and (live or not os.path.exists(img)):
            story_card(s, img)

    byid = {s["id"]: s for s in current}
    if pil:
        home_card(data, byid, os.path.join(ROOT, "og.jpg"))
    with open(ARCHIVE, "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=1, sort_keys=True)
    with open(os.path.join(ROOT, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(rss(data, current))
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap(archive, today))
    print(f"built {len(archive)} story pages ({len(live_ids)} live), feed.xml, sitemap.xml" + (", images" if pil else ""))


if __name__ == "__main__":
    main()
