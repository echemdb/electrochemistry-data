# Contributing to electrochemistry-data

Thank you for helping us build an open collection of interfacial electrochemistry data!

If you are unsure about anything, open an
[issue](https://github.com/echemdb/electrochemistry-data/issues) or a draft pull request
and ask. We are happy to help.

## Two kinds of contributions

**Data contributions** add new data, or check and correct existing entries. They need
knowledge of electrochemistry and careful reading of publications, but **no
programming**: you extract the experimental details from a publication into a YAML
file and verify that they are correct. Basic familiarity with Git and GitHub helps; if
you are new to it, ask in an issue and we will guide you. If you prefer to send your
data without Git, or want to discuss a contribution first, contact a maintainer via
the [contribute page on echemdb.org](https://www.echemdb.org/contribute/).
→ [Part I: Data contributions](#part-i-data-contributions)

**Technical contributions** improve the conversion and validation tools, the CI, or the
review assistants. They need a development background (Python, Git, pixi).
→ [Part II: Technical contributions](#part-ii-technical-contributions)

Both kinds end with a pull request, see
[Submitting a pull request](#submitting-a-pull-request).

| You want to … | Kind | Go to |
| --- | --- | --- |
| add data traced from a figure in a publication | data | [Route A: digitized figure](#route-a-digitized-figure) |
| add the data behind a figure that you measured yourself (CSV) | data | [Route B: source data](#route-b-source-data) |
| check existing entries against their publications | data | [Checking existing entries](#checking-and-correcting-existing-entries) |
| report an error in an existing entry | data | [open an issue](https://github.com/echemdb/electrochemistry-data/issues/new/choose) |
| fix a bug or improve the conversion and validation tools | technical | [Part II](#part-ii-technical-contributions) |
| propose new metadata fields or a change of the metadata structure | schema | [metadata-schema](https://github.com/echemdb/metadata-schema/blob/main/CONTRIBUTING.md) |
| ask a question or propose a feature | any | [open an issue](https://github.com/echemdb/electrochemistry-data/issues/new/choose) |

## Getting started

Install [pixi](https://pixi.sh). It provides all tools in the right versions; the
`dev` environment is set up automatically the first time you run a task. Do not
`pip install` into the environment; all dependencies are declared in `pyproject.toml`.

All contributions go through a **fork** and a **pull request** to
`echemdb/electrochemistry-data`.

1. **Fork once** on GitHub and clone the repository. The remotes should be:
   - `origin` → `echemdb/electrochemistry-data` (upstream, you only fetch from it)
   - a remote for your fork, e.g. named after your GitHub user:

     ```sh
     git clone https://github.com/echemdb/electrochemistry-data.git
     cd electrochemistry-data
     git remote add <user> git@github.com:<user>/electrochemistry-data.git
     ```

2. **Start every change on a fresh branch from upstream.** For new data, name the
   branch after the entry identifier (see [Identifiers](#identifiers-and-file-names)):

   ```sh
   git fetch origin
   git checkout -b <branch-name> --no-track origin/main
   ```

   Do not work on `main`, and do not reuse an old branch for a new change.

3. **Keep each branch minimal.** One concern per branch and pull request: one
   publication, one fix, or one feature. Fixes of unrelated entries, bibliography
   clean-ups and tooling changes go into separate pull requests. Small pull requests
   are reviewed and merged much faster.

---

## Part I: Data contributions

Adding a publication takes these steps:

1. [Determine the identifier](#identifiers-and-file-names) of the publication.
2. [Add the publication to the bibliography](#adding-the-publication-to-the-bibliography).
3. Add the data, either as a [digitized figure](#route-a-digitized-figure) (SVG + YAML)
   or as [source data](#route-b-source-data) (CSV + YAML).
4. Fill in [the metadata](#what-to-put-in-the-metadata) from the publication.
5. [Check](#checking-your-data) the files locally.
6. [Submit a pull request](#submitting-a-pull-request).

### Identifiers and file names

Every publication gets an identifier that is used as the BibTeX key, the directory
name, the `source.citationKey` in the YAML files, and the prefix of all file names:

```text
<firstauthor>_<year>_<firsttitleword>_<firstpage>
```

for example `markovic_1996_oxygen_6715`. Common words such as "a", "on" or "the" are
skipped when choosing the title word. The identifier is computed from the BibTeX entry
by `svgdigitizer.pdf.Pdf.build_identifier`. Run `pixi run -e dev validate-bib-keys`
after adding the BibTeX entry: a `KEY MISMATCH` message shows the expected key.

Files of a single curve are named

```text
<identifier>_f<figure>_<curve>.<ext>
```

for example `markovic_1996_oxygen_6715_f1_111.svg`. Use `sf` instead of `f` for figures
in the supporting information (e.g. `_sf2b_`). The figure label must match the article
(`f2b` for Figure 2b). The curve label is short and unambiguous, e.g. a color
(`blue`), a label from the legend (`111`), or a number (`1`).

**Everything is lowercase**: identifiers, file names and SVG labels
(`pixi run -e dev fix-lowercase` fixes this for you).

### Adding the publication to the bibliography

All references live in a single file,
[`literature/bibliography/bibliography.bib`](literature/bibliography/bibliography.bib).

1. Add the BibTeX entry of the publication (e.g. from the publisher's website or
   Google Scholar) and set its key to the identifier.
2. Fix typos and unwanted whitespace, in particular in the title (`Pt (111)` →
   `Pt(111)`).
3. Normalize the file:

   ```sh
   pixi run -e dev fix-bib-format   # consistent formatting
   pixi run -e dev fix-bib-utf8     # LaTeX accents such as {\"u} → ü
   ```

### Route A: digitized figure

Data traced from a figure goes into
`literature/svgdigitizer/<identifier>/`. The preparation of the SVG files is
described step by step in the
[svgdigitizer workflow](https://echemdb.github.io/svgdigitizer/workflow.html).
Unlike in that workflow, the BibTeX entry goes into the shared
`bibliography.bib` (see above) and not into a `.bib` file in the folder.

1. **Put the PDF in the folder** as `<identifier>.pdf`. PDFs are ignored by git and
   are **never committed**; they are only needed locally to create the SVGs.
2. **Create one SVG per curve** (`<identifier>_f<figure>_<curve>.svg`) with
   `svgdigitizer paginate` and annotate it in Inkscape:
   - axis labels with the units **exactly as in the figure** (including a reference
     such as `V vs. RHE`),
   - a scaling factor label (e.g. `j_scaling_factor: 10`) if a curve in the figure is
     scaled, e.g. "×10",
   - `figure: 2b` (the label as printed in the article, without the `f`),
   - `curve: <curve>` matching the file name,
   - a `scan rate:` label (mandatory, possibly taken from the text or caption),
   - a `tags:` label with the type of measurement, e.g. `tags: BCV` or
     `tags: BCV, SHA`. Commonly used tags are `BCV` (blank CV), `SHA` (specific halide
     adsorption), `COOR`, `FAOR`, `MOR`, `HER`, `OER` and `ORR`,
   - a `linked:` label for other measurements shown in the same figure (e.g.
     `linked: DEMS`), if any,
   - a `comment:` label, if needed (see [Comments](#comments)).
3. **Create one YAML file per SVG** with the same name. Start from the
   [svgdigitizer example](https://github.com/echemdb/metadata-schema/blob/main/examples/file_schemas/svgdigitizer.yaml)
   of the metadata schema or from a similar existing entry in
   [`literature/svgdigitizer/`](literature/svgdigitizer). The fields and the allowed
   values are documented in the
   [schema reference](https://echemdb.github.io/metadata-schema/).
4. **Check that the data converts:**

   ```sh
   pixi run -e dev convert-svg-one <identifier>
   ```

   This creates the CSV and JSON for your folder and validates them. Plot the CSV
   and compare it with the figure in the PDF.

### Route B: source data

If you have the data behind a published figure, e.g. from your own measurements, you
can submit it directly as CSV without digitizing. The data goes into
`literature/source_data/<identifier>/`:

1. **Add one CSV file per curve** (`<identifier>_f<figure>_<curve>.csv`) as exported
   from your instrument or analysis software. Do not edit the data by hand.
2. **Add a YAML file with the same name.** Start from the
   [source data example](https://github.com/echemdb/metadata-schema/blob/main/examples/file_schemas/source_data.yaml)
   or from an existing entry in
   [`literature/source_data/`](literature/source_data). Besides the metadata of the
   experiment, the `dataDescription` section describes how to read the CSV:
   - `dialect`: delimiter, decimal separator, encoding, and the number of header
     lines,
   - `fieldMapping`: which column holds the potential, current, time, etc.,
   - `fieldUnits`: the unit (and reference electrode) of each column,
   - `scanRate` and `measurementType`.
3. **Check that the data converts:**

   ```sh
   pixi run -e dev convert-raw
   ```

### What to put in the metadata

- **Only information stated in the publication** (including its supporting
  information and the publications it cites for the procedure). Do not guess, and do
  not fill in typical values. Leave out fields for which the publication gives no
  information. When you derive a value (e.g. an electrode area from a stated
  diameter), say so in a comment of that quantity.
- **The schema decides what is required.** `pixi run -e dev validate-input` reports
  missing required fields; everything else is optional but welcome.
- **Comments** follow the rules in [Comments](#comments) below.
- If the metadata cannot be expressed with the schema, do not work around it with a
  comment. Open an issue (here or in
  [metadata-schema](https://github.com/echemdb/metadata-schema/issues)) instead.
- Add yourself as `curator` in `curation.process` with your name, ORCID and the
  date.

### Comments

Every curve can carry a curator comment, which is shown on the page of the entry on
echemdb.org. For digitized figures it is the `comment:` text label in the SVG; for
source data it is `figureDescription.comment` in the YAML. Comments are complete
sentences ending with a period.

A curve comment is meant for notes on **the data and how it was obtained from the
figure**:

1. **Technical difficulties during tracing**: overlapping or stacked curves, broad or
   noisy lines, peaks exceeding the axis limits, curves cut off by the axes, gaps in
   the curve, imprecise axis labels.
2. **Values determined by the curator**: e.g. a zero-current baseline that is not given
   in the figure, a scan rate calculated from a reported charge, an estimated
   concentration.
3. **Apparent errors or inconsistencies in the original figure**: e.g. a potential axis
   possibly labeled vs. SHE instead of RHE, or a unit that cannot be represented. The
   data itself is **never corrected**; the issue is only noted.

It is **not** meant for

- the scientific context or the focus of the publication,
- experimental details that are not specific to the curve (electrolyte preparation,
  counter or reference electrode, …). These belong in the structured metadata, or in
  the `comment` of the corresponding YAML object (e.g. of a `source`, an electrolyte
  component, or a quantity),
- missing information: a field that is not given in the publication is simply left out,
- template placeholders.

Use the standard phrases wherever the same issue appears, so that the website shows a
consistent wording:

| Issue | Standard phrase |
| --- | --- |
| baseline not given | The zero-current baseline (j-axis offset) is not given in the figure and was estimated by the curator. |
| noisy original | The original curve is noisy. / The original curve is very noisy. |
| broad line | The curve is drawn with a broad line. |
| overlapping curves | The curve partly overlaps with other curves in the figure. |
| curve cut off | The curve is cut off by the figure axes at … |
| imprecise axis | The y-axis labels are imprecise. |
| scan rate calculated | The scan rate is not given in the publication. It was calculated by the curator from the reported charge as … |

### Checking your data

Run the checks **locally** before you push. CI runs them as well, but it is a safety
net, not the first test run.

```sh
pixi run -e dev validate-new-input   # schema, file names and bib keys of the entries you changed
pixi run check-news                  # news entries are well-formed
```

Helpful fixes (each has a `-dry-run` variant that only shows what would change):

```sh
pixi run -e dev fix-lowercase           # lowercase SVG labels and file names
pixi run -e dev fix-identifiers         # rename folders/files whose name differs from the citationKey
pixi run -e dev rename-identifiers OLD NEW
```

### Checking and correcting existing entries

Checking existing entries against their publications is just as valuable as adding
new ones, and needs nothing but the publication and the YAML files. Typical findings
are wrong units or reference electrodes, a missing scaling factor, electrode or
electrolyte details that are stated in the publication but missing in the metadata,
or values that are not stated in the publication at all.

If you find an error, either

- [open an issue](https://github.com/echemdb/electrochemistry-data/issues/new/choose)
  with the identifier, the figure and curve, what is wrong, and where the correct
  information is stated in the publication, or
- open a pull request that fixes only this entry, with a news entry under
  `**Fixed:**`.

---

## Part II: Technical contributions

### What lives where

| Path | Content |
| --- | --- |
| [`echemdb_ecdata/`](echemdb_ecdata) | Python package: batch conversion, validation, bibliography and fix utilities |
| [`pyproject.toml`](pyproject.toml) | dependencies and all pixi tasks (`pixi run` lists them) |
| [`data/`](data) | Makefile for the conversion into `data/generated/` (not committed) |
| [`.github/workflows/`](.github/workflows) | CI: tests, validation of input and generated data, news check |
| [`.github/prompts/`](.github/prompts) | instructions of the AI review assistants (the Claude skills in `.claude/skills/` only point to them; edit the prompt files) |
| [`util/`](util) | shell helpers |

The metadata itself is defined in
[metadata-schema](https://github.com/echemdb/metadata-schema). Its validation tools
(`mdstools`) are a dependency of this repository; keep the `mdstools` tag in
`pyproject.toml` in sync with `SCHEMA_VERSION` in
[`echemdb_ecdata/validate.py`](echemdb_ecdata/validate.py). After a breaking schema
release, `pixi run -e dev migrate-metadata` upgrades the YAML files in `literature/`.

### Checks

```sh
pixi run -e dev test       # doctests and pytest
pixi run -e dev lint       # pylint, black, isort
pixi run check-news        # news entries are well-formed
```

If you change the conversion or validation, also run it on the full data:

```sh
pixi run -e dev convert-force && pixi run -e dev verify-all   # output identical to before?
pixi run -e dev validate-input && pixi run -e dev validate-generated
```

To test with a specific Python version, use e.g. `pixi run -e python-312 test`.

Public functions should have docstrings with examples that serve as doctests. Do not
disable pylint checks; refactor instead.

---

## Submitting a pull request

### News entry

Every pull request adds `doc/news/<branch-name>.rst`. These files are merged into the
[`ChangeLog`](ChangeLog) when a release is made. Copy
[`doc/news/TEMPLATE.rst`](doc/news/TEMPLATE.rst) and

- keep **only the sections that have entries**. Delete all other sections, and never
  leave a `<news item>` placeholder in the file,
- use the section headers exactly as in the template: `**Added:**`, `**Changed:**`,
  `**Deprecated:**`, `**Removed:**`, `**Fixed:**`, `**Performance:**`,
- start each bullet with the verb of its section (`Added …`, `Changed …`, `Fixed …`,
  `Removed …`, `Deprecated …`, `Improved …`),
- write each entry so that it is understandable on its own (entries are merged and
  reordered), name the affected entries with RST double backticks
  (``` ``markovic_1996_oxygen_6715`` ```) and reference issues as `(#123)`,
- save as UTF-8 without BOM. On Windows, do not create the file with PowerShell
  `>`, `Set-Content` or `Out-File`; use your editor.

If your branch changes something that already has a news file, update that file
instead of adding a second one.

Changes that do not belong in the ChangeLog (CI configuration, typos in the
documentation, …) need no news entry. Name such a branch `silent-fix-<topic>`; CI then
skips the check that a news entry was added.

Example:

```rst
**Added:**

* Added cyclic voltammograms of Pt(111), Pt(100) and Pt(110) in 0.1 M KOH from ``markovic_1996_oxygen_6715``.
```

### Opening the pull request

Push to your fork and open a pull request against `echemdb/electrochemistry-data:main`:

```sh
git push -u <user> <branch>
```

- Name pull requests that add data `Add <identifier>`.
- Fill in the pull request template.
- If `origin/main` moves during the review, `git fetch origin` and merge or rebase.

### What happens after you submit

1. **CI** checks the pull request. For data: the changed entries (schema, file names,
   bibliography); for code: tests and the conversion of all data. The news entry is
   checked in both cases. Fix any failures; the logs tell you which file and which
   field.
2. **Review.** For data, a curator compares your files with the publication:
   identifiers, units, scaling factors, traced curves and metadata. The review may be
   assisted by an AI assistant that cross-checks the YAML against the PDF; all of its
   findings are checked by a curator. Reviewers may ask questions or push small fixes
   to your branch.
3. **Merge.** Once approved, the pull request is merged into `main`.
4. **Release.** With the next release, the data is converted, published as a
   [GitHub release](https://github.com/echemdb/electrochemistry-data/releases) and on
   [Zenodo](https://doi.org/10.5281/zenodo.20723429), and appears on
   [echemdb.org](https://www.echemdb.org/cv).

## License

Your contributions are published under the licenses of this repository, see
[License](README.md#license) in the README.
