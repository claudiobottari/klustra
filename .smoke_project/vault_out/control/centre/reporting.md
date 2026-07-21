---
type: concept
level: 0
entity_id: control.centre.reporting
title: control.centre.reporting
domain: default
confidence: 0.5
schema_version: '1.0'
description: A mandatory safety procedure requiring immediate notification of the
  control centre when a cable fault occurs during live HV cable operations.
tags:
- safety
- emergency
- control centre
- reporting
- high-voltage cable
- fault management
sources:
- source_id: 46d617e505500254
  source_path: C:\Users\botta\github\klustra\.smoke_project\corpus\safety_standards.md
created_at: '2026-07-21T23:18:00.781072+00:00'
updated_at: '2026-07-21T23:18:00.781072+00:00'
---

In the context of [[high-voltage.cable.systems]] work, **control.centre.reporting** is a mandatory safety procedure under emergency protocols. The requirement is defined in relevant safety standards, such as [[iec.61936-1]], [[local.electrical.safety.regulations]], and [[company.specific.safety.procedures]].

When a cable fault occurs during live operation, the following actions must be taken before any further work:

1. Maintain an [[exclusion.zone.for.cable.fault]] of 3 m around the suspected fault location.^[46d617e505500254:Emergency Procedures]
2. Do not attempt to re-energize the circuit without inspection (see [[fault.re-energization.prohibition]]).^[46d617e505500254:Emergency Procedures]
3. **Report immediately to the control centre.**^[46d617e505500254:Emergency Procedures]

This reporting step ensures that the control centre is aware of the fault, can coordinate safe isolation, and can initiate the appropriate response. The procedure is part of the broader safe working practices that include [[cable.isolation.and.earthing]], [[voltage.absence.verification]], [[safety.locks.and.tags]], and establishing a [[safe.work.zone.with.barriers]].^[46d617e505500254:Regulatory Framework, Safe Working Practices]
