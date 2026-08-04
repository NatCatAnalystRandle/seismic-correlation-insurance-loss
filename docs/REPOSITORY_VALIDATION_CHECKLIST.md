# Final Repository Validation Checklist

This milestone is separate from the scientific and numerical validation performed inside Notebooks 01 through 07.

## Milestone definition

The repository-level milestone passes only when:

- automated checks report zero critical failures;
- the worktree is clean;
- a fresh clone can create the documented environment and begin the workflow;
- the GitHub repository and profile render correctly;
- no unnecessary generated data, secrets, credentials, or machine-specific paths are public.

Record the final commit SHA and validation date in the sign-off table at the end of this document.

Review [`REPOSITORY_AUDIT_FINDINGS.md`](REPOSITORY_AUDIT_FINDINGS.md) before beginning the sign-off checks.

## A. Automated validation

Run from the repository root:

```powershell
python tools\validate_repository.py --profile runtime
```

Confirm each item below:

- [ ] `README.md`, `SETUP.md`, `requirements.txt`, `.gitignore`, and `.gitattributes` exist and are tracked.
- [ ] Notebooks 01 through 07 have the exact intended names.
- [ ] Notebook numbering is continuous.
- [ ] Every notebook parses as valid version 4 notebook JSON.
- [ ] Notebook metadata consistently records Python 3.12.3.
- [ ] No duplicated `.ipynb.ipynb` extension exists.
- [ ] All required Notebook 2 through Notebook 7 handoff and final-validation files exist.
- [ ] All required Java and Gradle source files exist and are tracked.
- [ ] The four selected PNG figures exist, are tracked, and are linked from the README.
- [ ] Every local README link resolves to an existing repository path.
- [ ] Every notebook is linked from the README.
- [ ] The README contains a basic valid Mermaid workflow block.
- [ ] GitHub-compatible display-math delimiters are used.
- [ ] `.gitignore` contains the required data, environment, log, temporary, Java, Gradle, and notebook exclusions.
- [ ] No tracked file exceeds the selected 50 MiB threshold.
- [ ] No `.class`, `.log`, `.tmp`, cache, build, IDE, or downloaded USGS software artifact is tracked.
- [ ] No absolute user-home path occurs in tracked text.
- [ ] No obvious secret, credential, access token, password, or private key occurs in tracked text.
- [ ] `requirements.txt` covers all detected notebook imports and Excel-engine requirements.
- [ ] Python 3.12 and JDK 11 are available for the runtime profile.
- [ ] The Git worktree is clean.

Save a report outside the repository when an audit record is needed:

```powershell
python tools\validate_repository.py `
  --profile runtime `
  --json-out "$env:TEMP\seismic_repository_validation.json"
```

## B. Manual local checks

- [ ] Run `git diff --check` and confirm there are no whitespace errors.
- [ ] Run `git status --short` and confirm the output is empty.
- [ ] Run `git ls-files | Sort-Object` and review the complete tracked inventory.
- [ ] Confirm raw USGS model files are not tracked.
- [ ] Confirm the enriched local NSI workbook is not tracked.
- [ ] Confirm generated ground-motion, damage, loss, insurance, and reinsurance tables are not tracked unless intentionally selected.
- [ ] Confirm compiled Java classes, JAR files, Gradle caches, downloaded source archives, and build folders are not tracked.
- [ ] Confirm validation metadata retained in Git are small, interpretable, and needed for auditability.
- [ ] Open each selected PNG locally and confirm that it is readable, correctly labeled, and not cropped.
- [ ] Open all seven notebooks in Jupyter and confirm that the notebook kernel metadata is valid.
- [ ] Search the repository for personal directories, email credentials, keys, and private source data names.

Suggested searches:

```powershell
git grep -n -I -E "[A-Za-z]:[\\/]Users[\\/]"
git grep -n -I -E "BEGIN .*PRIVATE KEY|github_pat_|ghp_|AKIA|xox[baprs]-"
git ls-files | Select-String -Pattern "\.class$|\.log$|\.tmp$|__pycache__|\.ipynb_checkpoints|/build/|/\.gradle/"
```

## C. Fresh-clone reproducibility test

Use a directory outside the working repository.

- [ ] Clone the public repository into an empty temporary directory.
- [ ] Create a new Python 3.12 virtual environment.
- [ ] Install `requirements.txt` without reusing the original environment.
- [ ] Verify `python --version` reports Python 3.12.x.
- [ ] Verify both `java -version` and `javac -version` report major version 11.
- [ ] Run `python tools\validate_repository.py --profile runtime`.
- [ ] Launch JupyterLab.
- [ ] Open Notebook 1.
- [ ] Confirm Notebook 1 imports successfully and identifies the cloned repository root.
- [ ] Confirm Notebook 1 can begin the official USGS model download and checksum workflow.
- [ ] Confirm Notebook 2 can locate the JDK and is prepared to download the pinned `nshmp-haz 2.6.5` archive.
- [ ] Document that Notebook 4 requires the local enriched exposure workbook before full reproduction can continue.

## D. GitHub repository rendering

Open the public repository in a signed-out or private browser window.

- [ ] The repository is public and opens without authentication.
- [ ] The README loads from the default branch.
- [ ] The Mermaid workflow renders as a diagram rather than raw code or an indefinite loading placeholder.
- [ ] All display equations render correctly.
- [ ] The four selected PNG figures display in the README.
- [ ] Each figure is sharp enough to read at normal browser width.
- [ ] All seven notebook links open the intended notebook.
- [ ] Each notebook preview loads, or GitHub provides a valid raw/download view when the preview is too large.
- [ ] `SETUP.md` opens from the README.
- [ ] The repository validation checklist opens from the README.
- [ ] No README link returns a 404 page.
- [ ] The repository tree contains only intended notebooks, metadata, documentation, Java source, HAZUS references, selected figures, and repository support files.
- [ ] No unnecessary generated data are visible in the public tree.

## E. GitHub repository metadata

Recommended repository description:

```text
End-to-end earthquake catastrophe risk model using the USGS NSHM 2018 to simulate event catalogs, ground motions, building damage, insurance losses, reinsurance recoveries, AAL, AEP, OEP, and PML.
```

Recommended topics:

```text
catastrophe-modeling
earthquake-risk
seismic-risk
insurance
reinsurance
stochastic-simulation
usgs-nshm
python
jupyter-notebook
risk-analysis
```

Confirm:

- [ ] The repository description matches the project scope.
- [ ] The repository website field is either intentionally blank or points to the intended portfolio page.
- [ ] Repository topics are added.
- [ ] The default branch is `main`.
- [ ] The repository is pinned to the GitHub profile.
- [ ] The repository does not display an unintended release, package, deployment, or environment.

## F. GitHub profile validation

Open `https://github.com/NatCatAnalystRandle` in a signed-out or private browser window.

- [ ] The profile README appears on the Overview tab.
- [ ] The project section accurately describes the completed Phase 1 baseline.
- [ ] The project repository link opens the correct public repository.
- [ ] The repository is visible in the pinned or popular repositories section.
- [ ] The profile bio, LinkedIn link, and contact information are current.
- [ ] The profile does not expose information that should remain private.

## G. Final security and privacy review

- [ ] Review the full Git history, not only the current files, for accidentally committed secrets or private data.
- [ ] Confirm no secret was committed and later merely deleted.
- [ ] Confirm no personal Windows username or private directory appears in current tracked text.
- [ ] Confirm no access token, API key, password, credential file, SSH key, or cloud credential is tracked.
- [ ] Confirm no raw licensed, confidential, or personally identifiable exposure data are tracked.
- [ ] Confirm email addresses and contact information shown publicly are intentional.
- [ ] Enable available GitHub security alerts and secret scanning settings.

When a real secret has ever been committed, rotate or revoke it immediately. Removing it from the latest commit is not sufficient.

## H. Milestone sign-off

| Item | Value |
|---|---|
| Validation date | `YYYY-MM-DD` |
| Validated commit SHA | `<commit-sha>` |
| Validator profile | `runtime` |
| Critical failures | `0` |
| Warnings reviewed | `<count>` |
| Fresh-clone smoke test | `PASS` |
| GitHub README rendering | `PASS` |
| GitHub profile validation | `PASS` |
| Reviewer | `Emmanuel Randle` |

Final milestone status:

- [ ] **REPOSITORY-LEVEL AND REPRODUCIBILITY VALIDATION COMPLETE**
