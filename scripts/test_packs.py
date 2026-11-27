#!/usr/bin/env python3
"""Tests for the pack rules in packs.py (CI runs this on pull requests, before the checks).

  DOTBUDDY_SRC=<a dot-buddy checkout> python3 -I scripts/test_packs.py

A bad pack is refused for each reason, a recolored copy of a pack is caught as the same outline while the real packs
don't match each other, and a pack missing a core motion is flagged. Standard library only.
"""
import importlib.util, json, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import packs as cm

fails = []
def check(name, got, want):
    print(("ok   " if got == want else "FAIL ") + name)
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")

names = set(cm.motions())
ids = [os.path.basename(d) for d in cm.packs()]
check("there are packs to test with", len(ids) >= 2, True)

with tempfile.TemporaryDirectory() as td:
    bad = os.path.join(td, "Bad_Name"); os.makedirs(bad)
    open(os.path.join(bad, "idle.png"), "wb").write(b"not a png"); open(os.path.join(bad, "run.sh"), "w").write("echo hi")
    open(os.path.join(bad, "chara.json"), "w").write('{"name": "x", "license": "GPL"}')
    errs = " ".join(cm.check_pack(bad, names))
    check("a bad pack is refused for each reason", [k in errs for k in ("folder name", "run.sh", "'author' is required", "'license' must be", "idle.png is not a PNG")], [True] * 5)

    open(os.path.join(bad, "chara.json"), "w").write('{"name": "x", "author": "a", "license": "MIT", "descriptions": {"ko": "' + "가" * 141 + '"}}')
    check("a description in another language is limited like the main one", any("'descriptions'" in e for e in cm.check_pack(bad, names)), True)

    cp = os.path.join(td, ids[0] + "-copy"); shutil.copytree(os.path.join(cm.COMMUNITY, ids[0]), cp)
    shapes = {i: cm.idle_shape(os.path.join(cm.COMMUNITY, i)) for i in ids}
    check("every pack has an idle outline", all(shapes.values()), True)
    check("a copy of a pack has the same outline", cm.same_shape(shapes[ids[0]], cm.idle_shape(cp)), True)
    check("different packs don't match", any(cm.same_shape(shapes[x], shapes[y]) for x in ids for y in ids if x < y), False)
    # official characters: knockoffs (flipped, moved, resized, with something added) get flagged, different characters don't
    off = [i for i in ids if cm.official(json.load(open(os.path.join(cm.COMMUNITY, i, "chara.json"), encoding="utf-8")))]
    check("the maintainers' packs are official, the others aren't", (len(off) >= 1, all(i in off for i in ids if i in ("ghost", "teacup")), "onion" in off), (True, True, False))
    s0 = shapes[off[0]]
    variants = {"flip": {(-x, y) for x, y in s0}, "shift": {(x + 1, y + 1) for x, y in s0},
                "2x": {(2 * x + dx, 2 * y - dy) for x, y in s0 for dx in (0, 1) for dy in (0, 1)},
                "hat": s0 | {(x, max(y for _, y in s0) + k) for x in range(-3, 4) for k in range(1, 5)}}
    check("knockoffs of an official character look alike", {k: cm.likeness(s0, v) >= cm.LOOKALIKE for k, v in variants.items()}, {k: True for k in variants})
    check("different characters don't look alike", max(cm.likeness(shapes[x], shapes[y]) for x in ids for y in ids if x < y) < cm.LOOKALIKE, True)
    os.remove(os.path.join(cp, "walk.png"))
    check("a missing core motion is flagged", any("walk.png" in e for e in cm.check_pack(cp, names)), True)

# names: someone else's pack can't use an official character's name or call itself official
with tempfile.TemporaryDirectory() as td:
    real, cm.COMMUNITY = cm.COMMUNITY, td
    try:
        for pid, meta in (("ghost", {"name": "Ghost", "author": "doldoldol21", "license": "MIT"}), ("boo", {"name": "ghost", "author": "x", "license": "MIT"}),
                          ("cat", {"name": "Cat", "names": {"ko": "공식 고양이"}, "author": "x", "license": "MIT"}), ("dog", {"name": "Dog", "author": "x", "license": "MIT"})):
            os.makedirs(os.path.join(td, pid)); json.dump(meta, open(os.path.join(td, pid, "chara.json"), "w"))
        check("an official name or the word official is refused, other names aren't",
              [bool(cm.official_name_errors(p)) for p in ("boo", "cat", "dog", "ghost")], [True, True, False, False])
    finally:
        cm.COMMUNITY = real

# the pre-check comment on character pull requests (the model part runs only in CI)
spec = importlib.util.spec_from_file_location("precheck", os.path.join(os.path.dirname(os.path.abspath(__file__)), "precheck.py"))
pc = importlib.util.module_from_spec(spec); spec.loader.exec_module(pc)
check("links, mentions and e-mail in the words are flagged, plain words aren't",
      [bool(pc.rules("x", m)) for m in ({"name": "Cat", "description": "visit https://spam.example"}, {"name": "Cat", "descriptions": {"ko": "문의 me@spam.io"}},
                                        {"name": "@someone"}, {"name": "Teacup", "names": {"ko": "찻잔"}, "description": "A little teacup that steams while it waits."})],
      [True, True, True, False])
check("model words are cleaned before they reach the comment", pc.clean("Pikachu (Pokémon) https://x.example @all <b>"), "Pikachu (Pokémon) all b")
check("a clean pull request gets a thank-you", "look fine" in pc.comment([]), True)

# the artists list in the READMEs: everyone once, in the order their first pack was added
art = cm.artists([{"id": "b", "author": "Ann", "added": "2026-12-02"}, {"id": "a", "author": "bob", "added": "2026-12-01"},
                  {"id": "c", "author": "ann", "added": "2026-12-03"}] + [{"id": f"x{i}", "author": f"u{i}", "added": "2026-12-09"} for i in range(6)])
check("each artist once, first pack first, seven to a row", (art.index('alt="bob"') < art.index('alt="Ann"'), art.lower().count('alt="ann"'), art.count("<tr>")), (True, 1, 2))
check("no packs, no table", cm.artists([]), "")

if fails:
    print("FAIL\n  " + "\n  ".join(fails)); sys.exit(1)
print("ok — pack rules")
