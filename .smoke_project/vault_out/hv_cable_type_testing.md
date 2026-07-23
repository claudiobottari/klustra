---
type: concept
level: 0
entity_id: hv_cable_type_testing
title: hv_cable_type_testing
domain: default
confidence: 0.5
schema_version: '1.0'
description: Qualification tests per IEC 62067 that validate the electrical, mechanical,
  and thermal performance of a high-voltage cable system design.
tags:
- testing
- high-voltage cables
- IEC 62067
- type testing
sources:
- source_id: 362871cd3841da0e
  source_path: C:\Users\botta\github\klustra\.smoke_project\corpus\testing_procedures.md
created_at: '2026-07-22T05:45:56.459534+00:00'
updated_at: '2026-07-22T05:45:56.459534+00:00'
---

## hv_cable_type_testing

**hv_cable_type_testing** refers to the suite of qualification tests performed on a [[high_voltage_cable_systems]] design to validate its electrical, mechanical, and thermal performance in accordance with [[iec_62067]] standards. These tests are distinct from [[hv_cable_routine_testing]] (applied to every manufactured length) and [[hv_cable_after_installation_testing]] (commissioning tests).

### Standards

All type tests are conducted per the requirements of [[iec_62067]], which defines the test procedures and acceptance criteria for cable systems rated above 30 kV up to 500 kV.^[362871cd3841da0e:narrative]

### Test categories

Type testing covers three main categories:^[362871cd3841da0e:narrative]

- **Electrical tests**: withstand voltage, [[partial_discharge_measurement]], and tan delta (dielectric loss) measurement.
- **Mechanical tests**: bending test (verifying minimum bending radius) and tensile test (simulating installation stresses).
- **Thermal tests**: load cycling at rated current and at emergency temperature to verify thermal performance.

### Relationship to other testing phases

Successful completion of type testing is a prerequisite for the cable system design to be included in an [[approved_supplier_list_hv_cable_components]]. Subsequent routine tests on production lengths and after-installation tests (e.g., sheath integrity test, joint resistance measurement) ensure consistency with the type-tested design.^[362871cd3841da0e:narrative]
