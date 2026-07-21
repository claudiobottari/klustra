---
type: concept
level: 0
entity_id: conductor_resistance_check
title: conductor_resistance_check
domain: default
confidence: 0.5
schema_version: '1.0'
description: A routine test to measure the DC resistance of a cable conductor to verify
  compliance with design specifications.
tags:
- testing
- cable
- conductor
- quality control
- IEC 62067
sources:
- source_id: dc426de07f1561d5
  source_path: C:\Users\bottacl001\GitHub\klustra\.smoke_project\corpus\testing_procedures.md
created_at: '2026-07-21T10:10:27.339267+00:00'
updated_at: '2026-07-21T10:10:27.339267+00:00'
---

## Conductor Resistance Check

The **conductor resistance check** is a routine test performed on every manufactured cable length to verify that the DC resistance of the conductor meets the specified value. It is part of the quality assurance process for [[high_voltage_cable_systems]] and is typically conducted in accordance with [[iec_62067]].^[dc426de07f1561d5:0]

### Purpose

The test ensures that the conductor's electrical resistance is within acceptable limits, which is critical for minimizing power losses and ensuring proper current-carrying capacity. Deviations from the specified resistance can indicate manufacturing defects such as incorrect conductor cross-section, material impurities, or poor stranding.

### Procedure

During routine testing, the conductor resistance is measured using a low-resistance ohmmeter (e.g., a Kelvin bridge) at a known temperature. The measured value is then corrected to a standard reference temperature (typically 20 °C) using the temperature coefficient of resistance for the conductor material (copper or aluminium). The corrected resistance must not exceed the maximum value specified in the cable design.

### Relation to Other Tests

The conductor resistance check is one of several routine tests performed on each cable length. Other routine tests include:
- High-voltage withstand test at 2.5 U0 for 30 minutes^[dc426de07f1561d5:0]
- Partial discharge measurement (threshold < 5 pC)^[dc426de07f1561d5:0]

After installation, additional tests such as [[joint_resistance_measurement]] are performed to verify the integrity of field-installed joints.

### Standards

The test is specified in [[iec_62067]] for power cable systems with rated voltages above 150 kV. It is also referenced in other international and national standards for cable testing.

### See also
- [[routine_testing]]
- [[type_testing]]
- [[after_installation_testing]]
- [[high_voltage_withstand_test]]
- [[partial_discharge_measurement]]
- [[joint_resistance_measurement]]
