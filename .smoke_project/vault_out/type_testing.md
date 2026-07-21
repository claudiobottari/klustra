---
type: concept
level: 0
entity_id: type_testing
title: type_testing
domain: default
confidence: 0.5
schema_version: '1.0'
description: Formal qualification of cable system design per IEC 62067, covering electrical,
  mechanical, and thermal tests.
tags:
- testing
- standards
- cables
- type_testing
sources:
- source_id: dc426de07f1561d5
  source_path: C:\Users\bottacl001\GitHub\klustra\.smoke_project\corpus\testing_procedures.md
created_at: '2026-07-21T10:10:27.339240+00:00'
updated_at: '2026-07-21T10:10:27.339240+00:00'
---

# type_testing

**Type testing** is a formal qualification process defined by [[iec_62067]] that validates the design and performance of [[high_voltage_cable_systems]] before they are approved for commercial use. It is distinct from [[routine_testing]], which is performed on every manufactured cable length, and from [[after_installation_testing]], which verifies the installed system.

The primary purpose of type testing is to confirm that the cable system — including the [[cable_core]], [[semi_conductive_screen]], [[metallic_sheath]], [[outer_protective_jacket]], and any [[prefabricated_joints]] or terminations — can withstand the electrical, mechanical, and thermal stresses expected over its [[design_lifetime]].

## Tests performed

Type tests per IEC 62067 encompass three categories^[dc426de07f1561d5]:
- **Electrical tests**: high-voltage withstand test, [[partial_discharge_measurement]], and tan delta measurement.
- **Mechanical tests**: bending test (verified at the [[minimum_bending_radius]]), tensile test.
- **Thermal tests**: load cycling at rated and emergency [[operating_temperature]].

These tests are applied to a complete cable system (cable plus accessories) to demonstrate that all components work together reliably.

## Relationship to other testing stages

Type testing is performed once for a given design. After type approval, each production length is subject to routine testing — including a high-voltage withstand test at 2.5 U₀ for 30 min, partial discharge measurement (threshold < 5 pC), and [[conductor_resistance_check]]^[dc426de07f1561d5]. On-site commissioning then verifies the installed system with DC or VLF withstand testing, [[sheath_integrity_test]] (e.g., 10 kV DC for 1 min), and [[joint_resistance_measurement]]^[dc426de07f1561d5].

## Applicable cables and materials

Type testing applies to [[cross_linked_polyethylene_insulation]] (XLPE) cables as widely used in [[underground_urban_networks]], [[submarine_crossings]], and [[offshore_wind_farms]]. Insulation compounds such as [[borealis_visico_le4253]] or [[dow_chemical_hfda_4202_ec]] are evaluated during type testing for [[dielectric_strength]] and resistance to [[water_treeing]] and [[electrical_treeing]].

## See also

- [[routine_testing]]
- [[after_installation_testing]]
- [[iec_62067]]
- [[design_lifetime]]
