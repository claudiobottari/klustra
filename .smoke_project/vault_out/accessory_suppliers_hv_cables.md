---
type: concept
level: 0
entity_id: accessory_suppliers_hv_cables
title: Accessory suppliers for HV cables
domain: default
confidence: 0.5
schema_version: '1.0'
description: List of approved suppliers for high-voltage cable accessories, including
  Prysmian and NKT, with testing, installation, and safety context.
tags:
- HV cables
- accessories
- suppliers
- joints
- terminations
- Prysmian
- NKT
- IEC 62067
sources:
- source_id: 66fee6e56f742178
  source_path: C:\Users\botta\github\klustra\.smoke_project\corpus\supplier_list.txt
created_at: '2026-07-22T05:45:56.459442+00:00'
updated_at: '2026-07-22T05:45:56.459442+00:00'
---

## Overview

**Accessory suppliers for high-voltage (HV) cables** provide critical components such as joints, terminations, and connectors that ensure the reliability and safety of [[high_voltage_cable_systems]]. These accessories must meet stringent type-testing and performance standards, particularly [[iec_62067]] for extruded cables and their accessories. The approved supplier list for HV cable accessories is typically maintained by utilities or project owners as part of an [[approved_supplier_list_hv_cable_components]].

## Approved suppliers

Two major suppliers are commonly approved for HV cable accessories:

- **Prysmian** – supplies pre-moulded joints and terminations that are IEC type-tested. These components are designed for use with [[xlpe_insulation]] cables and are suitable for a wide range of HV applications.^[66fee6e56f742178:0]
- **NKT** – provides cold-shrink joints covering the voltage range 66–170 kV. Cold-shrink technology simplifies installation and reduces the risk of installation errors compared to heat-shrink alternatives.^[66fee6e56f742178:0]

Both suppliers’ products are intended to be used in conjunction with other approved components such as [[conductor_suppliers_hv_cables]] (e.g., Norsk Hydro, Aurubis) and [[insulation_compound_suppliers_hv_cables]] (e.g., Borealis, Dow).

## Testing and quality requirements

Accessories must undergo rigorous testing to ensure compatibility with the cable system. Key tests include:
- [[hv_cable_type_testing]] – verifies design and performance under extreme conditions.
- [[hv_cable_routine_testing]] – performed on every production unit.
- [[hv_cable_after_installation_testing]] – includes [[partial_discharge_measurement]], [[high_voltage_withstand_test]], [[sheath_integrity_test]], and [[joint_resistance_measurement]].

These tests are mandated by standards such as [[iec_62067]] and are critical for long-term reliability.

## Installation considerations

Proper installation of accessories is essential. Key parameters include:
- [[hv_cable_installation_bending_radius]] – must not be exceeded to avoid damaging the accessory or cable.
- [[hv_cable_installation_pulling_tension]] – controlled to prevent mechanical stress.
- [[hv_cable_installation_temperature_conditions]] – especially important for cold-shrink and pre-moulded components.

Installation methods such as [[hv_cable_duct_installation_process]] and [[hv_cable_direct_burial_installation]] impose specific requirements on accessory design and handling.

## Safety and regulatory framework

All work on HV cable accessories must comply with [[hv_cable_safety_standards]] and the [[hv_cable_regulatory_framework]]. Personnel must follow [[hv_cable_safe_working_practices]] and be prepared for [[hv_cable_emergency_procedures]]. Jointing operations, in particular, require adherence to [[hv_cable_jointing_requirements]] to maintain system integrity.

## See also
- [[conductor_suppliers_hv_cables]]
- [[insulation_compound_suppliers_hv_cables]]
- [[sheathing_suppliers_hv_cables]]
- [[xlpe_insulation_properties]]
- [[xlpe_manufacturing_process]]
- [[xlpe_degradation_mechanisms]]
- [[xlpe_compound_quality]]

## References

- Approved Supplier List – HV Cable Components (source document)^[66fee6e56f742178:0]
