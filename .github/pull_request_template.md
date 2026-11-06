## What and why

<!-- What does this PR add or change, and why? For new data: which publication and which figures.
Link the related issue, e.g. "Closes #123". If it builds on an unmerged PR, add "Depends on #123".
See CONTRIBUTING.md for the full guide. -->

## Checklist

- [ ] The branch starts from a recent `origin/main` and contains only this change (one publication per PR).
- [ ] Added `doc/news/<branch-name>.rst` ([News entry](https://github.com/echemdb/electrochemistry-data/blob/main/CONTRIBUTING.md#news-entry)).
- [ ] `pixi run -e dev validate-new-input` and `pixi run check-news` pass locally.

**New or changed data only** (delete otherwise), see [CONTRIBUTING.md](https://github.com/echemdb/electrochemistry-data/blob/main/CONTRIBUTING.md):

- [ ] PR is named `Add <identifier>`.
- [ ] The identifier is identical in `bibliography.bib`, the directory name, the file names and `source.citationKey`; everything is lowercase.
- [ ] The figure labels (`f2b`, `sf2b`, `figure: 2b`) match the article.
- [ ] SVG: units as in the figure, scaling factors considered, `scan rate:` and `tags:` labels present.
- [ ] YAML: only information stated in the publication; comments are complete sentences ending with a period.
- [ ] The data converts (`convert-svg-one <identifier>` or `convert-raw`) and matches the figure.
- [ ] No PDF is committed.

**Code changes only** (delete otherwise):

- [ ] `pixi run -e dev test` and `pixi run -e dev lint` pass locally.
- [ ] Changes to the conversion or validation: `convert-force`, `verify-all`, `validate-input` and `validate-generated` pass.
