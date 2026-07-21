---
type: concept
level: 0
entity_id: installation.temperature
title: Installation Temperature
domain: default
confidence: 0.5
schema_version: '1.0'
description: Minimum ambient temperature permitted during cable installation to prevent
  damage to insulation and sheathing materials.
tags:
- installation
- temperature
- cable handling
sources:
- source_id: 8913d160a82c281a
  source_path: C:\Users\botta\github\klustra\.smoke_project\corpus\installation_guide.txt
created_at: '2026-07-21T23:18:00.780910+00:00'
updated_at: '2026-07-21T23:18:00.780910+00:00'
---

## General requirement

Cables must be installed only when the ambient temperature is **above 0 °C** (32 °F). This condition applies to all installation methods — duct pulling, direct burial, and jointing — and is intended to prevent embrittlement of the [[xlpe.insulation]] and the [[outer.protective.jacket]], which can lead to cracking or reduced flexibility during handling.^[8913d160a82c281a]

## Related installation parameters

- [[installation.minimum.bending.radius]] – minimum bending radius during installation is 20× cable outer diameter.^[8913d160a82c281a]
- [[installation.maximum.pulling.tension]] – maximum pulling tension must not exceed 50 N/mm² on the conductor.^[8913d160a82c281a]
- [[installation.duct.installation]] – duct pulling requires compatible lubricant and steady winch speed.^[8913d160a82c281a]
- [[installation.direct.burial]] – trench depth, sand bedding, and warning tape specifications.^[8913d160a82c281a]
- [[installation.jointing]] – joints must be installed in a controlled environment; prefabricated joints preferred.^[8913d160a82c281a]

## Practical considerations

If installation must proceed in cold weather, temporary heating of the cable drum or the work area may be required. The 0 °C limit is a general minimum; local regulations or manufacturer specifications may impose stricter limits for certain cable designs (e.g., [[xlpe.insulation]] compounds with higher stiffness at low temperature).
