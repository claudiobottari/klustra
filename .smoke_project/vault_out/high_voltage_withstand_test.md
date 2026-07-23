---
type: concept
level: 0
entity_id: high_voltage_withstand_test
title: High voltage withstand test
domain: default
confidence: 0.5
schema_version: '1.0'
description: Procedure that applies a voltage above the rated level to a cable system
  to confirm insulation integrity.
tags:
- testing
- insulation
- high voltage
sources:
- source_id: 362871cd3841da0e
  source_path: C:\Users\botta\github\klustra\.smoke_project\corpus\testing_procedures.md
created_at: '2026-07-22T05:45:56.459571+00:00'
updated_at: '2026-07-22T05:45:56.459571+00:00'
---

The **high voltage withstand test** is a diagnostic procedure that verifies the insulation integrity of [[high_voltage_cable_systems]] by applying a voltage higher than the rated operating voltage for a specified duration. It is a mandatory test in both [[hv_cable_routine_testing]] and [[hv_cable_after_installation_testing]].

## Routine testing
During routine factory testing, every manufactured cable length must undergo a high-voltage withstand test at **2.5 U₀** for **30 minutes** (where U₀ is the rated phase-to-earth voltage).^[362871cd3841da0e] This test is typically performed immediately after [[partial_discharge_measurement]] to confirm that the insulation can endure the specified overvoltage without breakdown.

## After‑installation testing
On-site commissioning tests may employ **DC or VLF (very low frequency) withstand testing** to verify that the cable and its accessories have not been damaged during transport, handling, or installation.^[362871cd3841da0e] The exact voltage level and duration depend on the cable type and applicable standards, such as [[iec_62067]].

## Relationship to other tests
The high voltage withstand test is distinct from the [[sheath_integrity_test]] (which applies 10 kV DC for 1 minute to the metallic sheath) and from [[joint_resistance_measurement]], but it is often performed in sequence with these tests as part of a comprehensive commissioning program.^[362871cd3841da0e]

## Storia e revisioni
No conflicting claims were provided; the single source (362871cd3841da0e) is consistent in its description of the test parameters.
