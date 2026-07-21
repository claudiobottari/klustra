---
type: concept
level: 0
entity_id: installation.prefabricated.joints
title: installation.prefabricated.joints
domain: default
confidence: 0.5
schema_version: '1.0'
description: Factory‑made, cold‑shrink or slip‑on accessories used to splice high‑voltage
  cable sections. They are preferred because they reduce on‑site work, minimise contamination
  risk and allow fast, repeatable installation.
tags:
- cable jointing
- high‑voltage accessories
- pre‑moulded joints
- cold‑shrink joints
sources:
- source_id: 8913d160a82c281a
  source_path: C:\Users\botta\github\klustra\.smoke_project\corpus\installation_guide.txt
created_at: '2026-07-21T23:18:00.780990+00:00'
updated_at: '2026-07-21T23:18:00.780990+00:00'
---

# installation.prefabricated.joints

Prefabricated joints (also known as pre‑moulded joints) are factory‑made cable accessories that allow rapid and reproducible field assembly of high‑voltage cable sections. They are the preferred jointing method for modern extruded dielectric cables because they minimise installation time and reduce the risk of on‑site contamination.^[8913d160a82c281a]

## Overview and design philosophy

A prefabricated joint consists of a factory‑moulded rubber (usually EPDM or silicone) housing that contains an internal electrode system designed to control the electric field at the cable cut‑ends. The joint body is pre‑expanded and shipped on a supporting core; during installation the core is removed, allowing the joint to shrink onto the prepared cable ends. This ``cold‑shrink'' principle (supplied, for example, by [[nkt.cold-shrink.joints.66-170.kv]]) avoids the need for heat or specialised curing equipment.^[8913d160a82c281a] The same principle is also adopted by manufacturers such as [[prysmian.pre-moulded.joints.terminations]].

Prefabricated joints are designed to meet [[iec.62067]] (power cables with extruded insulation for rated voltages above 150 kV) and its ancillary standards for testing. For voltages up to 170 kV the cold‑shrink type is widely used; above that, slip‑on or resin‑filled designs may be specified.^[8913d160a82c281a]

## Installation requirements

### Controlled environment

Field jointing must be carried out in a controlled environment. This typically means using a portable tent or enclosure that maintains low humidity (<60 % RH) and protects the joint from dust, rain and direct sunlight. The temperature inside the enclosure must be above 0 °C to match the requirement that cable installation temperature be above 0 °C.^[8913d160a82c281a]

### Joint bay dimensions

A joint bay – the excavated pit where two cable ends are brought together – must have minimum plan dimensions of 3 m × 1.5 m. These dimensions allow the cable ends to be laid out with the necessary [[bending.radii]] (minimum 20× cable outer diameter during installation) and give workers adequate space to fit the joint body and perform testing.^[8913d160a82c281a]

### Cable preparation

Before applying a prefabricated joint the cable ends must be cut square and the insulation surface must be clean and dry. The semi‑conductive screens, metallic sheath and outer jacket are peeled back to the lengths specified by the joint manufacturer. Conductor connections are made either by compression or by bolted connectors; the joint body is then positioned over the prepared section and the core is extracted to shrink it into place.^[8913d160a82c281a]

## Comparison with other jointing methods

| Aspect | Prefabricated (cold‑shrink) | Conventional (resin‑ or tape‑based) |
|--------|-----------------------------|-------------------------------------|
| Installation time | 30–60 min per joint | 2–4 h per joint |
| Skill dependency | Low – repeatable process | High – operator‑dependent |
| Contamination risk | Minimal – factory‑moulded | Higher – materials mixed on site |
| Immediate testing | Possible after cooling/relaxation | Requires full cure before testing |

---

## Quality assurance and testing

After installation each prefabricated joint must undergo the same [[cable.testing.after_installation_testing]] regime as the cable itself: a high‑voltage DC or VLF withstand test, partial discharge measurement, conductor resistance check and sheath integrity test. The joint resistance measurement is a specific check to confirm that the connector has not been damaged during the installation process.^[8913d160a82c281a]

## Related components and materials

- [[cable.isolation.and.earthing]] – safety procedures before opening a joint.
- [[installation.joint.bay.dimensions]] – detailed requirements for the bay layout.
- [[iec.62067]] – standard covering joints for high‑voltage cables.

## References

1. Cable Installation Guide, 8913d160a82c281a.
