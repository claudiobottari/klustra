---
type: concept
level: 0
entity_id: partial_discharge_measurement
title: Partial Discharge Measurement
domain: default
confidence: 0.5
schema_version: '1.0'
description: A diagnostic test that detects localized electrical discharges within
  insulation systems, used to assess insulation integrity in high-voltage cables and
  accessories.
tags:
- testing
- diagnostics
- high-voltage
- insulation
sources:
- source_id: dc426de07f1561d5
  source_path: C:\Users\bottacl001\GitHub\klustra\.smoke_project\corpus\testing_procedures.md
created_at: '2026-07-21T10:10:27.339262+00:00'
updated_at: '2026-07-21T10:10:27.339262+00:00'
---

## Overview

Partial discharge (PD) measurement is a non-destructive test that identifies localized electrical discharges occurring within insulation systems under high voltage stress. It is a critical quality assurance tool for [[high_voltage_cable_systems]], particularly those with [[cross_linked_polyethylene_insulation]], as PD activity can indicate defects that may lead to insulation failure over time.

## Standards and Thresholds

PD measurement is specified in international standards for cable testing. For routine testing of manufactured cable lengths, the threshold is set at less than 5 pC (picocoulombs) per IEC 62067.^[dc426de07f1561d5:1] This threshold applies to the cable core and its insulation system, including the [[semi_conductive_screen]] and [[metallic_sheath]].

## Testing Procedures

### Type Testing

During type testing per [[iec_62067]], PD measurement is performed alongside other electrical tests such as withstand voltage and tan delta.^[dc426de07f1561d5:1] This validates the cable system design for long-term reliability.

### Routine Testing

Every manufactured cable length undergoes PD measurement as part of routine testing. The test is conducted after the high-voltage withstand test at 2.5 U0 for 30 minutes.^[dc426de07f1561d5:1] The PD level must remain below 5 pC to pass.

### After-Installation Testing

On-site commissioning tests do not typically include PD measurement; instead, they rely on [[dc_vlf_withstand_testing]], [[sheath_integrity_test]], and [[joint_resistance_measurement]].^[dc426de07f1561d5:1] However, PD measurement may be used for diagnostic purposes in existing installations.

## Applications

PD measurement is essential for:
- [[underground_urban_networks]] where cable reliability is critical
- [[submarine_crossings]] and [[offshore_wind_farms]] where access for repairs is limited
- [[prefabricated_joints]] and terminations, where PD can indicate installation defects

## Related Tests

- [[high_voltage_withstand_test]]
- [[conductor_resistance_check]]
- [[dielectric_loss]] measurement (tan delta)

## Storia e revisioni

No conflicting claims were identified across sources. All information is derived from a single source (dc426de07f1561d5) describing cable testing standards per IEC 62067.
