## Conductor Resistance Check

The conductor resistance check is a routine test performed on every manufactured cable length to verify that the DC resistance of the conductor meets the specified value. This test ensures that the conductor material ([[copper.conductor]] or [[aluminium.conductor]]) and cross-section are correct and that no manufacturing defects, such as broken strands or poor joints, are present.^[362871cd3841da0e:section:Cable Testing Standards]

### Purpose
- Confirm conductor material and cross-section compliance.
- Detect manufacturing defects like broken strands or poor connections.
- Ensure consistent electrical performance of the cable system.

### Procedure
The measurement is typically carried out using a low-resistance ohmmeter (e.g., a Kelvin bridge or micro-ohmmeter) with four-terminal sensing to eliminate lead and contact resistance errors. The conductor temperature is recorded, and the measured resistance is corrected to a standard reference temperature (usually 20 °C) using the temperature coefficient of resistance for the conductor material.^[362871cd3841da0e:section:Cable Testing Standards]

### Acceptance Criteria
The measured DC resistance at 20 °C must not exceed the maximum value specified in the relevant cable standard (e.g., IEC 60228 for conductors of insulated cables). For [[copper.conductor]], typical values are around 0.017241 Ω·mm²/m at 20 °C; for [[aluminium.conductor]], around 0.028264 Ω·mm²/m at 20 °C.^[362871cd3841da0e:section:Cable Testing Standards]

### Relation to Other Tests
The conductor resistance check is part of the routine testing suite defined in [[iec.62067]] for high-voltage cable systems. It is performed alongside the high-voltage withstand test and partial discharge measurement. After installation, a joint resistance measurement ([[cable.testing.joint_resistance_measurement]]) is performed to verify the integrity of field-installed joints.^[362871cd3841da0e:section:Cable Testing Standards]

### See Also
- [[cable.testing.routine_testing]]
- [[cable.testing.joint_resistance_measurement]]
- [[iec.62067]]
- [[copper.conductor]]
- [[aluminium.conductor]]