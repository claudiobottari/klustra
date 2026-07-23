---
type: concept
level: 0
entity_id: hv_cable_after_installation_testing
title: hv_cable_after_installation_testing
domain: default
confidence: 0.5
schema_version: '1.0'
description: On-site commissioning tests performed on high-voltage cable systems after
  installation to verify insulation integrity, sheath continuity, and joint quality.
tags:
- testing
- commissioning
- high-voltage cables
- quality assurance
sources:
- source_id: 362871cd3841da0e
  source_path: C:\Users\botta\github\klustra\.smoke_project\corpus\testing_procedures.md
created_at: '2026-07-22T05:45:56.459555+00:00'
updated_at: '2026-07-22T05:45:56.459555+00:00'
---

# After-Installation Testing of High-Voltage Cable Systems

**After-installation testing** (also called commissioning or site acceptance testing) verifies that a [[high_voltage_cable_systems]] installation is free from damage and correctly assembled before being energised. The tests are performed on-site after all [[hv_cable_jointing_requirements]] have been completed and before the cable is put into service.

## Scope and purpose

After-installation testing is distinct from [[hv_cable_type_testing]] (which validates the design) and [[hv_cable_routine_testing]] (which checks every manufactured length). Its purpose is to detect defects introduced during transport, handling, pulling, jointing, or termination. The tests confirm that the installed cable system can withstand normal and emergency operating stresses.

## Standard test methods

### DC or VLF withstand testing
A high-voltage withstand test is applied to the main insulation. Both DC (direct current) and VLF (very low frequency, typically 0.1 Hz) methods are accepted. The test voltage and duration are specified in the project requirements, often based on [[iec_62067]]. VLF testing is preferred for [[xlpe_insulation]] cables because DC testing can cause space-charge accumulation that may damage the insulation.^[362871cd3841da0e:1-2]

### Sheath integrity test
The outer sheath (or metallic sheath) is tested for continuity and absence of punctures. A typical procedure applies 10 kV DC for 1 minute between the sheath and ground. Any leakage current above the acceptable threshold indicates a sheath defect that must be located and repaired.^[362871cd3841da0e:2]

### Joint resistance measurement
The resistance of each [[hv_cable_jointing_requirements|joint]] is measured and compared with an equivalent length of continuous conductor. A high or unstable resistance indicates a poor connection, which could lead to overheating and failure under load.^[362871cd3841da0e:2]

## Interpretation and acceptance criteria

- **Withstand test**: No breakdown or flashover during the test duration.
- **Partial discharge**: If measured, the discharge level must be below the threshold specified in the contract (typically < 5 pC for XLPE cables).
- **Sheath integrity**: Leakage current must be stable and within the limits defined in the test procedure.
- **Joint resistance**: The measured value must not exceed the resistance of an equivalent conductor length by more than a specified percentage (commonly 20 %).

## Relation to other testing stages

After-installation testing is the final electrical check before commissioning. It complements [[hv_cable_routine_testing]] (factory tests on each drum length) and [[hv_cable_type_testing]] (design qualification). The results are recorded in the site test report and become part of the cable system’s as-built documentation.

## See also

- [[partial_discharge_measurement]]
- [[high_voltage_withstand_test]]
- [[sheath_integrity_test]]
- [[joint_resistance_measurement]]
- [[hv_cable_safety_standards]]
- [[hv_cable_regulatory_framework]]

## Storia e revisioni

No conflicting claims were found in the source material. The description of DC vs. VLF testing for XLPE cables is based on current best practice; earlier standards sometimes permitted DC testing for all insulation types, but that practice has been deprecated for XLPE due to space-charge risks.^[362871cd3841da0e:1-2]
