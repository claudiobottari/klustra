---
type: concept
level: 0
entity_id: cable.testing.partial_discharge_measurement
title: Partial discharge measurement
domain: default
confidence: 0.5
schema_version: '1.0'
description: Partial discharge measurement is a non-destructive diagnostic test used
  to detect localized dielectric breakdowns in high-voltage cable insulation. It is
  a mandatory routine test per IEC 62067, with a threshold of <5 pC, and is also part
  of type testing for design validation.
tags:
- cable testing
- partial discharge
- IEC 62067
- routine testing
- type testing
sources:
- source_id: 362871cd3841da0e
  source_path: C:\Users\botta\github\klustra\.smoke_project\corpus\testing_procedures.md
created_at: '2026-07-21T23:18:00.781186+00:00'
updated_at: '2026-07-21T23:18:00.781186+00:00'
---

## Partial Discharge Measurement

Partial discharge (PD) measurement is a non‑destructive diagnostic technique used to detect localized dielectric breakdowns within the insulation of high‑voltage cables. It is a critical test in both **type testing** and **routine testing** of cable systems, as specified in IEC 62067.

### Role in Type Testing

During type testing, PD measurement is performed as part of the electrical verification suite, alongside withstand voltage and tan delta tests. This validates the cable system design under controlled laboratory conditions.^[362871cd3841da0e:narrative]

### Role in Routine Testing

Every manufactured cable length must undergo PD measurement as a routine test. The acceptance criterion is a partial discharge level **below 5 pC** under the specified test voltage.^[362871cd3841da0e:narrative]

### Relationship to Other Testing

PD measurement is distinct from after‑installation tests such as DC/VLF withstand testing or sheath integrity checks, which are performed on‑site to verify the installed cable system. However, PD measurement can also be applied on‑site for condition assessment, though that is not covered by the routine test requirement.^[362871cd3841da0e:narrative]

### See also

* [[cable.testing.type_testing]]
* [[cable.testing.routine_testing]]
* [[cable.testing.after_installation_testing]]
* [[cable.testing.high_voltage_withstand_test]]

