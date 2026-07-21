## High-Voltage Withstand Test (cable.testing.high_voltage_withstand_test)

The high-voltage withstand test is a fundamental electrical test applied to [[cable.testing.high_voltage_withstand_test|high-voltage cable systems]] to verify the integrity of the insulation system. It is performed at different stages of a cable's life cycle: during [[cable.testing.type_testing|type testing]], [[cable.testing.routine_testing|routine testing]], and [[cable.testing.after_installation_testing|after-installation testing]].

### Routine Testing (Factory)
Every manufactured cable length must undergo a high-voltage withstand test. The test is conducted at **2.5 U₀** (where U₀ is the rated phase-to-ground voltage) for a duration of **30 minutes**^[362871cd3841da0e:Routine Testing]. This test is a go/no-go check that ensures the cable can withstand the applied overvoltage without breakdown.

### Type Testing (Design Qualification)
During type testing per [[iec.62067|IEC 62067]], the electrical withstand voltage test validates the cable system design. It is one of several electrical tests that also include [[cable.testing.partial_discharge_measurement|partial discharge measurement]] and tan δ measurement^[362871cd3841da0e:Type Testing]. The mechanical and thermal performance of the cable system is also verified in the same type-test sequence.

### After‑Installation Testing (Commissioning)
On-site commissioning tests include a DC or VLF (Very Low Frequency) withstand test^[362871cd3841da0e:After-Installation Testing]. This test is applied after the cable has been installed, jointed, and terminated to confirm that the installation process did not damage the insulation. Supplementary tests such as [[cable.testing.sheath_integrity_test|sheath integrity test]] (10 kV DC for 1 minute) and [[cable.testing.joint_resistance_measurement|joint resistance measurement]] are also performed at this stage^[362871cd3841da0e:After-Installation Testing].

### Relation to Other Tests
The high-voltage withstand test is distinct from [[cable.testing.dc_vlf_withstand_testing|DC/VLF withstand testing]] (which is a specific technique used for on-site testing) and from [[cable.testing.partial_discharge_measurement|partial discharge measurement]] (which is a complementary diagnostic). A complete routine test sequence also includes [[cable.testing.conductor_resistance_check|conductor resistance check]]^[362871cd3841da0e:Routine Testing].

### Significance
Passing the high-voltage withstand test gives confidence that the insulation system is free from gross defects such as [[electrical.treeing|electrical trees]] or mechanical damage that could lead to premature failure. It is a mandatory requirement in international standards such as [[iec.62067|IEC 62067]] and is applied to all cable types, including [[xlpe.insulation|XLPE‑insulated]] cables.

### References
* IEC 62067 – Power cables with extruded insulation and their accessories for rated voltages above 150 kV (Um = 170 kV) up to 500 kV (Um = 550 kV)
* Source: 362871cd3841da0e (Cable Testing Standards)
