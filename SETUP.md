# Setup and Reproducibility Guide

This guide describes the validated Phase 1 environment for the `seismic-correlation-insurance-loss` project and the steps a fresh clone should follow before running the notebooks.

## 1. Supported environment

The completed notebooks record the following tested environment:

| Component | Validated value |
|---|---|
| Operating system | Windows 10 or Windows 11 |
| Python | Python 3.12.3 |
| Java | JDK 11, including both `java` and `javac` |
| USGS calculation source | `nshmp-haz 2.6.5` |
| Gradle | Gradle 7.3.1 wrapper included in the pinned USGS source archive |
| Notebook order | 01 through 07 |

The current Notebook 2 build procedure is Windows-specific because it invokes `cmd.exe` and `gradlew.bat`. The Python calculations are generally portable, but the full repository has only been validated end to end on Windows.

A machine with at least 20 GB of free disk space is recommended because the raw USGS model, downloaded Java source, compiled classes, ground-motion fields, and generated loss tables are intentionally not stored in Git.

## 2. Prerequisites

Install the following before cloning the repository:

1. Git.
2. A 64-bit Python 3.12 installation.
3. A full JDK 11 installation, not only a Java Runtime Environment.
4. A recent PowerShell version or Windows Command Prompt.

Verify the commands:

```powershell
python --version
git --version
java -version
javac -version
```

Both Java commands should report major version 11.

## 3. Clone the repository

```powershell
git clone https://github.com/NatCatAnalystRandle/seismic-correlation-insurance-loss.git
cd seismic-correlation-insurance-loss
```

Confirm that the seven notebooks are present:

```powershell
Get-ChildItem -Filter "*.ipynb" | Select-Object Name
```

## 4. Create the Python environment

Create a project-local virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

When PowerShell blocks activation, run this command once in the current terminal and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Register the kernel:

```powershell
python -m ipykernel install --user --name seismic-insurance-loss --display-name "Seismic Insurance Loss"
```

## 5. Validate the fresh clone

The repository validator uses only the Python standard library. Run it before opening Jupyter:

```powershell
python tools\validate_repository.py --profile runtime
```

The final milestone requires zero critical failures. Warnings should be reviewed and documented.

During development, uncommitted edits can be allowed explicitly:

```powershell
python tools\validate_repository.py --allow-dirty
```

To save a machine-readable report outside the repository:

```powershell
python tools\validate_repository.py `
  --profile runtime `
  --json-out "$env:TEMP\seismic_repository_validation.json"
```

## 6. Start Jupyter

```powershell
jupyter lab
```

Select the **Seismic Insurance Loss** kernel and run the notebooks in this order:

1. `01_download_and_inspect_usgs_nshm2018.ipynb`
2. `02_extract_usgs_rupture_rates.ipynb`
3. `03_generate_annual_event_catalog.ipynb`
4. `04_generate_ground_motion_fields.ipynb`
5. `05_calculate_ground_up_losses.ipynb`
6. `06_apply_insurance_terms.ipynb`
7. `07_baseline_results_and_validation.ipynb`

Do not generate separate event catalogs for the independent and spatially correlated cases. Phase 2 must reuse the validated Phase 1 catalog.

## 7. Inputs downloaded or generated locally

The repository intentionally excludes large and machine-generated files.

### Notebook 1

Notebook 1 downloads and verifies the official USGS `nshm-conus` release tagged `5.2.4`.

Expected archive SHA-256:

```text
c1b6e73f303ee4cee1ad057714d073eb9528c17168fee779c6c458df19dc0b47
```

The extracted model is written below:

```text
data/raw/usgs_nshm_conus_2018/
```

### Notebook 2

Notebook 2 downloads the official `nshmp-haz 2.6.5` source archive, verifies the pinned tag and commit, and uses its Gradle 7.3.1 wrapper to build the required Java classes. Downloaded source, compiled classes, JAR files, and build logs are excluded from Git.

### Exposure input

The enriched Seaside exposure workbook is local and is not distributed in the public repository. The current workflow expects:

```text
data/raw/exposure/seaside_nsi/gdf_NSI_Map_with_period_seaside.xlsx
```

A fresh clone can validate the repository and begin Notebooks 1 through 3 without this workbook. Notebook 4 cannot complete the portfolio ground-motion stage until the exposure file is supplied. The public metadata document the portfolio size and processed schema, but they do not replace the private source workbook.

## 8. Restartable workflow

Each notebook writes validation records and a handoff for the next stage. When resuming work:

1. Confirm the previous notebook's final validation passed.
2. Confirm the expected handoff file exists.
3. Do not manually edit generated numerical outputs.
4. Preserve the declared two-million-year catalog duration, including zero-event years.
5. Preserve seeds and random-stream specifications needed for the Phase 2 paired comparison.

## 9. Repository cleanliness

Before committing, run:

```powershell
python tools\validate_repository.py --allow-dirty
git status --short
git diff --check
```

After committing, run the final clean-worktree validation:

```powershell
python tools\validate_repository.py --profile runtime
git status --short
```

The final `git status --short` output should be empty.

## 10. Fresh-clone reproducibility test

Use a separate temporary directory so the test does not reuse local generated data:

```powershell
$TestRoot = Join-Path $env:TEMP "seismic-correlation-insurance-loss-fresh-clone"
Remove-Item $TestRoot -Recurse -Force -ErrorAction SilentlyContinue
git clone https://github.com/NatCatAnalystRandle/seismic-correlation-insurance-loss.git $TestRoot
Set-Location $TestRoot
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python tools\validate_repository.py --profile runtime
jupyter lab
```

For the smoke test, confirm that Notebook 1 opens, imports its dependencies, identifies the repository root, and begins the official USGS download and verification workflow. A complete computational rerun is a separate, longer test.

## 11. Reproducibility boundaries

The repository provides code, validation metadata, source-tool code, selected figures, and documentation. It does not provide every large generated table or the local enriched exposure workbook. Reproducibility therefore has two levels:

- **Repository reproducibility:** a clean clone can construct the environment, validate the public files, and begin the workflow.
- **Full computational reproduction:** the user also supplies the local exposure input and allows the notebooks to download and regenerate all excluded data and build artifacts.
