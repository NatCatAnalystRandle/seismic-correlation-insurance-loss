# HAZUS Reference Data

This folder contains the HAZUS-derived fragility, repair-cost-ratio, and replacement-cost tables used in the `seismic-correlation-insurance-loss` project.

These files are treated as reference inputs. They should not be edited directly during model execution. Any cleaned, filtered, corrected, or project-specific tables generated from them should be written to:

```text
data/processed/notebook_5_damage_loss_parameters/
```

## Folder Structure

```text
data/reference/hazus/
├── fragility/
│   ├── HAZUS_Structural_Fragility_Source.xlsx
│   ├── HAZUS_Nonstructural_Drift_Sensitive_Fragility.xlsx
│   └── HAZUS_Nonstructural_Acceleration_Sensitive_Fragility.xlsx
├── repair_cost_ratios/
│   ├── HAZUS_Structural_Repair_Cost_Ratios.xlsx
│   ├── HAZUS_Drift_Sensitive_Nonstructural_Repair_Costs.xlsx
│   └── HAZUS_Acceleration_Sensitive_Nonstructural_Repair_Costs.xlsx
└── replacement_costs/
    ├── HAZUS_Structure_Replacement_Costs.xlsx
    └── HAZUS_RES1_Replacement_Costs.xlsx
```

## File Inventory

### Fragility Workbooks

#### `HAZUS_Structural_Fragility_Source.xlsx`

Contains structural fragility parameters by structural type and seismic design level.

The workbook contains four worksheets:

- `HighCode`
- `ModerateCode`
- `LowCode`
- `PreCode`

Each worksheet includes four structural damage-state thresholds:

- Slight
- Moderate
- Extensive
- Complete

The median columns are currently named:

```text
sli_mod
mod_med
ext_med
com_med
```

The first column name appears to use `sli_mod` where `sli_med` would be more consistent with the other median columns. The source workbook is retained unchanged, and this naming difference must be handled explicitly when the table is imported.

The corresponding dispersion columns are:

```text
sli_beta
mod_beta
ext_beta
com_beta
```

The structural median values are interpreted as spectral-displacement thresholds, not direct spectral-acceleration thresholds. Therefore, this source workbook must not be applied directly to `sa0p4_simulated_g` without a documented transformation or a separately validated direct-IM fragility model.

For the current Seaside portfolio, the relevant structural type is `W2`.

#### `HAZUS_Nonstructural_Drift_Sensitive_Fragility.xlsx`

Contains drift-sensitive nonstructural fragility parameters by structural type and seismic design level.

The workbook uses the same four design-level worksheets and the same four damage states as the structural fragility workbook.

The median values are interpreted as spectral-displacement thresholds. They should therefore be paired with an appropriate displacement-based engineering demand parameter and should not be treated as direct acceleration thresholds.

The source workbook also uses `sli_mod` for the Slight-damage median column. This should be normalized to `sli_med` only in a generated, project-specific table.

#### `HAZUS_Nonstructural_Acceleration_Sensitive_Fragility.xlsx`

Contains acceleration-sensitive nonstructural fragility parameters by structural type and seismic design level.

The workbook uses the following median columns:

```text
sli_med
mod_med
ext_med
com_med
```

and the corresponding beta columns:

```text
sli_beta
mod_beta
ext_beta
com_beta
```

The median values are interpreted as spectral-acceleration thresholds in units of `g`. These parameters must be matched to the intensity measure required by the selected HAZUS methodology. They should not automatically be assigned to PGA or `SA(0.4)` without confirming the intended acceleration measure.

### Repair-Cost-Ratio Workbooks

#### `HAZUS_Structural_Repair_Cost_Ratios.xlsx`

Contains occupancy-specific structural repair-cost ratios for four paid damage states.

The columns are:

```text
DS_0
DS_1
DS_2
DS_3
```

These map to the project damage-state convention as follows:

| Project state | Damage state | HAZUS column |
|---:|---|---|
| 0 | None | 0.0 |
| 1 | Slight | `DS_0` |
| 2 | Moderate | `DS_1` |
| 3 | Extensive | `DS_2` |
| 4 | Complete | `DS_3` |

Values in the workbook are percentages of total building replacement value. They must be divided by 100 before use as decimal loss ratios.

#### `HAZUS_Drift_Sensitive_Nonstructural_Repair_Costs.xlsx`

Contains occupancy-specific repair-cost ratios for drift-sensitive nonstructural components.

Values are percentages of total building replacement value and must be converted to decimals before use.

These ratios should be applied to drift-sensitive nonstructural damage states only. They should not be assigned using the sampled structural damage state.

#### `HAZUS_Acceleration_Sensitive_Nonstructural_Repair_Costs.xlsx`

Contains occupancy-specific repair-cost ratios for acceleration-sensitive nonstructural components.

Values are percentages of total building replacement value and must be converted to decimals before use.

These ratios should be applied to acceleration-sensitive nonstructural damage states only. They should not be assigned using the sampled structural damage state.

## Replacement-Cost Workbooks

### `HAZUS_Structure_Replacement_Costs.xlsx`

Contains structure replacement costs by occupancy class in dollars per square foot.

The main cost column is:

```text
Structure Replacement Cost ($/ft²)
```

The replacement value for a building is calculated as:

```text
building floor area in ft² × replacement cost in $/ft²
```

The workbook identifies RES1 as requiring a separate replacement-cost table.

### `HAZUS_RES1_Replacement_Costs.xlsx`

Contains 2022 RES1 replacement costs in dollars per square foot.

Costs vary by:

- construction class;
- height class;
- basement condition.

This workbook is only required when RES1 occupancies are present in the modeled portfolio. The Seaside W2 commercial portfolio should be checked before use rather than assuming that RES1 records are absent.

## Intended Use in Notebook 5

Notebook 5 will use these files to develop a HAZUS-informed damage and ground-up loss model.

The current planned structural workflow is:

```text
simulated SA(0.4)
→ validated direct-IM W2 structural fragility
→ structural damage state
→ occupancy-specific structural repair-cost ratio
→ structural ground-up loss
```

The source structural fragility workbook is displacement-based. A separate validated table must therefore be created before the project applies a direct `SA(0.4)` structural fragility model.

The full building-repair-loss model may later include:

```text
structural repair loss
+ drift-sensitive nonstructural repair loss
+ acceleration-sensitive nonstructural repair loss
```

Each component must use its own fragility model and sampled damage state.

Contents loss is not included in the current reference-data package and must remain separate unless an appropriate contents-value and contents-damage model is added.

## Data-Handling Rules

1. Preserve the original Excel workbooks unchanged.
2. Do not silently replace missing structural types, design levels, occupancies, or cost values.
3. Do not substitute W1 fragility parameters for W2 buildings.
4. Join exposure, ground-motion, damage, and loss data using stable identifiers such as `site_id` and `occurrence_id`.
5. Convert repair-cost percentages to decimal ratios before calculating loss.
6. Record the source-file hash for every parameter table used in production.
7. Write cleaned or project-specific tables to the processed-data directory.
8. Reuse deterministic damage-state random draws in later independent-versus-correlated comparisons.
9. Keep structural, drift-sensitive, acceleration-sensitive, and contents losses separate before calculating total ground-up loss.
10. Document any corrected or excluded source values rather than editing them silently.

## Generated Project-Specific Tables

Notebook 5 is expected to generate validated files such as:

```text
data/processed/notebook_5_damage_loss_parameters/
├── seaside_w2_structural_fragility_parameters.csv
├── hazus_repair_cost_ratios_validated.csv
├── seaside_w2_replacement_values.csv
└── notebook_5_parameter_assignment_audit.csv
```

Each generated table should include source-file provenance, units, transformation notes, and validation status.

## Source and Version Information

The exact HAZUS release, technical-manual table numbers, original download locations, and extraction dates are not recorded inside the supplied workbooks.

Complete the following fields when the original sources are confirmed:

```text
HAZUS release/version:
Technical manual or inventory document:
Relevant table numbers:
Original source URL:
Date accessed:
Person who extracted or assembled the tables:
Transformations performed before inclusion:
```

Until those fields are completed, the workbooks should be described as HAZUS-derived reference tables rather than as verified extracts from a specific HAZUS release.

## Known Items Requiring Validation

Before production use, Notebook 5 must verify:

- the exact source and HAZUS version for every workbook;
- the units of all fragility medians;
- the design-level assignment rules for the Seaside inventory;
- the mapping between portfolio occupancy codes and HAZUS occupancy classes;
- the W2 structural fragility parameters selected for the direct-IM model;
- the intended acceleration measure for acceleration-sensitive nonstructural fragility;
- the dollar year of all general replacement-cost values;
- any repair-cost rows whose component totals do not reconcile as expected;
- whether inflation or regional cost adjustment is required.

## Project Scope

These tables support the Phase 1 no-spatial-correlation baseline. The same exposure, annual event catalog, consequence parameters, and deterministic damage random streams should be reused in the later spatial-correlation extension so that changes in portfolio loss can be attributed to the dependence model rather than unrelated input changes.
