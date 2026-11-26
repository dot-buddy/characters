# Contributing

Thanks for helping! There are three ways to help here.

## Share a character

Follow [Share your character](README.md#share-your-character) in the README. In short: draw a pack, try it on your pet, add it as `packs/<name>/` in a fork, and open a pull request with only that folder. The [rules](README.md#rules) are short; CI checks most of them for you and attaches a preview of your character to the run.

After you open the pull request:

- CI runs **Check packs**. If it fails, the log says what to fix, line by line.
- A maintainer looks at the preview and usually replies within a few days.
- After the merge, CI draws the preview and the character shows up in the [gallery](https://dot-buddy.github.io/characters/) and in every Dot Buddy's **More Characters…** list. You don't need to touch `preview.gif`, `packs/index.json` or the README gallery.

To change your character later, open another pull request that edits its folder. Only the author in its `chara.json` can.

## Suggest a character

No drawing skills needed: open a [character idea](https://github.com/dot-buddy/characters/issues/new?template=character_idea.yml). Someone may pick it up. Ideas marked [good first issue](https://github.com/dot-buddy/characters/labels/good%20first%20issue) are a nice place to start drawing.

## Improve the gallery or the checks

The site is `scripts/site.py` and the checks are `scripts/packs.py`, both Python with no dependencies. Test a change with:

```bash
DOTBUDDY_SRC=<a dot-buddy checkout> python3 -I scripts/test_packs.py      # the pack rules
python3 -I scripts/site.py _site && open _site/index.html                 # the site
```

On a pull request, CI checks packs with the checker from `main`, so a change to `scripts/packs.py` takes effect after it's merged.

Problems with the app itself go to [the app repo's issues](https://github.com/doldoldol21/dot-buddy/issues).

Everyone here follows the [code of conduct](https://github.com/dot-buddy/.github/blob/main/CODE_OF_CONDUCT.md).
