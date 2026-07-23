---
type: cluster
level: 1
entity_id: default.cluster.l1.approved-conductor-suppliers-hv-cables
title: Approved Conductor Suppliers for High-Voltage Cables
domain: default
confidence: 0.8
schema_version: '1.0'
description: This cluster groups approved suppliers of conductor materials—aluminium
  and copper rod—used in high-voltage cable systems.
tags:
- conductor
- supplier
- high-voltage cable
- aluminium
- copper
- approved supplier list
children:
- conductor_suppliers_hv_cables
- norsk_hydro_aluminium_rod
- aurubis_copper_rod
cluster_meta:
  algo: hdbscan
  run_id: default.cluster.l1.approved-conductor-suppliers-hv-cables
  cohesion: 0.7
created_at: '2026-07-22T05:45:56.459737+00:00'
updated_at: '2026-07-22T05:45:56.459737+00:00'
---

The reliability of high-voltage cable systems depends critically on the quality of conductor materials. Approved suppliers must meet stringent international standards such as IEC 60228 for aluminium and EN 13601 for copper. This cluster brings together key suppliers of conductor rod for HV cables.

[[conductor_suppliers_hv_cables]] serves as the overarching page listing approved suppliers. Two specific suppliers are detailed: [[norsk_hydro_aluminium_rod]] provides aluminium rod certified to IEC 60228, while [[aurubis_copper_rod]] supplies oxygen-free copper rod certified to EN 13601. Together, these pages form a comprehensive reference for sourcing conductor materials in high-voltage cable manufacturing.
