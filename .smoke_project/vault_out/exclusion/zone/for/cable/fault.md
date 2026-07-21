---
type: concept
level: 0
entity_id: exclusion.zone.for.cable.fault
title: exclusion.zone.for.cable.fault
domain: default
confidence: 0.5
schema_version: '1.0'
description: Safety perimeter around a suspected HV cable fault location, typically
  3 m, to protect personnel from re-energization risks.
tags:
- safety
- high voltage
- cable fault
- exclusion zone
- emergency procedure
sources:
- source_id: 46d617e505500254
  source_path: C:\Users\botta\github\klustra\.smoke_project\corpus\safety_standards.md
created_at: '2026-07-21T23:18:00.781058+00:00'
updated_at: '2026-07-21T23:18:00.781058+00:00'
---

## Exclusion Zone for Cable Fault

An **exclusion zone for cable fault** is a mandatory safety perimeter established around a suspected fault location on a high-voltage cable during live operation. Its purpose is to protect personnel from the risk of electric shock, arc flash, or explosion that may occur if the fault re-energizes or the cable behaves unpredictably.

### Establishment and Dimensions

When a cable fault is detected during live operation, an exclusion zone of **3 metres** must be maintained around the suspected fault location.^[46d617e505500254:Emergency Procedures] This distance is specified in [[iec.61936-1]] and is reinforced by [[local.electrical.safety.regulations]] and [[company.specific.safety.procedures]].

### Prohibited Actions

Within the exclusion zone:

- No person may enter or remain without explicit authorization.
- No attempt shall be made to [[fault.re-energization.prohibition|re-energize the cable]] until a full inspection has been completed.^[46d617e505500254:Emergency Procedures]

### Reporting and Coordination

Upon establishing the exclusion zone, the incident must be reported immediately to the [[control.centre.reporting|control centre]].^[46d617e505500254:Emergency Procedures] The control centre coordinates further actions, including isolation, earthing, and verification of voltage absence.

### Relationship to General Safe Work Practices

The exclusion zone is part of a broader set of safe working practices for HV cable work. Before any work on cable systems, operators must:

1. [[cable.isolation.and.earthing|Isolate and earth the cable at both ends]]
2. [[voltage.absence.verification|Verify absence of voltage]] using approved indicators
3. Apply [[safety.locks.and.tags]]
4. Establish a [[safe.work.zone.with.barriers]]^[46d617e505500254:Safe Working Practices]

These preliminary steps prevent the need for emergency exclusion zones, but when a fault occurs unexpectedly, the emergency procedure (including the 3 m exclusion zone) overrides normal work practices.

## Storia e revisioni

No conflicting claims were found in the available sources. The single source (46d617e505500254) consistently specifies a 3 m exclusion zone.

---

**confidence:** 0.9
