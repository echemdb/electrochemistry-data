
# Adding Literature Checklist (delete if not applicable)

For contributors and reviewers alike.

- [ ] Name PR `Add literature_identifier`

**Filename**

- [ ] Words and identifiers in the filenames must be lowercase.
- [ ] The filename must be of type `NAME_YEAR_FIRST-WORD_VOLUME_fxy_IDENTIFIER` (where x is the figure number and y the subfigure label, i.e., 2b).
- [ ] The figure number must match that of the figure in the article.

**Bib file**

- [ ] The identifier must be identical with that in the filename as well as the citation key in the YAML.
- [ ] Remove typos (or unwanted whitespace), specifically in the title such as `Pt (111)` to `Pt(111)`.

**SVG**

- [ ] The curve label should be short and unambiguous?
- [ ] Figure label should be of type `Figure: xy` (not `Figure: fxy`).
- [ ] The figure label must be identical to that in the article.
- [ ] Comments should be complete sentences ending with a period.
- [ ] A `tags` text label should be included in the SVG.
- [ ] The units on the axis should be identical to those n the figure.

**YAML**

- [ ] The identifier must be identical to that in the filename.
- [ ] Comments should be complete sentences ending with a period.
