# Skill: Review Literature Addition PR

## Purpose

Automate the review of pull requests that add new literature data to the echemdb electrochemistry-data repository. This replaces the manual review checklist from `.github/pull_request_template.md`.

## When to Use

Use this skill when:
- A PR adds new files under `literature/svgdigitizer/` or `literature/source_data/`
- The user asks to "review" a literature PR or data submission
- Validation errors occur and the user wants a comprehensive review

## Review Process

### Step 1: Run Input Validation First

```bash
pixi run -e dev validate-input
```

This is the first thing to run. It performs schema validation, filename checks,
identifier matching, and bib key validation across all input files. Any failures
here are critical and must be resolved before proceeding. Report all errors.

### Step 2: Identify Changed Entries

Run `git diff main --name-only` to find new/modified files. Focus on directories under:
- `literature/svgdigitizer/{identifier}/` — SVG-digitized data
- `literature/source_data/{identifier}/` — Raw experimental data
- `literature/bibliography/bibliography.bib` — Bibliography entries

### Step 3: Run the Review Module

```python
from echemdb_ecdata.review import review_entry, format_report
report = review_entry("literature/svgdigitizer/{identifier}")
print(format_report(report))
```

This performs the following checks automatically:

#### Filename Checks
- All filenames and directory names are lowercase
- Filenames follow `{citationKey}_f{figure}_{curve}.{ext}` pattern
- Each SVG has a matching YAML file
- Filenames start with the directory name (= citation key)

#### Bibliography Checks
- `citationKey` in YAML matches the directory name
- Bibliography entry exists in `bibliography.bib`
- Computed identifier (via `svgdigitizer.pdf.Pdf.build_identifier`) matches the citation key
- Title has no spurious spaces before parentheses (e.g., `Pt (111)` → `Pt(111)`)

#### SVG Checks
- Has `tags` text label (BCV, ORR, etc.)
- Has `figure` text label in correct format (number only, not prefixed with 'f')
- Has `curve` text label (short, unambiguous)
- Has `scan rate` text label
- All axis labels present (E1, E2, j1, j2)
- Reference electrode in SVG axes matches YAML

#### YAML Checks
- `citationKey` matches directory name
- Required sections present: `curation`, `source`, `system`
- Source URL is a valid DOI
- Electrolyte has `type` and `components`
- Working electrode and reference electrode defined
- Curator has ORCID

#### PDF Cross-Validation
The review module downloads the paper via DOI and extracts text to verify:
- Electrolyte components mentioned in paper
- Concentration values match
- Electrode material matches
- Crystallographic orientation matches
- pH value matches
- Scan rate matches
- Reference electrode matches
- Purity/grade info matches
- Supplier names match

### Step 4: Manual Cross-Checks and Enrichment (Agent MUST Do)

After automated checks, the agent MUST read the PDF text and add findings as
numbered actionable items in the REVIEW.md. Each finding gets the same decision
box format (accept / reject / comment) so the reviewer can decide.

Key checks to perform by reading the PDF experimental section:

1. **Missing metadata from PDF**: Compare PDF experimental section against YAML fields.
   Look for manufacturer/supplier names, purity grades, preparation details that
   are in the paper but missing from the YAML. Add as ENRICHMENT items with
   proposed YAML additions.
2. **Axis units and potential range**: Confirm SVG axis values match the paper's
   figure description. Add as VERIFY item.
3. **Spelling consistency**: Check that chemical names, brand names, and technical
   terms in the YAML match common/correct spelling (e.g., `Milli-Q` vs `MilliQ`).
   Add as VERIFY item.
4. **Counter/auxiliary electrode**: Check if the paper mentions a CE. If not, note
   that its omission is acceptable. Add as VERIFY item.
5. **Preparation procedure**: Verify the description matches the paper. Check
   that comments are complete sentences ending with a period.

### Step 5: Generate REVIEW.md Report

Generate `REVIEW.md` at the **repository root** (not inside the entry directory).
This file is listed in `.gitignore` and must not be committed.

The report has two sections:

**Section 1 — Actionable Issues** (numbered, each with decision boxes):

Each issue follows this format:
```markdown
## {N}. {title} ({severity})

**Category:** {category}

**Evidence from PDF:** *"quoted text from paper"*

{Explanation and comparison with established entries}

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
- **VERIFY** — needs human judgment, no automated fix

**Section 2 — Automated Checks Summary** (checklist of all passing/failing checks).

**Section 3 — Curator Notes** (free-form): An optional `## Curator Notes` section at the
end of the report where the curator can leave general observations, context, open questions,
or remarks not covered by the structured issues above. The section is pre-populated with a
blockquote placeholder by `write_review_report` and should be filled in manually if needed.

Generate the report using:
```python
from echemdb_ecdata.review import review_entry, write_review_report
path = write_review_report("literature/svgdigitizer/{identifier}", output_path="REVIEW.md")
```

This writes to the repo root. Then manually append the Step 4 findings as additional numbered items.

### Step 6: Review Decisions and Apply Fixes

After the reviewer marks decisions in REVIEW.md, read it back and apply accepted fixes:

```python
from echemdb_ecdata.review import parse_review_report
issues = parse_review_report("REVIEW.md")
for issue in issues:
    if issue["decision"] == "accept":
        # Apply the proposed fix (rename command, YAML edit, etc.)
        pass
```

Each parsed issue returns: `number`, `title`, `category`, `decision`, `notes`, `fix_command`.

**Important:** REVIEW.md is saved at the repo root and listed in `.gitignore`.
Do not commit it — it is an internal review artifact.

### Step 7: Commit, Push, and Post Review Comment

After all accepted fixes are applied and validation passes, **ask the reviewer
for confirmation**, then:

1. **Commit the changes** with a `Co-authored-by` trailer so the Copilot avatar
   appears on the commit in GitHub:
   ```bash
   git add -A
   git commit -m "review: apply fixes for {identifier}

   Co-authored-by: github-copilot[bot] <noreply@github.com>"
   ```
   Note: `Co-authored-by` makes Copilot visible on individual commits but does
   **not** add it as a PR participant. The PR participants sidebar only lists
   accounts that commented, reviewed, or were requested for review.

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
   The PR number is available from the repository context attachment (e.g., PR #107).
   Include the full REVIEW.md content with the reviewer's decisions marked.

**Important:** Always ask the reviewer before committing, pushing, or posting.

### Step 8: Ensure News File Exists

Every PR must include a news file in `doc/news/`. Check if one exists; if not,
create it based on `doc/news/TEMPLATE.rst`.

- **Naming**: Use the identifier or a short descriptive slug, e.g.,
  `doc/news/{identifier}.rst` or `doc/news/add-{identifier}.rst`
- **Content**: Fill in the `**Added:**` section with a brief description of the
  figures/data added, e.g.:
  ```rst
  **Added:**

  * Added figure 2 from Hirai et al., 2000.
  ```
- **Check**: Verify the file exists before committing. If missing, create it and
  include it in the commit.

## Key References

- PR checklist: `.github/pull_request_template.md`
- Naming convention: `{citationKey}_f{figure}_{curve}.{ext}` where citationKey = `{author}_{year}_{title_word}_{first_page}`
- Review module: `echemdb_ecdata/review.py`
- Validation: `pixi run -e dev validate-input`
- Bibliography: `literature/bibliography/bibliography.bib`
- Metadata schema: https://github.com/echemdb/metadata-schema

## Common Issues

1. **BIB MISMATCH**: Citation key in YAML doesn't match bibliography.bib — check spelling and that the bib entry was added
2. **Figure label format**: Should be `2` not `f2` in the SVG text label
3. **Missing tags**: Every SVG must have a `tags:` text node
4. **Uppercase in filenames**: All identifiers must be lowercase (Windows compatibility)
5. **Missing counter electrode**: The PR checklist expects WE, RE, and optionally CE
