---
type: cluster
level: 1
entity_id: default.cluster.l1.high-voltage-cable-system-materials
title: High-Voltage Cable System Components and Materials
domain: default
confidence: 0.8
schema_version: '1.0'
description: This cluster groups approved suppliers and materials used in high-voltage
  cable systems, including conductor materials, insulation compounds, sheathing barriers,
  and jointing accessories.
tags:
- high-voltage cables
- cable components
- approved suppliers
- insulation
- sheathing
- jointing
children:
- norsk_hydro
- dow_chemical_hfda_4202_ec
- exxonmobil_hdpe_compound
- arkema_aluminium_pe_laminate_tape
- nkt_cold_shrink_joints
cluster_meta:
  algo: hdbscan
  run_id: default.cluster.l1.high-voltage-cable-system-materials
  cohesion: 0.7
created_at: '2026-07-21T10:10:27.339421+00:00'
updated_at: '2026-07-21T10:10:27.339421+00:00'
---

This cluster brings together five key suppliers and materials that form the backbone of modern high-voltage cable systems. Each member plays a specific role in the cable’s lifecycle, from conductor to insulation to outer protection and jointing. [[norsk_hydro]] supplies aluminium rod certified to IEC 60228, which serves as the conductive core of the cable. [[dow_chemical_hfda_4202_ec]] provides an extra-clean XLPE compound used as the primary insulation layer, ensuring electrical integrity under high stress. Together, these two materials enable the core transmission function of the cable.

Surrounding the insulated conductor, the cable requires robust sheathing to protect against moisture and mechanical damage. [[exxonmobil_hdpe_compound]] is a high-density polyethylene compound approved for use as a radial moisture barrier in the cable’s outer jacket. [[arkema_aluminium_pe_laminate_tape]] works in conjunction with such HDPE compounds, providing an additional aluminium-PE laminate layer that prevents water ingress—critical for applications in underground networks, submarine crossings, and offshore wind farms.

Finally, [[nkt_cold_shrink_joints]] are pre-moulded accessories designed for jointing cables with XLPE insulation in the 66–170 kV range. These joints are approved to IEC 62067 and rely on the same material standards as the cables themselves, ensuring seamless system performance. The cluster therefore illustrates a complete ecosystem of materials and components, where each approved supplier contributes to a reliable, long-lasting high-voltage cable system.
