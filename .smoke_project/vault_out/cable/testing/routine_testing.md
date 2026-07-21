---
type: concept
level: 0
entity_id: cable.testing.routine_testing
title: Routine Testing
domain: default
confidence: 0.5
schema_version: '1.0'
description: Manufacturing-stage tests performed on every cable length, including
  high-voltage withstand, partial discharge, and conductor resistance checks.
sources:
- source_id: 362871cd3841da0e
  source_path: C:\Users\botta\github\klustra\.smoke_project\corpus\testing_procedures.md
created_at: '2026-07-21T23:18:00.781161+00:00'
updated_at: '2026-07-21T23:18:00.781161+00:00'
---

# Routine Testing of High-Voltage Cables

**Routine testing** is a mandatory set of electrical and physical checks performed on every manufactured cable length before it leaves the factory. These tests verify that the cable meets the design specifications and is free from manufacturing defects. The procedures are defined in international standards such as [[IEC 62067]] (which also covers [[cable.testing.type_testing]]).

## Required Tests

Every manufactured cable length must pass the following three routine tests:^[362871cd3841da0e:narrative]

### High-Voltage Withstand Test
This test applies a voltage of **2.5 U₀** (where U₀ is the rated phase-to-earth voltage) to the cable for **30 minutes**. The cable must not suffer a dielectric breakdown during this period.^[362871cd3841da0e:narrative]  
See [[cable.testing.high_voltage_withstand_test]] for further details on the procedure.

### Partial Discharge Measurement
Partial discharge (PD) activity is measured under increased voltage. The acceptable limit is **less than 5 pC** (picocoulombs). Any measured PD above this threshold indicates a localized defect in the insulation system.^[362871cd3841da0e:narrative]  
Refer to [[cable.testing.partial_discharge_measurement]] for measurement techniques and interpretation.

### Conductor Resistance Check
A direct-current measurement of each conductor’s resistance is performed. The value must comply with the design specification (typically based on the conductor material, cross‑section, and length). This test ensures that the conductor is continuous and has the correct cross‑sectional area.^[362871cd3841da0e:narrative]  
See [[cable.testing.conductor_resistance_check]] for the measurement method and acceptance criteria.

## Relationship to Other Testing Stages

Routine testing is distinct from [[cable.testing.type_testing]] (which validates the cable design) and [[cable.testing.after_installation_testing]] (which verifies the installed cable system). Together, these three stages ensure a high‑voltage cable system’s reliability throughout its lifecycle.

## Storia e revisioni

No conflicting claims were identified in the available sources.

---

*confidence: 0.95*
