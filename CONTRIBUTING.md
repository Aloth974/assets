# Contributing

You need an AI tool that can generate images. Read [docs/style.md](docs/style.md) and
[docs/specs.md](docs/specs.md) first.

## The loop

1. **Pick a brief** in `briefs/<family>/` with `status: open`. Set it to `taken` and add
   your GitHub handle as `owner` in the same PR as your first submission, or in a small PR
   right away to claim it.
2. **Generate** from the brief, starting from the prompt starter in `docs/specs.md`. Make a
   few candidates and keep only the ones you would ship.
3. **Submit** each candidate as `submissions/<stem>/<handle>-<n>.png` with a record
   `submissions/<stem>/<handle>-<n>.json`:

   ```json
   {
     "brief": "<stem>",
     "author": "<github handle>",
     "tool": "ChatGPT",
     "model": "gpt-image-1",
     "date": "2026-10-05",
     "prompt": "The exact full prompt you used.",
     "references": [],
     "sha256": "<sha256 of the PNG>"
   }
   ```

   `references` lists repo-relative paths of images you fed the tool. Get the hash with
   `sha256sum file.png`, or let `python tools/check.py --fix-hashes` fill it.
4. **Check** locally: `pip install -r tools/requirements.txt && python tools/check.py`.
5. **Open a PR.** CI runs the same check. The maintainer reviews against the brief.

## After review

An accepted candidate moves to `archive/<family>/<stem>.png` with its record, and the
brief becomes `done`. Rejected candidates are deleted; the review comment says why.

## Rules

- Never invent lore, names, factions or places. A brief says everything you need.
- Never submit anything you didn't generate for this repo, or anything with a watermark.
- No local paths, usernames or personal data in records or prompts.

## Licence

By contributing, you release your contribution under [CC0 1.0](LICENSE).
