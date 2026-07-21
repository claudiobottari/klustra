---
type: concept
level: 0
entity_id: sheath_integrity_test
title: sheath_integrity_test
domain: default
confidence: 0.5
schema_version: '1.0'
description: A sheath integrity test is a non-destructive electrical test performed
  on high-voltage cable systems to verify the continuity and insulation condition
  of the metallic sheath and outer protective jacket after installation. It is a standard
  commissioning procedure defined in IEC 62067 and related standards, typically conducted
  at 10 kV DC for 1 minute to detect sheath damage, punctures, or moisture ingress
  that could compromise cable longevity.
tags:
- testing
- commissioning
- high-voltage cables
- sheath integrity
- IEC 62067
sources:
- source_id: dc426de07f1561d5
  source_path: C:\Users\bottacl001\GitHub\klustra\.smoke_project\corpus\testing_procedures.md
created_at: '2026-07-21T10:10:27.339279+00:00'
updated_at: '2026-07-21T10:10:27.339279+00:00'
---

## Overview

The sheath integrity test is an after-installation test applied to [[high_voltage_cable_systems]], particularly those with [[cross_linked_polyethylene_insulation]] and a [[metallic_sheath]]. Its purpose is to confirm that the outer protective jacket and metallic sheath are continuous and free from defects that could allow moisture or contaminants to reach the [[cable_core]] or [[semi_conductive_screen]]. The test is part of the commissioning suite defined in [[iec_62067]] and is performed on-site after cable laying, jointing, and termination are complete.^[dc426de07f1561d5:testing_procedures.md]

## Procedure

During the sheath integrity test, a DC voltage of 10 kV is applied between the metallic sheath and ground for a duration of 1 minute. The leakage current is monitored; a low and stable current indicates a healthy sheath, while a rising or erratic current suggests a defect such as a puncture, cut, or moisture path. The test is typically conducted using a portable DC high-voltage tester with current measurement capability.^[dc426de07f1561d5:testing_procedures.md]

## Context in Testing Regime

The sheath integrity test is one of several after-installation tests specified in [[iec_62067]] and related standards. It complements other commissioning tests such as:
- [[dc_vlf_withstand_testing]] (DC or VLF withstand testing)
- [[joint_resistance_measurement]]
- [[high_voltage_withstand_test]]
- [[partial_discharge_measurement]]

These tests are performed after cable installation, including [[duct_installation]], [[direct_burial]], or [[submarine_crossings]], and after [[jointing]] with [[prefabricated_joints]] or [[nkt_cold_shrink_joints]]. The sheath integrity test is particularly important for cables installed in harsh environments such as [[underground_urban_networks]], [[offshore_wind_farms]], or areas with high groundwater, where sheath damage could lead to rapid degradation.^[dc426de07f1561d5:testing_procedures.md]

## Safety Considerations

Before performing the sheath integrity test, personnel must follow [[cable_isolation_and_earthing]] procedures, including [[voltage_absence_verification]] and application of [[safety_locks_and_tags]]. The test area should be designated as a [[safe_work_zone_with_barriers]] to prevent accidental contact. If a fault is detected, the [[cable_fault_emergency_procedure]] should be followed, and the affected section should be isolated within a [[fault_exclusion_zone]].^[dc426de07f1561d5:testing_procedures.md]

## Interpretation and Acceptance Criteria

A passing sheath integrity test shows leakage current below a threshold defined by the cable manufacturer or project specification (typically in the microampere range). If leakage exceeds the limit, the sheath is considered compromised, and the cable must be repaired or replaced. The test is repeated after repair to confirm integrity.^[dc426de07f1561d5:testing_procedures.md]

## Storia e revisioni

No conflicting claims were identified in the source material. The test procedure and voltage level (10 kV DC for 1 minute) are consistent with industry practice for medium- and high-voltage cables.^[dc426de07f1561d5:testing_procedures.md]
