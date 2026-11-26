#!/usr/bin/env python3
"""Tests for the pack rules in packs.py (CI runs this on pull requests, before the checks).

  DOTBUDDY_SRC=<a dot-buddy checkout> python3 -I scripts/test_packs.py

A bad pack is refused for each reason, a recolored copy of a pack is caught as the same outline while the real packs
don't match each other, and a pack missing a core motion is flagged. Standard library only.
"""
import importlib.util, os, shutil, sys, tempfile

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
    os.remove(os.path.join(cp, "walk.png"))
    check("a missing core motion is flagged", any("walk.png" in e for e in cm.check_pack(cp, names)), True)

# the pre-check comment on character pull requests (the model part runs only in CI)
spec = importlib.util.spec_from_file_location("precheck", os.path.join(os.path.dirname(os.path.abspath(__file__)), "precheck.py"))
pc = importlib.util.module_from_spec(spec); spec.loader.exec_module(pc)
check("links, mentions and e-mail in the words are flagged, plain words aren't",
      [bool(pc.rules("x", m)) for m in ({"name": "Cat", "description": "visit https://spam.example"}, {"name": "Cat", "descriptions": {"ko": "문의 me@spam.io"}},
                                        {"name": "@someone"}, {"name": "Teacup", "names": {"ko": "찻잔"}, "description": "A little teacup that steams while it waits."})],
      [True, True, True, False])
check("model words are cleaned before they reach the comment", pc.clean("Pikachu (Pokémon) https://x.example @all <b>"), "Pikachu (Pokémon) all b")
check("a clean pull request gets a thank-you", "look fine" in pc.comment([]), True)

if fails:
    print("FAIL\n  " + "\n  ".join(fails)); sys.exit(1)
print("ok — pack rules")
