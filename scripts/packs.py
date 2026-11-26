#!/usr/bin/env python3
"""Dot Buddy character packs (packs/<id>/): check them, and build the list the app reads.

  python3 scripts/packs.py check [--app <DotBuddy binary>]    check every pack (CI runs this on pull requests)
  python3 scripts/packs.py check-pr --base <sha> --author <login> [--app <DotBuddy binary> --previews <dir>]
                                                            rules for one pull request: one pack, the author's own, no generated files;
                                                            with --previews, also draw the changed packs' previews there for review
  python3 scripts/packs.py build --app <DotBuddy binary>     check, draw packs/<id>/preview.gif with the app,
                                                            write packs/index.json and the gallery in README.md

Contributors only add packs/<id>/ (chara.json + PNGs). preview.gif, index.json and the gallery are made by CI after
the merge, so a pull request never needs to touch them. Standard library only.

The motion names come from the app's source: DOTBUDDY_SRC=<a dot-buddy checkout>, or else Sources/Charas.swift is read
from github.com/doldoldol21/dot-buddy. PACKS_ROOT=<dir> checks another checkout with this copy of the script
(CI runs the base branch's script on a pull request, so a pull request can't loosen its own checks).
"""
import hashlib, json, os, re, struct, subprocess, sys, urllib.request, zlib

HERE = os.path.realpath(os.environ.get("PACKS_ROOT") or os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
COMMUNITY = os.path.join(HERE, "packs")
INDEX = os.path.join(COMMUNITY, "index.json")
README = os.path.join(HERE, "README.md")
APP_SRC = "https://raw.githubusercontent.com/doldoldol21/dot-buddy/main/Sources/Charas.swift"

ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,31}$")
RESERVED = {"acorn", "mandu", "sprout", "cloud", "candle", "pebble", "index", "readme"}   # the built-in characters keep their names
LICENSES = {"CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "MIT"}
KEYS = {"name", "names", "frame", "height", "fps", "eyes", "author", "license", "description", "based_on"}
REQUIRED = ["idle", "walk", "work", "sleep", "ask"]                      # the motions people see most (fall/jump: one of the two)
MAINTAINERS = {"doldoldol21"}                                              # check-pr's ownership rules don't apply to them
SAME_SHAPE = 0.95                                                          # idle outlines this alike are treated as the same character
MAX_FILE, MAX_PACK, MAX_FRAMES = 64 << 10, 512 << 10, 16
MAX_W, MAX_H = 30, 32
GENERATED = {"preview.gif"}
START, END = "<!-- gallery:start -->", "<!-- gallery:end -->"


def motions():
    """Motion names, read from the app's source so the two never drift apart"""
    local = os.environ.get("DOTBUDDY_SRC")
    if local:
        src = open(os.path.join(local, "Sources", "Charas.swift"), encoding="utf-8").read()
    else:
        with urllib.request.urlopen(urllib.request.Request(APP_SRC, headers={"User-Agent": "dot-buddy-packs"}), timeout=30) as r:
            src = r.read().decode()
    block = src[src.index("let MOTIONS"):src.index("let MOTION_FALLBACK")]
    return re.findall(r'\("([a-z]+)", T\(', block)


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(33)
    if len(head) < 33 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def png_alpha(path):
    """Opaque mask of a PNG's pixels as rows of bools (8-bit gray, RGB, palette, gray+alpha or RGBA; not interlaced), or None"""
    try:
        b = open(path, "rb").read()
        if b[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        i, idat, trns, w = 8, b"", b"", 0
        while i < len(b):
            n, t = struct.unpack(">I4s", b[i:i + 8]); d = b[i + 8:i + 8 + n]; i += 12 + n
            if t == b"IHDR":
                w, h, depth, ctype, _, _, lace = struct.unpack(">IIBBBBB", d)
            elif t == b"IDAT":
                idat += d
            elif t == b"tRNS":
                trns = d
        if depth != 8 or lace or ctype not in (0, 2, 3, 4, 6):
            return None
        bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
        raw, stride, prev, rows, pos = zlib.decompress(idat), w * bpp, bytearray(w * bpp), [], 0
        for _ in range(h):
            f, line = raw[pos], bytearray(raw[pos + 1:pos + 1 + stride]); pos += 1 + stride
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                c = prev[x - bpp] if x >= bpp else 0
                up = prev[x]
                if f == 1: line[x] = (line[x] + a) & 255
                elif f == 2: line[x] = (line[x] + up) & 255
                elif f == 3: line[x] = (line[x] + (a + up) // 2) & 255
                elif f == 4:
                    pa, pb, pc = abs(up - c), abs(a - c), abs(a + up - 2 * c)
                    line[x] = (line[x] + (a if pa <= pb and pa <= pc else up if pb <= pc else c)) & 255
            prev = line
            if ctype == 6: rows.append([line[x * 4 + 3] > 0 for x in range(w)])
            elif ctype == 4: rows.append([line[x * 2 + 1] > 0 for x in range(w)])
            elif ctype == 3: rows.append([line[x] >= len(trns) or trns[line[x]] > 0 for x in range(w)])
            else: rows.append([True] * w)
        return rows
    except Exception:
        return None


def idle_shape(d):
    """The first idle frame's opaque dots, bottom-centered (so frames of different sizes line up), or None"""
    rows = png_alpha(os.path.join(d, "idle.png"))
    if not rows:
        return None
    fw = len(rows[0])
    try:
        fr = json.load(open(os.path.join(d, "chara.json"), encoding="utf-8")).get("frame")
        if isinstance(fr, list) and len(fr) == 2 and isinstance(fr[0], int) and 0 < fr[0] <= fw:
            fw = fr[0]
    except Exception:
        pass
    h = len(rows)
    return {(x - fw // 2, h - y) for y, r in enumerate(rows) for x, v in enumerate(r[:fw]) if v} or None


def same_shape(a, b):
    return a and b and len(a & b) / len(a | b) >= SAME_SHAPE


def check_pack(d, names):
    """Problems with one pack folder (empty list = fine)"""
    pid, errs = os.path.basename(d), []
    if not ID.match(pid):
        errs.append("folder name must be 2-32 characters of a-z, 0-9 and '-', starting with a letter or digit")
    if pid in RESERVED:
        errs.append(f"'{pid}' is taken by a built-in character; pick another name")
    files = sorted(os.listdir(d))
    hidden = [f for f in files if f.startswith(".")]
    files = [f for f in files if not f.startswith(".")]
    if hidden:
        errs.append("remove hidden files: " + ", ".join(hidden))
    for f in files:
        p = os.path.join(d, f)
        if os.path.islink(p) or not os.path.isfile(p):
            errs.append(f"{f}: only plain files (no folders or links)")
        elif f in GENERATED:
            pass
        elif f != "chara.json" and not (f.endswith(".png") and f[:-4] in names):
            errs.append(f"{f}: not a motion name (see CHARACTERS.md) — allowed: chara.json and <motion>.png")
        elif os.path.getsize(p) > MAX_FILE:
            errs.append(f"{f}: {os.path.getsize(p)} bytes, the limit is {MAX_FILE}")
    total = sum(os.path.getsize(os.path.join(d, f)) for f in files if f not in GENERATED and os.path.isfile(os.path.join(d, f)))
    if total > MAX_PACK:
        errs.append(f"the pack is {total} bytes, the limit is {MAX_PACK}")
    missing = [m for m in REQUIRED if m + ".png" not in files] + ([] if "fall.png" in files or "jump.png" in files else ["fall (or jump)"])
    if missing:
        errs.append("draw these motions too (the ones people see most): " + ", ".join(m if m.endswith(")") else m + ".png" for m in missing))
    meta = {}
    if "chara.json" not in files:
        errs.append("chara.json is required (name, author, license)")
    else:
        try:
            meta = json.load(open(os.path.join(d, "chara.json"), encoding="utf-8"))
            if not isinstance(meta, dict):
                raise ValueError("not an object")
        except Exception as e:
            errs.append(f"chara.json: {e}")
            meta = {}
    if meta:
        extra = set(meta) - KEYS
        if extra:
            errs.append("chara.json: unknown keys " + ", ".join(sorted(extra)))
        for k, lim in (("name", 40), ("author", 39), ("description", 140), ("based_on", 60)):
            v = meta.get(k, "")
            if k not in ("description", "based_on") and not (isinstance(v, str) and v.strip()):
                errs.append(f"chara.json: '{k}' is required")
            elif not isinstance(v, str) or len(v) > lim:
                errs.append(f"chara.json: '{k}' must be text of at most {lim} characters")
        if meta.get("license") not in LICENSES:
            errs.append("chara.json: 'license' must be one of " + ", ".join(sorted(LICENSES)))
        if "names" in meta and not (isinstance(meta["names"], dict) and all(isinstance(v, str) and len(v) <= 40 for v in meta["names"].values())):
            errs.append("chara.json: 'names' must map languages to names, e.g. {\"en\": \"Teacup\", \"ko\": \"찻잔\"}")
    # frame sizes: every motion PNG is a strip of frames the size of one idle frame
    idle = png_size(os.path.join(d, "idle.png")) if "idle.png" in files else None
    if "idle.png" in files and not idle:
        errs.append("idle.png is not a PNG")
    fw, fh = (meta.get("frame") or [None, None]) if isinstance(meta.get("frame"), list) and len(meta.get("frame")) == 2 else (None, None)
    if idle:
        fw, fh = fw or idle[0], fh or idle[1]
        if not (isinstance(fw, int) and isinstance(fh, int) and 0 < fw <= MAX_W and 0 < fh <= MAX_H):
            errs.append(f"frame size {fw}x{fh}: at most {MAX_W}x{MAX_H} dots")
        else:
            for f in files:
                if not f.endswith(".png") or f[:-4] not in names:
                    continue
                s = png_size(os.path.join(d, f))
                if not s:
                    errs.append(f"{f}: not a PNG")
                elif s[1] != fh or s[0] % fw or not 1 <= s[0] // fw <= MAX_FRAMES:
                    errs.append(f"{f}: {s[0]}x{s[1]}, but frames are {fw}x{fh} side by side (1-{MAX_FRAMES} frames)")
    return errs


def packs():
    if not os.path.isdir(COMMUNITY):
        return []
    return sorted(os.path.join(COMMUNITY, n) for n in os.listdir(COMMUNITY) if os.path.isdir(os.path.join(COMMUNITY, n)) and not n.startswith("."))


def entry(d):
    meta = json.load(open(os.path.join(d, "chara.json"), encoding="utf-8"))
    files = []
    for f in sorted(os.listdir(d)):
        if f.startswith(".") or f in GENERATED:
            continue
        b = open(os.path.join(d, f), "rb").read()
        files.append({"name": f, "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)})
    e = {"id": os.path.basename(d), "name": meta["name"].strip(), "author": meta["author"].strip(), "license": meta["license"],
         "description": meta.get("description", "").strip(), "files": files}
    if meta.get("names"):
        e["names"] = meta["names"]
    if meta.get("based_on", "").strip():
        e["based_on"] = meta["based_on"].strip()
    if os.path.exists(os.path.join(d, "preview.gif")):
        e["preview"] = "preview.gif"
    return e


def digest(e):
    return hashlib.sha256("\n".join(f"{f['name']}:{f['sha256']}" for f in e["files"]).encode()).hexdigest()


def app_load(app):
    """Ids the app itself loads from packs/ (the real loader, with its own limits)"""
    r = subprocess.run([app, "--charas"], capture_output=True, text=True, timeout=60, env=dict(os.environ, DOTBUDDY_CHARAS=COMMUNITY))
    return {c["id"]: c for c in json.loads(r.stdout or '{"charas": []}')["charas"]}


def check(app=None):
    names, bad = set(motions()), 0
    loaded = app_load(app) if app else {}
    shapes = {}                                                            # outlines of the packs already checked (alphabetical: the later one is flagged)
    for d in packs():
        shapes_next = (os.path.basename(d), idle_shape(d))
        errs = check_pack(d, names)
        pid = os.path.basename(d)
        if app and not errs:
            c = loaded.get("pack:" + pid)
            if not c:
                errs.append("the app could not load this pack")
            elif "idle" not in c["motions"] and not c["size"][0]:
                errs.append("the app loaded no picture")
        if not errs:
            others = [o for o in shapes if same_shape(shapes[o], shapes_next[1])]
            if others:
                errs.append(f"idle.png has almost the same outline as '{others[0]}'. A recolor of another pack isn't a new character; "
                            "if this really is a different drawing, say so in the pull request")
        print(("ok    " if not errs else "FAIL  ") + pid)
        for e in errs:
            print("      - " + e)
            if os.environ.get("GITHUB_ACTIONS"):
                print(f"::error file=packs/{pid}::{e}")
        bad += bool(errs)
        shapes[shapes_next[0]] = shapes_next[1]
    if bad:
        print(f"\n{bad} pack(s) need fixing. The rules are in README.md.")
    return bad == 0


def gallery(entries):
    if not entries:
        return "No characters yet. Be the first!"
    rows = ["| | Character | By | License |", "|---|---|---|---|"]
    for e in entries:
        img = f'<img src="packs/{e["id"]}/preview.gif" width="220" alt="{e["name"]}">' if e.get("preview") else ""
        desc = f'<br>{e["description"]}' if e["description"] else ""
        if e.get("based_on"):
            desc += f'<br><sub>Fan art of {e["based_on"]}</sub>'
        rows.append(f'| {img} | **{e["name"]}**{desc} | [@{e["author"]}](https://github.com/{e["author"]}) | {e["license"]} |')
    return "\n".join(rows)


def added(pid):
    try:
        days = git("log", "--diff-filter=A", "--format=%cs", "--", f"packs/{pid}/chara.json").split()
        if days:
            return days[-1]
    except Exception:
        pass
    from datetime import date
    return date.today().isoformat()


def build(app):
    if not check(app):
        return False
    old = {}
    if os.path.exists(INDEX):
        old = {e["id"]: e for e in json.load(open(INDEX, encoding="utf-8")).get("packs", [])}
    out = []
    for d in packs():
        pid, e = os.path.basename(d), entry(d)
        gif = os.path.join(d, "preview.gif")
        if not os.path.exists(gif) or pid not in old or digest(old[pid]) != digest(e):    # draw the preview again only when the pack changed
            r = subprocess.run([app, "--demo-gif", gif, "chara:pack:" + pid], capture_output=True, timeout=120, env=dict(os.environ, DOTBUDDY_CHARAS=COMMUNITY))
            if r.returncode:                                                              # (with DOTBUDDY_CHARAS set the built-in packs aren't loaded, so ids can't clash)
                print(f"preview for {pid} failed: {r.stderr.decode()[:200]}")
                return False
            e = entry(d)
        e["added"] = old.get(pid, {}).get("added") or added(pid)                       # when the pack first appeared (the site lists newest first)
        out.append(e)
    json.dump({"version": 1, "packs": out}, open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(INDEX, "a").write("\n")
    if os.path.exists(README):
        s = open(README, encoding="utf-8").read()
        if START in s and END in s:
            s = s[:s.index(START) + len(START)] + "\n" + gallery(out) + "\n" + s[s.index(END):]
            open(README, "w", encoding="utf-8").write(s)
    print(f"index: {len(out)} pack(s)")
    return True


def git(*a):
    return subprocess.run(["git", "-C", HERE, *a], capture_output=True, text=True, check=True).stdout


def check_pr(base, author, app=None, previews=None):
    """Rules for one pull request that touches packs/: everything inside one pack folder, no generated files,
    and the pack is the pull request author's (a new pack names them as author; an existing one was already theirs)"""
    changed = [f for f in git("diff", "--name-only", f"{base}...HEAD").splitlines() if f]
    mine = [f for f in changed if f.startswith("packs/")]
    if not mine:
        print("no packs changed"); return True
    errs, ids = [], sorted({f.split("/")[1] for f in mine if f.count("/") >= 2})
    gen = [f for f in mine if f.count("/") < 2 or os.path.basename(f) in GENERATED]
    if gen:
        errs.append("leave these to CI (it makes them after the merge): " + ", ".join(gen))
    if author.lower() not in MAINTAINERS:
        if len(ids) > 1:
            errs.append("one character per pull request, please: this one changes " + ", ".join(ids))
        rest = [f for f in changed if not f.startswith("packs/")]
        if rest:
            errs.append("a character pull request only adds its packs/<name>/ folder; send other changes separately: " + ", ".join(rest))
        for pid in ids:
            try:
                was = json.loads(git("show", f"{base}:packs/{pid}/chara.json")).get("author", "")
            except Exception:
                was = None
            try:
                now = json.load(open(os.path.join(COMMUNITY, pid, "chara.json"), encoding="utf-8")).get("author", "")
            except Exception:
                now = ""
            if was is not None and was.strip().lower() != author.lower():
                errs.append(f"'{pid}' is @{was}'s character; only they (or a maintainer) can change it")
            elif was is None and now.strip().lower() != author.lower():
                errs.append(f"packs/{pid}/chara.json: 'author' must be your GitHub username ({author})")
    for e in errs:
        print("FAIL  " + e)
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error::{e}")
    if previews and app:
        os.makedirs(previews, exist_ok=True)
        for pid in ids:
            if os.path.isfile(os.path.join(COMMUNITY, pid, "idle.png")):
                r = subprocess.run([app, "--demo-gif", os.path.join(previews, pid + ".gif"), "chara:pack:" + pid], capture_output=True, timeout=120,
                                   env=dict(os.environ, DOTBUDDY_CHARAS=COMMUNITY))
                print(("preview " if not r.returncode else "preview failed ") + pid)
    if not errs:
        print("ok    pull request: " + ", ".join(ids))
    return not errs


if __name__ == "__main__":
    a = sys.argv[1:]
    app = a[a.index("--app") + 1] if "--app" in a and a.index("--app") + 1 < len(a) else None
    if a[:1] == ["check"]:
        sys.exit(0 if check(app) else 1)
    opt = lambda k: a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else None
    if a[:1] == ["check-pr"] and opt("--base") and opt("--author"):
        sys.exit(0 if check_pr(opt("--base"), opt("--author"), app, opt("--previews")) else 1)
    if a[:1] == ["build"] and app:
        sys.exit(0 if build(app) else 1)
    print(__doc__)
    sys.exit(2)
