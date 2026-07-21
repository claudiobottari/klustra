---
type: concept
level: 0
entity_id: voltage_absence_verification
title: Voltage Absence Verification
domain: default
confidence: 0.5
schema_version: '1.0'
description: Voltage absence verification is a critical safety procedure performed
  before any work on high-voltage (HV) cable systems to confirm that the cable is
  de-energized and safe to handle. It is part of a broader set of safe working practices
  mandated by international and local regulations.
tags:
- safety
- high-voltage
- cable
- verification
- procedure
sources:
- source_id: b359cf61b264db52
  source_path: C:\Users\bottacl001\GitHub\klustra\.smoke_project\corpus\safety_standards.md
created_at: '2026-07-21T10:10:27.339157+00:00'
updated_at: '2026-07-21T10:10:27.339157+00:00'
---

## Overview

Voltage absence verification is a mandatory step in the safe working procedure for high-voltage (HV) cable systems. It ensures that a cable is de-energized before personnel begin any work, such as jointing, termination, or repair. The procedure is part of a sequence of actions that include isolation, earthing, locking, and tagging.

## Regulatory Framework

All HV cable work must comply with:
- [[iec_61936_1]] (Power installations exceeding 1 kV)
- [[local_electrical_safety_regulations]]
- [[company_specific_safety_procedures]]

These standards require that voltage absence be verified using approved indicators before any work commences.^[b359cf61b264db52:1-2]

## Procedure

Before any work on cable systems, the following steps must be taken:
1. [[cable_isolation_and_earthing]] at both ends
2. **Verify absence of voltage** using approved indicators
3. Apply [[safety_locks_and_tags]]
4. Establish [[safe_work_zone_with_barriers]]

Voltage absence verification is the second step, performed after isolation and earthing, and before locking and tagging.^[b359cf61b264db52:2]

## Approved Indicators

Only approved voltage indicators, such as those meeting relevant safety standards, must be used. The specific type of indicator (e.g., contact or non-contact) depends on the cable system and local regulations. The verification must be performed at the point of work, typically at the cable ends or at accessible joints.

## Relationship to Other Safety Measures

Voltage absence verification is closely linked to:
- [[cable_isolation_and_earthing]]: The cable must be isolated and earthed before verification.
- [[safety_locks_and_tags]]: After verification, locks and tags are applied to prevent re-energization.
- [[safe_work_zone_with_barriers]]: A safe work zone is established after verification.

## Emergency Context

In case of a cable fault during live operation, voltage absence verification is not performed until the fault is isolated and the cable is de-energized. Emergency procedures include maintaining a [[fault_exclusion_zone]] of 3 m around the suspected fault location, not attempting to re-energize without inspection, and reporting immediately to the control centre.^[b359cf61b264db52:3]

## Storia e revisioni

No conflicting claims were identified in the source. The procedure described is consistent with standard industry practice for HV cable work.

## References

- IEC 61936-1: Power installations exceeding 1 kV
- Local electrical safety regulations
- Company-specific safety procedures

All claims in this page are derived from the source document: Safety Standards for HV Cable Work.^[b359cf61b264db52:1-3]
