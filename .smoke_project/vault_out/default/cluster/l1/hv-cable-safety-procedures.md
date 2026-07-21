---
type: cluster
level: 1
entity_id: default.cluster.l1.hv-cable-safety-procedures
title: HV Cable Safety Procedures Framework
domain: default
confidence: 0.8
schema_version: '1.0'
description: All safety procedures, from statutory regulations to emergency protocols,
  required for personnel protection during high-voltage cable work, including isolation,
  verification, and fault response.
tags:
- safety
- high-voltage-cable
- isolation
- earthing
- emergency-procedures
- regulations
children:
- local.electrical.safety.regulations
- company.specific.safety.procedures
- cable.isolation.and.earthing
- voltage.absence.verification
- safety.locks.and.tags
- safe.work.zone.with.barriers
- exclusion.zone.for.cable.fault
- fault.re-energization.prohibition
- control.centre.reporting
cluster_meta:
  algo: hdbscan
  run_id: default.cluster.l1.hv-cable-safety-procedures
  cohesion: 0.7
created_at: '2026-07-21T23:18:00.781269+00:00'
updated_at: '2026-07-21T23:18:00.781269+00:00'
---

This cluster defines the core safety framework for working on high-voltage (HV) cable systems. It integrates **[[local.electrical.safety.regulations]]** and **[[company.specific.safety.procedures]]** to form a jurisdictional and organizational compliance base. Both statutory codes and internal protocols mandate a strict sequence of actions before any work begins.

At the heart of this sequence is the six-step safe-work procedure. It begins with **[[cable.isolation.and.earthing]]** to disconnect and ground the cable, followed by **[[voltage.absence.verification]]** to confirm a de-energized state. Next, **[[safety.locks.and.tags]]** are applied to prevent accidental re-closure, and a **[[safe.work.zone.with.barriers]]** is established to control access. These steps are all governed by standards such as IEC 61936-1.

For emergency scenarios, specifically cable faults, additional critical procedures are introduced. An **[[exclusion.zone.for.cable.fault]]** (typically a 3 m perimeter) must be set up to protect personnel from the risk of spontaneous re-energization. A strict **[[fault.re-energization.prohibition]]** is enforced, forbidding re-energization until a full safety inspection is completed. All of this is coordinated through **[[control.centre.reporting]]**, ensuring immediate communication with the operations team to manage the incident and maintain grid stability.
