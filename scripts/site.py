#!/usr/bin/env python3
"""Build the gallery site (GitHub Pages) from packs/index.json.

    python3 scripts/site.py [out_dir]      # default _site

One page in English (/) and one in Korean (/ko/). Each pack gets its preview and a zip of its files
(<id>.zip, one folder inside) that people can drop on their pet to install. CI runs this after the gallery
is updated on main (.github/workflows/packs.yml). Standard library only.
"""
import html, json, os, shutil, sys, zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "dot-buddy/characters"
APP = "https://github.com/doldoldol21/dot-buddy"
SITE = "https://dot-buddy.github.io/characters/"
ICON = "https://raw.githubusercontent.com/doldoldol21/dot-buddy/main/docs/media/icon.png"

TEXT = {
    "en": dict(title="Dot Buddy characters", lede="Characters people drew for Dot Buddy, the pixel desktop pet that tells you when your coding agent is done.",
               how="In the app: right-click the pet → Character → <b>More Characters…</b>, or download a zip here and drop it on your pet.",
               search="Search", by="by", fan="Fan art of {}", get="Download zip", add="Add your character", app="Get Dot Buddy",
               other="한국어", other_href="ko/", count="{} characters", empty="No match", report="Report a character",
               like="Like it on GitHub (❤️ or 👍)", official="Official: drawn by the Dot Buddy team", newest="Newest", popular="Most liked", sort="Sort",
               foot="Each character keeps the license its author chose. The original characters behind fan art belong to their owners."),
    "ko": dict(title="도트 친구 캐릭터", lede="코딩 에이전트가 끝나면 알려 주는 맥 바탕화면 도트 펫, 도트 친구에 쓸 수 있게 사람들이 그린 캐릭터예요.",
               how="앱에서 펫을 오른쪽 클릭 → 캐릭터 → <b>다른 캐릭터 받기…</b> 로 받거나, 여기서 zip 을 받아 펫에 끌어다 놓아도 돼요.",
               search="검색", by="그린 사람", fan="팬아트 · 원작 {}", get="zip 받기", add="내 캐릭터 올리기", app="도트 친구 받기",
               other="English", other_href="../", count="캐릭터 {}개", empty="맞는 캐릭터가 없어요", report="캐릭터 신고",
               like="GitHub에서 좋아요 누르기 (❤️ 또는 👍)", official="공식: 도트 친구 팀이 그린 캐릭터", newest="최신순", popular="인기순", sort="정렬",
               foot="캐릭터마다 그린 사람이 고른 라이선스를 따라요. 팬아트의 원작 캐릭터 권리는 원작자에게 있어요."),
}

CSS = """
:root { --bg: #fbfaf7; --fg: #1f2328; --muted: #59636e; --line: #d8dee4; --card: #ffffff; --chip: #f2f0eb; --link: #0b62d6; --accent: #e8743b; }
@media (prefers-color-scheme: dark) { :root { --bg: #111316; --fg: #e6e8eb; --muted: #9aa4ae; --line: #30363d; --card: #171a1e; --chip: #1f242a; --link: #6cb0ff; --accent: #f08a50; } }
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Segoe UI", "Noto Sans KR", sans-serif; }
a { color: var(--link); }
header { position: sticky; top: 0; z-index: 1; display: flex; align-items: center; gap: 16px; padding: 10px 16px; background: color-mix(in srgb, var(--bg) 88%, transparent); backdrop-filter: blur(8px); border-bottom: 1px solid var(--line); }
header .name { font-weight: 700; color: var(--fg); text-decoration: none; display: flex; align-items: center; gap: 8px; }
header .name img { width: 24px; height: 24px; image-rendering: pixelated; }
header nav { margin-left: auto; display: flex; gap: 16px; font-size: 14px; }
main { max-width: 1080px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 36px; line-height: 1.2; margin: 8px 0 8px; }
.lede { color: var(--muted); margin: 0 0 4px; max-width: 680px; }
.how { margin: 0 0 24px; max-width: 680px; }
.bar { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin: 0 0 20px; }
.bar input { flex: 1 1 240px; max-width: 360px; font: inherit; padding: 8px 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--card); color: var(--fg); }
.bar .count { color: var(--muted); font-size: 14px; }
.bar .add { margin-left: auto; font-size: 14px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.card { display: flex; flex-direction: column; background: var(--card); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.card .pic { background: var(--chip); }
.card .pic img { display: block; width: 100%; height: auto; image-rendering: pixelated; }
.card .body { padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 4px; flex: 1; }
.card h2 { font-size: 17px; margin: 0; }
.card h2 .official { display: inline-flex; vertical-align: -2px; margin-left: 4px; }
.card h2 .official svg { width: 16px; height: 16px; }
.card .meta { color: var(--muted); font-size: 13px; }
.card .fan { font-size: 12px; color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 1px 8px; align-self: flex-start; }
.card p { margin: 4px 0 8px; font-size: 14px; }
.card .acts { margin-top: auto; display: flex; align-items: center; gap: 12px; }
.card .like { font-size: 14px; color: var(--muted); text-decoration: none; padding: 6px 4px; }
.card .like:hover { color: var(--accent); }
.card .like:focus-visible, .bar select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.bar select { font: inherit; font-size: 14px; padding: 6px 8px; border: 1px solid var(--line); border-radius: 8px; background: var(--card); color: var(--fg); }
.card .get { align-self: flex-start; font-size: 14px; font-weight: 600; text-decoration: none; color: #fff; background: #1f2328; padding: 6px 12px; border-radius: 8px; }
@media (prefers-color-scheme: dark) { .card .get { background: #e6e8eb; color: #111316; } }
.card .get:focus-visible, .bar input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.empty { color: var(--muted); }
footer { max-width: 1080px; margin: 0 auto; padding: 24px 16px 48px; border-top: 1px solid var(--line); color: var(--muted); font-size: 14px; }
@media (max-width: 600px) { h1 { font-size: 28px; } header nav a.long { display: none; } }
"""

JS = """
const q = document.getElementById('q'), cards = [...document.querySelectorAll('.card')], count = document.getElementById('count'), empty = document.getElementById('empty');
const sort = document.getElementById('sort'), grid = document.querySelector('.grid');
sort.addEventListener('change', () => {
  const by = sort.value === 'popular' ? (a, b) => (b.dataset.likes - a.dataset.likes) || b.dataset.added.localeCompare(a.dataset.added) : (a, b) => b.dataset.added.localeCompare(a.dataset.added);
  for (const c of [...cards].sort(by)) grid.appendChild(c);
});
q.addEventListener('input', () => {
  const t = q.value.trim().toLowerCase(); let n = 0;
  for (const c of cards) { const on = !t || c.dataset.text.includes(t); c.hidden = !on; n += on; }
  count.textContent = count.dataset.fmt.replace('{}', n); empty.hidden = n > 0;
});
"""


def page(lang, packs, prefix):
    t, e = TEXT[lang], html.escape
    mark = (ROOT / "site" / "official.svg").read_text(encoding="utf-8").replace("<title>Official</title>", "")   # the pixel check (title comes from the span)
    cards = []
    for p in packs:
        name = p.get("names", {}).get(lang) or p.get("names", {}).get("en") or p["name"]
        about = p.get("descriptions", {}).get(lang) or p.get("description", "")
        text = " ".join([name, p["name"], p["author"], p.get("description", ""), p.get("based_on", "")] + list(p.get("names", {}).values()) + list(p.get("descriptions", {}).values())).lower()
        pic = f'<img src="{prefix}packs/{e(p["id"])}/preview.gif" alt="{e(name)}" loading="lazy">' if p.get("preview") else ""
        fan = f'<span class="fan">{e(t["fan"].format(p["based_on"]))}</span>' if p.get("based_on") else ""
        desc = f'<p>{e(about)}</p>' if about else ""
        badge = f'<span class="official" role="img" title="{e(t["official"])}" aria-label="{e(t["official"])}">{mark}</span>' if p.get("official") else ""
        disc = p.get("discussion", "")
        like = (f'<a class="like" href="{e(disc)}" title="{e(t["like"])}" aria-label="{e(t["like"])}: {int(p.get("likes", 0))}">♥ {int(p.get("likes", 0))}</a>'
                if disc.startswith(f"https://github.com/{REPO}/discussions/") else "")
        cards.append(f'<article class="card" data-text="{e(text)}" data-added="{e(p.get("added", ""))}" data-likes="{int(p.get("likes", 0))}"><div class="pic">{pic}</div><div class="body"><h2>{e(name)}{badge}</h2>'
                     f'<div class="meta">{t["by"]} <a href="https://github.com/{e(p["author"])}">@{e(p["author"])}</a> · {e(p["license"])}</div>{fan}{desc}'
                     f'<div class="acts"><a class="get" href="{prefix}{e(p["id"])}.zip" download>{t["get"]}</a>{like}</div></div></article>')
    url = SITE + ("ko/" if lang == "ko" else "")
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t["title"]}</title>
<meta name="description" content="{e(t["lede"])}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="en" href="{SITE}">
<link rel="alternate" hreflang="ko" href="{SITE}ko/">
<link rel="icon" href="{ICON}">
<meta property="og:title" content="{t["title"]}">
<meta property="og:description" content="{e(t["lede"])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}social-preview.png">
<meta name="twitter:card" content="summary_large_image">
<style>{CSS}</style>
</head>
<body>
<header>
  <a class="name" href="{url}"><img src="{ICON}" alt="">{t["title"]}</a>
  <nav><a href="{t["other_href"]}">{t["other"]}</a><a class="long" href="{APP}">{t["app"]}</a><a href="https://github.com/{REPO}">GitHub</a></nav>
</header>
<main>
<h1>{t["title"]}</h1>
<p class="lede">{e(t["lede"])}</p>
<p class="how">{t["how"]}</p>
<div class="bar">
  <input id="q" type="search" placeholder="{t["search"]}" aria-label="{t["search"]}">
  <span class="count" id="count" data-fmt="{t["count"]}">{t["count"].format(len(packs))}</span>
  <select id="sort" aria-label="{t["sort"]}"><option value="newest">{t["newest"]}</option><option value="popular">{t["popular"]}</option></select>
  <a class="add" href="https://github.com/{REPO}/blob/main/{"README.ko.md" if lang == "ko" else "README.md"}#{"내-캐릭터-올리기" if lang == "ko" else "share-your-character"}">{t["add"]}</a>
</div>
<div class="grid">
{chr(10).join(cards)}
</div>
<p class="empty" id="empty" hidden>{t["empty"]}</p>
</main>
<footer>{t["foot"]} <a href="https://github.com/{REPO}/issues/new?template=report_character.yml">{t["report"]}</a></footer>
<script>{JS}</script>
</body>
</html>
"""


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "_site").resolve()
    if out.exists():
        shutil.rmtree(out)
    (out / "ko").mkdir(parents=True)
    packs = json.load(open(ROOT / "packs" / "index.json", encoding="utf-8"))["packs"]
    packs = sorted(packs, key=lambda p: p.get("added", ""), reverse=True)            # newest first (ties keep the index's order)
    for p in packs:
        src = ROOT / "packs" / p["id"]
        if p.get("preview"):
            (out / "packs" / p["id"]).mkdir(parents=True, exist_ok=True)
            shutil.copy(src / "preview.gif", out / "packs" / p["id"] / "preview.gif")
        with zipfile.ZipFile(out / f'{p["id"]}.zip', "w", zipfile.ZIP_DEFLATED) as z:   # only the files the index lists (what the app would install)
            for f in p["files"]:
                z.write(src / f["name"], f'{p["id"]}/{f["name"]}')
    (out / "index.html").write_text(page("en", packs, ""))
    (out / "ko" / "index.html").write_text(page("ko", packs, "../"))
    for f in sorted((ROOT / "site").glob("*")):                                       # files served as they are (the Search Console check, the social preview image)
        if f.is_file():
            shutil.copy(f, out / f.name)
    today = date.today().isoformat()
    (out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                     f"  <url><loc>{SITE}</loc><lastmod>{today}</lastmod></url>\n  <url><loc>{SITE}ko/</loc><lastmod>{today}</lastmod></url>\n</urlset>\n")
    print(f"site: {out} ({len(packs)} packs)")


if __name__ == "__main__":
    main()
