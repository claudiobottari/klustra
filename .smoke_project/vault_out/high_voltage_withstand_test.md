---
type: concept
level: 0
entity_id: high_voltage_withstand_test
title: high_voltage_withstand_test
domain: default
confidence: 0.5
schema_version: '1.0'
description: A high-voltage withstand test is a procedure that applies a specified
  overvoltage to a cable system to verify insulation integrity, performed during type
  testing, routine manufacturing, and after installation.
tags:
- testing
- high voltage
- cable
- insulation
- commissioning
sources:
- source_id: dc426de07f1561d5
  source_path: C:\Users\bottacl001\GitHub\klustra\.smoke_project\corpus\testing_procedures.md
created_at: '2026-07-21T10:10:27.339256+00:00'
updated_at: '2026-07-21T10:10:27.339256+00:00'
---

## Overview

The **high voltage withstand test** is a critical diagnostic procedure used to verify the insulation integrity of [[high_voltage_cable_systems]] after manufacturing and installation. It ensures that the cable system can withstand specified overvoltages without breakdown, thereby confirming the quality of [[cross_linked_polyethylene_insulation]] and other components.

## Types of Withstand Testing

### Type Testing
Per [[iec_62067]], type tests validate the cable system design. The electrical portion includes a withstand voltage test, [[partial_discharge_measurement]], and tan delta measurement. Mechanical and thermal tests (e.g., bending, tensile, load cycling) are also performed.^[dc426de07f1561d5:1-4]

### Routine Testing
Every manufactured cable length undergoes a high-voltage withstand test at **2.5 U0** for **30 minutes**. This is followed by [[partial_discharge_measurement]] (threshold < 5 pC) and [[conductor_resistance_check]].^[dc426de07f1561d5:6-9]

### After-Installation Testing
On-site commissioning tests include:
- **DC or VLF withstand testing** (very low frequency alternative to DC)
- **Sheath integrity test** at 10 kV DC for 1 minute
- **Joint resistance measurement**^[dc426de07f1561d5:11-14]

## Purpose and Importance

The test verifies that the insulation system ([[xlpe_insulation_material]], [[semi_conductive_screen]], [[metallic_sheath]], [[outer_protective_jacket]]) can endure transient overvoltages and operating stresses. It is essential for [[underground_urban_networks]], [[submarine_crossings]], and [[offshore_wind_farms]] where cable reliability is paramount.

## Related Standards and Procedures

- [[iec_62067]]: Power cables with extruded insulation and their accessories for rated voltages above 150 kV (Um = 170 kV) up to 500 kV (Um = 550 kV)
- [[iec_61936_1]]: Power installations exceeding 1 kV AC
- [[local_electrical_safety_regulations]] and [[company_specific_safety_procedures]] govern safe execution, including [[cable_isolation_and_earthing]], [[voltage_absence_verification]], [[safety_locks_and_tags]], and [[safe_work_zone_with_barriers]].

## Storia e revisioni

No conflicting claims were identified across sources. All statements are consistent with the provided testing procedures document.

## References

- dc426de07f1561d5: Cable Testing Standards (type, routine, after-installation testing)


