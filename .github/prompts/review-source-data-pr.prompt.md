# Skill: Review Source Data Addition PR

## Purpose

Automate the review of pull requests that add new raw/source data to the echemdb
electrochemistry-data repository under `literature/source_data/`. Unlike SVG-digitized
entries, source data is submitted as CSV files with YAML metadata — no SVG is involved.
Data correctness and conversion are verified automatically; this review focuses on
identifiers, metadata completeness, and cross-checking the YAML against the PDF.

## When to Use

Use this skill when:
- A PR adds new files under `literature/source_data/`
- The user asks to "review" a source data PR or raw data submission

## Review Process

### Step 1: Run Input Validation First

```bash
pixi run -e dev validate-input
```

Run this first. It performs schema validation, filename checks, identifier matching,
and bib key validation across all input files. Any failures are critical and must be
resolved before proceeding. Report all errors.

### Step 2: Identify Changed Entries

Run `git diff main --name-only` to find new/modified files. Focus on directories under:
- `literature/source_data/{identifier}/` — Raw experimental data
- `literature/bibliography/bibliography.bib` — Bibliography entries

### Step 3: Identifier and Filename Checks

Verify manually:
- Directory name matches the `citationKey` in every YAML file in that directory
- All filenames are lowercase
- Filenames follow the pattern `{citationKey}_f{figure}_{curve}.{ext}`
- Each CSV file has a matching YAML file
- Filenames start with the directory name (= citation key)
- The `citationKey` in the YAML matches an entry in `literature/bibliography/bibliography.bib`

### Step 4: YAML Structure Checks

Verify the YAML contains the required sections and fields:

#### `source` section
- `citationKey` matches directory name
- `url` is a valid DOI
- `figure` is present
- `curve` is present
- `originalFilename` matches the actual CSV filename

#### `figureDescription` section
- `type` is present (e.g., `raw`)
- `measurementType` is present (e.g., `CV`, `CA`)
- `scanRate` is present if the measurement type requires it — **note**: this value may
  differ from what is shown in the published figure, since the paper may show processed
  or normalized data. If the scan rate cannot be determined from the paper, flag it as
  a curator checklist item.

#### `dataDescription` section
- `dialect` block is present with `delimiters`, `decimal`, `encoding`, `headerLines`, `columnHeaderLines`
- `fieldMapping` maps original column headers to standardized names
- `fieldUnits` lists units and (for potential columns) `reference` electrode

#### `system` section
- `type: electrochemical` is present
- `electrodes` contains at least a working electrode (`WE`) and reference electrode (`REF`)
- Working electrode has `material`, `crystallographicOrientation`
- Reference electrode has `type`
- `electrolyte` has `type` and `components`

#### `curation` section
- At least one entry with `role`, `name`, `orcid`, `date`
- ORCID is a valid URL

### Step 5: PDF Cross-Validation (Agent MUST Do)

Read the PDF (located at `literature/source_data/{identifier}/{identifier}.pdf`) and
cross-check the YAML metadata against the paper's experimental section. Add findings
as numbered actionable items in REVIEW.md.

Key items to verify from the PDF:

1. **Electrolyte components**: All components in the YAML are mentioned in the paper.
   Check concentrations, solvents, and supporting electrolytes.
2. **Electrode material and orientation**: Working electrode material and crystallographic
   orientation match the paper.
3. **Reference electrode**: The reference electrode type in the YAML matches the paper.
   Note: the column unit `reference` in `fieldUnits` should correspond to the RE used
   during the measurement, which may differ from the RE used in the figure axis labels
   in the published paper (raw data is often recorded vs. a pseudo-reference).
4. **Temperature**: If stated in the paper, verify it matches the YAML (default: 298.15 K).
5. **Supplier and purity**: If the paper lists reagent grades, suppliers, or water
   purification systems, verify these are captured in the YAML `source` fields.
6. **Electrochemical cell type**: If the paper describes a specific cell setup, check
   whether the `electrochemicalCell` block is present and accurate.
7. **Preparation procedure**: If the paper describes electrode preparation (e.g., flame
   annealing), verify the `preparationProcedure` field is present and matches.

**Important caveats for source data:**
- Raw data columns (e.g., `E`, `I`, `t`) may use different units or potential scales
  than the axes in the published figure — the paper's figure shows processed data.
  Do **not** flag unit mismatches between the CSV and the figure as errors; flag them
  as VERIFY items for the curator if clarification is needed.
- Scan rate may not be explicitly stated in the paper if only processed data is shown.
  Flag as a curator checklist item if it cannot be confirmed.

### Step 6: Generate REVIEW.md Report

Generate `REVIEW.md` at the **repository root** (not inside the entry directory).
This file is listed in `.gitignore` and must not be committed.

The report has three sections:

**Section 1 — Actionable Issues** (numbered, each with decision boxes):

Each issue follows this format:
```markdown
## {N}. {title} ({severity})

**Category:** {category}

**Evidence from PDF:** *"quoted text from paper"*

{Explanation and comparison with YAML}

**Proposed fix:** {code block or description}

**Decision:**
- [ ] accept
- [ ] reject
- [ ] comment

**Reviewer notes:**
>
```

Severity levels:
- **ERROR** — must be fixed for validation to pass
- **ENRICHMENT** — metadata present in PDF but missing from YAML (optional but recommended)
- **VERIFY** — needs human judgment; cannot be resolved automatically

**Section 2 — Automated Checks Summary** (checklist of all passing/failing checks).

**Section 3 — Curator Checklist** (items that cannot be verified from the PDF alone):

```markdown
## Curator Checklist

Items that require the curator's direct knowledge of the data:

- [ ] Scan rate value is correct (cannot always be confirmed from the published figure)
- [ ] Column units in `fieldUnits` match the actual measurement conditions (raw data
      may use a different potential reference than the published figure)
- [ ] `originalFilename` is the actual filename of the raw data file as received
- [ ] All curves from the figure that are relevant have been submitted
- [ ] No additional metadata is available that should be captured
```

**Section 4 — Curator Notes** (free-form):

An optional section where the curator can leave general observations, context,
open questions, or remarks not covered by the structured issues above.

### Step 7: Review Decisions and Apply Fixes

After the reviewer marks decisions in REVIEW.md, read it back and apply accepted fixes
(YAML edits, filename renames, bibliography corrections, etc.).

**Important:** REVIEW.md is saved at the repo root and listed in `.gitignore`.
Do not commit it — it is an internal review artifact.

### Step 8: Commit, Push, and Post Review Comment

After all accepted fixes are applied and validation passes, **ask the reviewer
for confirmation**, then:

1. **Commit the changes**:
   ```bash
   git add -A
   git commit -m "review: apply fixes for {identifier}

   Co-authored-by: github-copilot[bot] <noreply@github.com>"
   ```

2. **Push to the PR branch** (ask before pushing):
   ```bash
   git push
   ```

3. **Post the review report as a PR comment** using the GitKraken MCP tool:
   ```
   mcp_gitkraken_issues_add_comment(
       provider="github",
       repository_organization="echemdb",
       repository_name="electrochemistry-data",
       issue_id="{pr_number}",
       comment=<contents of REVIEW.md>
   )
   ```
   The PR number is available from the repository context attachment.
   Include the full REVIEW.md content with the reviewer's decisions marked.

**Important:** Always ask the reviewer before committing, pushing, or posting.

### Step 9: Ensure News File Exists

Every PR must include a news file in `doc/news/`. Check if one exists; if not,
create it based on `doc/news/TEMPLATE.rst`.

- **Naming**: `doc/news/{identifier}.rst` or `doc/news/add-{identifier}.rst`
- **Content**: Fill in the `**Added:**` section with a brief description, e.g.:
  ```rst
  **Added:**

  * Added raw data for figure 1 from Schoenig et al., 2023.
  ```

## Key References

- PR checklist: `.github/pull_request_template.md`
- Naming convention: `{citationKey}_f{figure}_{curve}.{ext}` where citationKey = `{author}_{year}_{title_word}_{first_page}`
- Validation: `pixi run -e dev validate-input`
- Bibliography: `literature/bibliography/bibliography.bib`
- Metadata schema: https://github.com/echemdb/metadata-schema

## Common Issues

1. **BIB MISMATCH**: Citation key in YAML doesn't match `bibliography.bib` — check spelling and that the bib entry was added
2. **Uppercase in filenames**: All identifiers must be lowercase (Windows compatibility)
3. **Missing `originalFilename`**: Must exactly match the submitted CSV filename
4. **Wrong `reference` in `fieldUnits`**: Should reflect the actual RE used during measurement, not the axis label in the published figure
5. **Missing `columnHeaderLines`**: Must match the actual number of header rows in the CSV
6. **Unit mismatch in `geometricElectrolyteContactArea`**: Value and unit should be separate fields, not combined (e.g., `value: 0.196`, `unit: cm2`)
