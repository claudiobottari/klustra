---
type: concept
level: 0
entity_id: maximum_pulling_tension
title: maximum_pulling_tension
domain: default
confidence: 0.5
schema_version: '1.0'
description: Maximum allowable longitudinal force applied to a cable conductor during
  pulling, expressed as stress on the conductor cross-section.
tags:
- installation parameter
- mechanical limit
- cable pulling
sources:
- source_id: 4548a58ab1ab402c
  source_path: C:\Users\bottacl001\GitHub\klustra\.smoke_project\corpus\installation_guide.txt
created_at: '2026-07-21T10:10:27.339064+00:00'
updated_at: '2026-07-21T10:10:27.339064+00:00'
---

In [[high_voltage_cable_systems]] installation, **maximum pulling tension** is the highest allowable longitudinal force applied to the cable during pulling, and it must not exceed **50 N/mm² on the conductor** ([[cable_core]])^[4548a58ab1ab402c]. This limit prevents mechanical damage (e.g., conductor necking, insulation stretching) that could degrade electrical performance. To ensure compliance, a [[cable_winch_tension_monitoring]] system is used during pulling, typically at a steady rate of 5–10 m/min^[4548a58ab1ab402c]. The limit is independent of cable type, but specific installation conditions (e.g., [[duct_installation]], [[direct_burial]]) may require lower tension to avoid damage from friction or bends. The pulling tension value is verified by the winch’s tension gauge and should be recorded for quality assurance.
