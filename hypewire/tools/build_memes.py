#!/usr/bin/env python3
"""Build Hypewire's daily share pack from hypewire/stories.json.

Writes, inside hypewire/memes/:
  meme-1.jpg ... meme-4.jpg   1080x1350 caption cards (Instagram portrait, also fine on X, Threads and WhatsApp)
                               for the hottest stories that have a meme. Each card carries the joke, the plain facts
                               underneath, and the site address, so a shared image always leads back to the story.
  captions.txt                 a ready-to-paste post caption for each card
  index.html                   a phone-friendly page to download the cards and copy the captions (not indexed)

Run from anywhere:  python3 hypewire/tools/build_memes.py
Needs Pillow. Without it, the script prints a warning and leaves the existing pack alone.
"""
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "memes")
SITE = "https://rahuloo7.github.io/hypewire/"
COUNT = 4
W, H = 1080, 1350

sys.path.insert(0, HERE)
import build_pages as bp  # noqa: E402  (shared fonts, colours and text wrapping)

# Vivid category colours, matching the site's dark look: (deep, bright, accent)
CAT = {
    "ai": ("#1E1150", "#5B21B6", "#C4B5FD"),
    "entertainment": ("#4A0B24", "#BE123C", "#FF9BB3"),
    "gaming": ("#052A1A", "#15803D", "#86EFAC"),
    "tech": ("#071F3D", "#0369A1", "#7DD3FC"),
}
NAMES = {"ai": "AI", "entertainment": "ENTERTAINMENT", "gaming": "GAMING", "tech": "TECH"}
HEAT = (255, 46, 126)
INK = (9, 8, 15)


def background(cat):
    from PIL import Image, ImageDraw, ImageFilter
    deep, bright, acc = (bp.hexrgb(c) for c in CAT.get(cat, CAT["tech"]))
    small = Image.new("RGB", (54, 68))
    px = small.load()
    for y in range(68):
        for x in range(54):
            t = min(1, (x / 54) * .35 + (1 - y / 68) * .75)
            px[x, y] = tuple(int(deep[i] + (bright[i] - deep[i]) * t) for i in range(3))
    img = small.resize((W, H), Image.BILINEAR).convert("RGBA")
    for box, col, alpha in (((-300, -380, 700, 520), acc, 90), ((520, 420, 1400, 1200), HEAT, 55)):
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).ellipse(box, fill=alpha)
        img = Image.composite(Image.new("RGBA", (W, H), col + (255,)), img, mask.filter(ImageFilter.GaussianBlur(120)))
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    for y in range(14, H, 30):
        for x in range(14 + (y // 30 % 2) * 15, W, 30):
            dd.ellipse((x - 1.6, y - 1.6, x + 1.6, y + 1.6), fill=(255, 255, 255, 16))
    return Image.alpha_composite(img, dots), acc


def fit(d, text, name, sizes, width, lines):
    for size in sizes:
        f = bp.font(name, size)
        out = bp.wrap(d, text, f, width, lines)
        if not out[-1].endswith("…") or size == sizes[-1]:
            return f, size, out


def outlined(d, xy, text, f, fill, stroke=6):
    d.text(xy, text, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK)


def card(s, path):
    from PIL import Image, ImageDraw
    img, acc = background(s["category"])
    d = ImageDraw.Draw(img)
    # Header: wordmark and category
    fw = bp.font("InterDisplay-Bold", 46)
    d.text((72, 64), "Hype", font=fw, fill="#FFFFFF")
    d.text((72 + d.textlength("Hype", font=fw), 64), "wire", font=fw, fill=HEAT)
    fc = bp.font("Inter-SemiBold", 26)
    cat = NAMES.get(s["category"], "TECH")
    cw = d.textlength(cat, font=fc)
    d.rounded_rectangle((W - 72 - cw - 36, 66, W - 72, 116), radius=12, fill=acc)
    d.text((W - 72 - cw - 18, 76), cat, font=fc, fill=INK)

    # The joke: setup in white, punchline in pink, centred
    cx = W // 2
    ft, st, top = fit(d, s["meme"]["top"].upper(), "InterDisplay-Bold", (92, 84, 76, 68), W - 144, 3)
    fb, sb, bot = fit(d, s["meme"]["bottom"].upper(), "InterDisplay-Bold", (92, 84, 76, 68), W - 144, 3)
    y = 210
    for ln in top:
        outlined(d, (cx - d.textlength(ln, font=ft) / 2, y), ln, ft, "#FFFFFF")
        y += int(st * 1.08)
    y += 34
    for ln in bot:
        outlined(d, (cx - d.textlength(ln, font=fb) / 2, y), ln, fb, HEAT)
        y += int(sb * 1.08)

    # The facts, on a dark panel at the bottom, so the image never travels without them
    panel_top = max(y + 70, 820)
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(panel).rounded_rectangle((48, panel_top, W - 48, H - 130), radius=36, fill=INK + (225,))
    img = Image.alpha_composite(img, panel)
    d = ImageDraw.Draw(img)
    fl = bp.font("Inter-SemiBold", 24)
    d.text((92, panel_top + 40), "WHAT ACTUALLY HAPPENED", font=fl, fill=acc)
    room = (H - 130 - 40) - (panel_top + 90)
    fh, sh, tl = fit(d, s["title"], "InterDisplay-Bold", (46, 42, 38), W - 184, 3)
    yy = panel_top + 86
    for ln in tl:
        d.text((92, yy), ln, font=fh, fill="#FFFFFF")
        yy += int(sh * 1.18)
    left = (panel_top + 90 + room) - yy - 10
    if left > 60:
        fs = bp.font("Inter-Medium", 30)
        for ln in bp.wrap(d, s["summary"], fs, W - 184, max(1, min(3, int(left // 40)))):
            d.text((92, yy + 10), ln, font=fs, fill=(205, 200, 230))
            yy += 40
    # Footer: where to find more, and the heat score
    ff = bp.font("Inter-SemiBold", 30)
    url = "rahuloo7.github.io/hypewire"
    d.text((72, H - 92), url, font=ff, fill="#FFFFFF")
    hs = "HEAT %d" % s["hype"]
    hw = d.textlength(hs, font=ff)
    d.rounded_rectangle((W - 72 - hw - 40, H - 102, W - 72, H - 46), radius=14, fill=HEAT)
    d.text((W - 72 - hw - 20, H - 92), hs, font=ff, fill="#FFFFFF")
    img.convert("RGB").save(path, "JPEG", quality=88, optimize=True, progressive=True)


def caption(s):
    tag = {"ai": "#AI", "entertainment": "#Movies #TV", "gaming": "#Gaming", "tech": "#Tech"}.get(s["category"], "")
    return (f"{s['meme']['take']}\n\nWhat actually happened: {s['summary']}\n\n"
            f"Full story: {SITE}s/{s['id']}/\n{tag} #Hypewire")


def page(picks, edition):
    esc = html.escape
    items = []
    for i, s in enumerate(picks, 1):
        cap = caption(s)
        items.append(f"""<article><img src="meme-{i}.jpg?v={esc(edition)}" alt="{esc(s['meme']['top'] + ' / ' + s['meme']['bottom'])}" width="1080" height="1350" loading="lazy">
<div class="row"><a class="btn" href="meme-{i}.jpg" download="hypewire-{esc(s['id'])}.jpg">Download image</a><button class="btn alt" type="button" data-cap="{esc(cap)}">Copy caption</button></div>
<pre>{esc(cap)}</pre></article>""")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>Hypewire share pack</title>
<style>
:root{{color-scheme:dark}}body{{margin:0;background:#09080F;color:#F6F4FF;font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:560px;margin:0 auto;padding:20px 16px 60px;display:flex;flex-direction:column;gap:28px}}
h1{{margin:0;font-size:1.6rem;letter-spacing:-.03em}}h1 span{{color:#FF2E7E}}p{{margin:0;color:#A9A4C4}}
article{{background:#14121E;border:1px solid #24212F;border-radius:20px;overflow:hidden}}img{{display:block;width:100%;height:auto}}
.row{{display:flex;gap:10px;padding:14px}}.btn{{flex:1;text-align:center;border:0;border-radius:999px;padding:12px;font:600 .95rem system-ui;background:#fff;color:#09080F;text-decoration:none;cursor:pointer}}
.btn.alt{{background:#FF2E7E;color:#fff}}pre{{margin:0;padding:0 16px 16px;white-space:pre-wrap;font:14px/1.45 system-ui;color:#CFCBE6}}a.back{{color:#FF2E7E}}
</style></head><body><main>
<h1>Hype<span>wire</span> share pack</h1>
<p>Today's four hottest memes, ready to post. Download a card, copy its caption, post. Edition {esc(edition)}. <a class="back" href="../">Back to the site</a></p>
{''.join(items)}
</main><script>
document.querySelectorAll('[data-cap]').forEach(function(b){{b.onclick=function(){{var t=b.getAttribute('data-cap'),done=function(){{b.textContent='Copied';setTimeout(function(){{b.textContent='Copy caption'}},1600)}};
if(navigator.clipboard)navigator.clipboard.writeText(t).then(done,function(){{prompt('Copy this caption',t)}});else prompt('Copy this caption',t);}}}});
</script></body></html>
"""


def main():
    if not bp.load_pil():
        print("warning: Pillow is not installed, so the share pack was not rebuilt (pip install pillow)")
        return
    data = json.load(open(os.path.join(ROOT, "stories.json"), encoding="utf-8"))
    stories = [s for s in data.get("stories", []) if isinstance(s.get("meme"), dict) and s["meme"].get("top") and s["meme"].get("bottom")]
    stories.sort(key=lambda s: -int(s.get("hype", 0)))
    # One per category first, so the pack is varied, then the next hottest
    picks, seen = [], set()
    for s in stories:
        if s["category"] not in seen:
            picks.append(s); seen.add(s["category"])
        if len(picks) == COUNT:
            break
    for s in stories:
        if len(picks) >= COUNT:
            break
        if s not in picks:
            picks.append(s)
    picks.sort(key=lambda s: -int(s.get("hype", 0)))
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.startswith("meme-") and f.endswith(".jpg"):
            os.remove(os.path.join(OUT, f))
    for i, s in enumerate(picks, 1):
        card(s, os.path.join(OUT, f"meme-{i}.jpg"))
    edition = str(data.get("refreshedAt", ""))[:10]
    with open(os.path.join(OUT, "captions.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n\n-----\n\n".join(f"meme-{i}.jpg\n{caption(s)}" for i, s in enumerate(picks, 1)) + "\n")
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page(picks, edition))
    print(f"built share pack: {len(picks)} meme cards, captions.txt, index.html")


if __name__ == "__main__":
    main()
