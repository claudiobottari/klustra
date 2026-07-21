---
type: concept
level: 0
entity_id: cable.testing.joint_resistance_measurement
title: cable.testing.joint_resistance_measurement
domain: default
confidence: 0.5
schema_version: '1.0'
description: An on-site commissioning test that measures the DC resistance of cable
  joints to verify low and stable contact resistance after installation.
tags:
- cable testing
- after-installation testing
- joint integrity
- commissioning
sources:
- source_id: 362871cd3841da0e
  source_path: C:\Users\botta\github\klustra\.smoke_project\corpus\testing_procedures.md
created_at: '2026-07-21T23:18:00.781219+00:00'
updated_at: '2026-07-21T23:18:00.781219+00:00'
---

## Joint Resistance Measurement

Joint resistance measurement is an on-site commissioning test performed after cable installation. It is part of the [[cable.testing.after_installation_testing]] suite for [[high-voltage.cable.systems]] and is intended to verify that the electrical resistance of each cable joint is sufficiently low and stable.^[362871cd3841da0e:testing_procedures.md]

While the measurement technique is not specified in the source, the test is typically conducted with a low-resistance ohmmeter (micro-ohmmeter) to detect poor connections, inadequate crimping, or contamination at the joint interface. The acceptance criteria are usually defined by the applicable standard, such as [[iec.62067]] or the manufacturer’s specification, and often require that the joint resistance does not exceed the resistance of an equivalent-length continuous conductor.

Joint resistance measurement is one of several after-installation tests that also include [[cable.testing.dc_vlf_withstand_testing]] and [[cable.testing.sheath_integrity_test]].^[362871cd3841da0e:testing_procedures.md]
