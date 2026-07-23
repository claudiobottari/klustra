---
type: concept
level: 0
entity_id: joint_resistance_measurement
title: Joint Resistance Measurement
domain: default
confidence: 0.5
schema_version: '1.0'
description: Joint resistance measurement is an after-installation test for high-voltage
  cable systems that verifies the electrical integrity of cable joints by measuring
  the DC resistance across the joint and comparing it to an equivalent length of conductor.
tags:
- testing
- after-installation testing
- cable joints
- commissioning
- high voltage cable systems
sources:
- source_id: 362871cd3841da0e
  source_path: C:\Users\botta\github\klustra\.smoke_project\corpus\testing_procedures.md
created_at: '2026-07-22T05:45:56.459590+00:00'
updated_at: '2026-07-22T05:45:56.459590+00:00'
---

## Overview

**Joint resistance measurement** is a commissioning test performed on [[high_voltage_cable_systems]] after installation to verify the quality and electrical integrity of cable joints. It is one of the standard after-installation tests, alongside DC or VLF withstand testing and [[sheath_integrity_test]].^[362871cd3841da0e:section:Cable Testing Standards]

## Purpose

The test ensures that the resistance of a completed joint does not exceed the resistance of an equivalent length of uninterrupted conductor. An elevated joint resistance indicates poor connection, inadequate crimping, or contamination, which could lead to overheating and premature failure under load.

## Procedure

Joint resistance measurement is typically performed using a low-resistance ohmmeter (micro-ohmmeter) with a four-wire (Kelvin) connection to eliminate lead and contact resistance. The measured resistance across the joint is compared to the resistance of a conductor segment of the same length and cross-section. The test is conducted at ambient temperature, and results may be corrected for temperature differences.

## Acceptance Criteria

While specific limits depend on the cable system design and applicable standards (e.g., [[iec_62067]]), the general requirement is that the joint resistance should not exceed the resistance of an equivalent length of conductor. Any significant deviation warrants investigation and possible rework of the joint.

## Relation to Other Tests

Joint resistance measurement is part of the after-installation testing suite for [[high_voltage_cable_systems]]. It complements [[high_voltage_withstand_test]] and [[partial_discharge_measurement]] by focusing specifically on the DC conductive path, whereas those tests assess insulation integrity and dielectric performance.
