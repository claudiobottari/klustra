---
type: concept
level: 0
entity_id: metallic_sheath
title: Metallic sheath
domain: default
confidence: 0.5
schema_version: '1.0'
description: A metallic layer in high-voltage cables that provides water blocking,
  mechanical protection, and electrical screening.
tags:
- cable components
- high-voltage cables
- power transmission
sources:
- source_id: acd06c178fe5b8e6
  source_path: C:\Users\bottacl001\GitHub\klustra\.smoke_project\corpus\cable_intro.md
created_at: '2026-07-21T10:10:27.339027+00:00'
updated_at: '2026-07-21T10:10:27.339027+00:00'
---

## Overview

The **metallic sheath** is a component of high-voltage (HV) cable systems, positioned between the XLPE insulation layer and the outer protective jacket. Its primary function is to provide a continuous water-blocking barrier, preventing moisture ingress that could degrade the insulation and lead to premature failure.^[acd06c178fe5b8e6:1]

## Construction and materials

Metallic sheaths are typically made from lead, aluminium, or copper, and may be applied as a corrugated or smooth tube, or as a laminated tape (e.g., an aluminium–polyethylene laminate).^[acd06c178fe5b8e6:1] The choice of material depends on mechanical strength, corrosion resistance, and compatibility with the cable’s operating environment. In modern XLPE-insulated cables, the sheath is often bonded to the semi-conductive screen to ensure electrical continuity and facilitate fault current return.^[acd06c178fe5b8e6:1]

## Functions

- **Water blocking**: Prevents radial water ingress into the cable core, protecting the XLPE insulation from water treeing.^[acd06c178fe5b8e6:1]
- **Mechanical protection**: Provides resistance against crushing, impact, and rodent damage during installation and service.^[acd06c178fe5b8e6:1]
- **Electrical screening**: Acts as an earthed screen that confines the electric field within the cable and provides a path for capacitive charging currents and fault currents.^[acd06c178fe5b8e6:1]

## Installation considerations

During cable pulling, the metallic sheath must not be subjected to stresses exceeding the manufacturer’s specified [[maximum_pulling_tension]] or [[minimum_bending_radius]], as excessive deformation can compromise its water-tightness.^[acd06c178fe5b8e6:1] After installation, a [[sheath_integrity_test]] (e.g., DC or VLF withstand test) is performed to verify that the sheath has not been damaged.^[acd06c178fe5b8e6:1]

## Standards and testing

Metallic sheaths are covered by [[iec_62067]] for type testing and routine testing of HV cables. The sheath integrity is verified through [[after_installation_testing]] procedures, including partial discharge measurement and high-voltage withstand tests.^[acd06c178fe5b8e6:1]

## See also

- [[cable_core]]
- [[semi_conductive_screen]]
- [[cross_linked_polyethylene_insulation]]
- [[outer_protective_jacket]]
- [[water_treeing]]
- [[electrical_treeing]]
