---
type: concept
level: 0
entity_id: cable.testing.type_testing
title: Type Testing
domain: default
confidence: 0.5
schema_version: '1.0'
description: Type testing per IEC 62067 validates the design of a high-voltage cable
  system through a series of electrical, mechanical, and thermal tests to ensure it
  meets performance and safety requirements.
tags:
- cable testing
- type testing
- IEC 62067
- high-voltage cable
- design validation
- electrical testing
- mechanical testing
- thermal testing
sources:
- source_id: 362871cd3841da0e
  source_path: C:\Users\botta\github\klustra\.smoke_project\corpus\testing_procedures.md
created_at: '2026-07-21T23:18:00.781152+00:00'
updated_at: '2026-07-21T23:18:00.781152+00:00'
---

Type testing is a critical qualification process for high-voltage cable systems, performed according to [[iec.62067]] to validate the design of the cable and its accessories. Unlike routine testing, which is conducted on every manufactured length, type testing is carried out on a representative sample to confirm that the system design meets the required performance and safety standards.^[362871cd3841da0e:section:Cable Testing Standards]

## Test Categories

Type tests per IEC 62067 encompass three main categories:

- **Electrical tests**: These include withstand voltage tests, partial discharge measurement, and tan delta (dielectric loss) measurement. They verify the insulation integrity and overall electrical performance of the cable system.^[362871cd3841da0e:section:Cable Testing Standards]
- **Mechanical tests**: These involve bending tests and tensile tests to ensure the cable can withstand the mechanical stresses encountered during installation and service.^[362871cd3841da0e:section:Cable Testing Standards]
- **Thermal tests**: Load cycling at rated and emergency temperature conditions is performed to assess the cable's thermal performance and long-term reliability under operational heat cycles.^[362871cd3841da0e:section:Cable Testing Standards]

## Purpose and Scope

Type testing is essential for demonstrating that a cable system design is fit for purpose before it is approved for manufacturing and installation. It covers not only the cable itself but also its accessories such as joints and terminations, ensuring compatibility and overall system integrity. The tests are designed to simulate the most severe conditions the cable may encounter during its lifetime, including electrical stress, mechanical handling, and thermal cycling.

## Relationship to Other Testing

Type testing is distinct from [[cable.testing.routine_testing]] (performed on every cable length) and [[cable.testing.after_installation_testing]] (commissioning tests on site). While routine and after-installation tests focus on detecting manufacturing defects or installation damage, type testing validates the fundamental design and is typically required only once for a given cable system design, unless significant changes are made.^[362871cd3841da0e:section:Cable Testing Standards]
