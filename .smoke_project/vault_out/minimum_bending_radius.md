---
type: concept
level: 0
entity_id: minimum_bending_radius
title: minimum_bending_radius
domain: default
confidence: 0.5
schema_version: '1.0'
description: The smallest radius a cable can be bent without damage during installation
  or operation, typically 20× the cable outer diameter for HV XLPE cables.
tags:
- high voltage cable
- mechanical stress
- installation
sources:
- source_id: 4548a58ab1ab402c
  source_path: C:\Users\bottacl001\GitHub\klustra\.smoke_project\corpus\installation_guide.txt
created_at: '2026-07-21T10:10:27.339057+00:00'
updated_at: '2026-07-21T10:10:27.339057+00:00'
---

## Overview

The minimum bending radius (MBR) is the smallest radius a cable can be bent around without damaging its internal structure, especially the [[xlpe_insulation_material]], [[semi_conductive_screen]], [[metallic_sheath]], and [[outer_protective_jacket]]. Exceeding this limit during installation or operation can lead to permanent deformation, cracking, or electrical failure.

## Typical Value

During installation, the recommended minimum bending radius is **20 times the cable outer diameter (20× OD)**.^[4548a58ab1ab402c] This value applies to [[cross_linked_polyethylene_insulation]] cables commonly used in [[high_voltage_cable_systems]]. For specific cable designs (e.g., submarine or offshore wind farm arrays), the manufacturer's datasheet should be consulted, as the ratio may differ.

## Practical Consequences

Applying excessive bending can:
- Crack the [[semi_conductive_screen]], leading to partial discharges.
- Wrinkle or rupture the [[metallic_sheath]], compromising moisture barrier integrity.
- Damage the insulation, reducing [[dielectric_strength]] and accelerating [[electrical_treeing]] or [[water_treeing]].

## Relationship to Other Installation Parameters

The MBR is interdependent with:
- [[maximum_pulling_tension]] — tension and bending together increase mechanical stress on the conductor.
- [[installation_temperature]] — cold cables (below 0 °C) become stiffer; the MBR may need to be larger if installation temperature is below the manufacturer´s minimum (typically >0 °C^[4548a58ab1ab402c]).
- [[cable_lubricant]] — proper lubrication reduces friction, allowing the cable to follow the bend more smoothly.

## Application in Common Installation Methods
| Method | MBR relevance |
|--------|---------------|
| [[duct_installation]] | Bends inside ducts are constrained by the duct curvature; ensure duct radius ≥ MBR. Steady pulling at 5–10 m/min with [[cable_winch_tension_monitoring]] helps avoid sharp bends.^[4548a58ab1ab402c] |
| [[direct_burial]] | Trenches must be dug without sharp corners; sand bedding (100 mm below and above) cushions the cable.^[4548a58ab1ab402c] |
| [[jointing]] | In [[joint_bay_dimensions]] (min 3 m × 1.5 m^[4548a58ab1ab402c]), the cable tail must be formed with a radius ≥ MBR before attaching [[prefabricated_joints]]. |

## Testing After Installation
After installation, the cable must pass [[after_installation_testing]] including a [[high_voltage_withstand_test]] and [[sheath_integrity_test]] to confirm no damage from bending occurred.^[4548a58ab1ab402c]

## Standards
- [[iec_61936_1]] provides general guidance on installation radii.
- [[iec_62067]] covers type testing and routine testing for HV cables, including bending tests.

## References

- Cable Installation Guide, 2024.^[4548a58ab1ab402c]
