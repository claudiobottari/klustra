---
type: cluster
level: 1
entity_id: default.cluster.l1.post-installation-high-voltage-testing
title: Post-Installation High-Voltage Cable Testing
domain: default
confidence: 0.8
schema_version: '1.0'
description: Post-installation commissioning tests that verify the insulation and
  sheath integrity of high-voltage cable systems.
tags:
- testing
- high-voltage cables
- commissioning
- insulation
- sheath integrity
children:
- high_voltage_withstand_test
- sheath_integrity_test
cluster_meta:
  algo: hdbscan
  run_id: default.cluster.l1.post-installation-high-voltage-testing
  cohesion: 0.7
created_at: '2026-07-22T05:45:56.459783+00:00'
updated_at: '2026-07-22T05:45:56.459783+00:00'
---

This cluster covers **post-installation high-voltage testing** for cable systems, focusing on two complementary procedures that verify insulation and sheath integrity before commissioning.

Both [[high_voltage_withstand_test]] and [[sheath_integrity_test]] are performed after cable installation to detect defects that could lead to failure under normal operating conditions. The high voltage withstand test applies a voltage above the rated level to confirm the main insulation can withstand electrical stress, while the sheath integrity test specifically checks the metallic sheath or screen using a 10 kV DC application for one minute.

Together, these tests provide a comprehensive assessment of a cable system's electrical and mechanical integrity. Passing both is typically required before a high-voltage cable is placed into service, ensuring safety and reliability from the start of its operational life.
