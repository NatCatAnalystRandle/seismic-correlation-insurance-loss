# Repository Audit Findings

Audit date: 2026-08-03
Repository: `NatCatAnalystRandle/seismic-correlation-insurance-loss`
Milestone: Phase 1 repository hardening and reproducibility validation

## Audit status

**Current status: not yet ready for final sign-off.**

The scientific and computational validation inside Notebooks 01 through 07 is complete. The repository-level milestone remains open until the hardening files in this package are committed, machine-specific paths are removed or converted to portable path resolution, the automated validator passes on the local repository, and the GitHub manual checks are completed.

## Confirmed strengths

The public repository currently contains:

- the seven intended Phase 1 notebooks with continuous numbering from 01 through 07;
- the committed Java and Gradle source tools used for USGS rupture-rate extraction and Parker GMM support;
- extensive notebook validation metadata and handoff records;
- the four selected PNG figures intended for public display;
- a substantive project README;
- a public GitHub profile README with a working link to the project;
- the intended repository description.

The notebook metadata consistently records Python 3.12.3. The validated Notebook 2 build used JDK 11, the pinned `nshmp-haz 2.6.5` source, and its Gradle 7.3.1 wrapper.

## Blocking findings

### 1. Environment files are not yet committed

The current public repository does not contain `requirements.txt` or `SETUP.md`. The files supplied in this hardening package address that gap.

### 2. Repository-level validation is not yet automated in the public repository

The current public repository does not contain `tools/validate_repository.py` or the final manual checklist. The supplied validator checks structure, notebook integrity, handoffs, Java source files, figures, README links, dependencies, Git exclusions, tracked file size, generated artifacts, machine-specific paths, obvious credentials, and Git status.

### 3. Machine-specific paths remain in tracked notebook and metadata text

Several notebooks and metadata records contain absolute Windows paths beginning with a user home directory, including paths of the form:

```text
<user-home>/Documents/GitHub/seismic-correlation-insurance-loss/...
```

These are not credentials, but they are machine-specific and prevent an unqualified claim that a fresh clone is portable. Source cells should derive the repository root from `Path.cwd()` and its parents. Metadata intended for public Git should record repository-relative paths whenever possible.

### 4. Notebook 2 is currently Windows-specific

The validated Notebook 2 workflow invokes `cmd.exe` and `gradlew.bat`. The setup guide therefore documents Windows 10 or Windows 11 as the supported end-to-end environment. Cross-platform support would require a separate implementation using `gradlew` on macOS and Linux.

### 5. Full reproduction requires a local exposure workbook

The public repository excludes the enriched Seaside exposure workbook expected at:

```text
data/raw/exposure/seaside_nsi/gdf_NSI_Map_with_period_seaside.xlsx
```

This is a legitimate data-management boundary, but it must be stated clearly. A clean clone can construct the environment, validate public files, and begin the workflow. Notebook 4 cannot complete the production portfolio calculations until the local workbook is supplied.

### 6. README rendering needs revision

The current README contains a Mermaid source block, but visual rendering must still be confirmed manually in a browser. The current display equations use backslash-bracket delimiters that do not render reliably in the GitHub page parser. The supplied revised README uses `$$` display delimiters.

The four selected PNGs are present in the repository but are not embedded in the current README. The revised README embeds all four and makes the seven notebook names clickable.

### 7. `.gitignore` needs broader repository-hygiene exclusions

The current `.gitignore` covers major generated datasets and several Java artifacts, but it does not comprehensively exclude project virtual environments, generic environment files, all logs and temporary files, Gradle build folders, IDE settings, or operating-system artifacts. The supplied replacement expands those protections while preserving the four selected PNG exceptions.

## Checks that require Emmanuel's local repository

The following cannot be certified from the public web view alone:

- the current local `git status` is clean;
- no uncommitted generated files are present;
- the complete tracked-file size audit passes;
- the secret and credential scan passes across all tracked text;
- no machine-specific path remains after cleanup;
- the runtime validator passes with Python 3.12 and JDK 11;
- a separate fresh clone installs successfully and begins Notebook 1;
- the full Git history has never contained a real secret or private data file.

## GitHub checks still requiring manual confirmation

Use a signed-out or private browser window to confirm:

- the Mermaid diagram renders fully rather than remaining on a loading placeholder;
- all four README figures display;
- all seven notebooks open;
- the repository topics are present;
- the repository is pinned to the profile;
- the profile README, repository link, description, and public tree are correct;
- unnecessary generated data are not exposed.

## Required next action

Copy the supplied files into the repository, replace the current README and `.gitignore`, then run:

```powershell
python tools\validate_repository.py --allow-dirty
```

Resolve every critical failure, especially all reported absolute home paths. After committing, run:

```powershell
python tools\validate_repository.py --profile runtime
git status --short
git diff --check
```

The repository-level milestone should be signed off only when the runtime validator reports zero critical failures, the worktree is clean, the fresh-clone smoke test passes, and every manual GitHub check is complete.
