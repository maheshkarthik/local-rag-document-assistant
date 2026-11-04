# Kestrel T2 Smart Thermostat User Manual
> Model KT2-100 (24 V) and KT2-100L (line voltage). Manual revision C, 2026. Kestrel Home Systems is a fictional manufacturer; this manual is a sample for testing.

## 1. Safety Information

- Turn off power to your heating and cooling system at the circuit breaker before installing or removing the thermostat.
- The KT2-100 works only with 24 V low-voltage systems. Do **not** connect it to 120 V or 240 V line-voltage heaters such as baseboard heaters; use the KT2-100L for those.
- Do not install the thermostat on an outside wall, in direct sunlight, or within 1 m (3 ft) of heat sources such as lamps, ovens or air vents. These locations cause inaccurate readings.
- The thermostat contains a rechargeable lithium battery. Do not dispose of it in household waste.

## 2. What's in the Box

- Kestrel T2 display unit
- Wall plate with 10 labelled terminals
- C-wire adapter (CWA-1) for systems without a common wire
- Trim plate (to cover marks left by an old thermostat)
- 4 screws and 4 wall anchors
- Wire labels and this manual

## 3. Compatibility

The KT2-100 supports most 24 V systems, including:

| System type | Supported | Notes |
|---|---|---|
| Gas, oil or electric forced-air furnace | Yes | Up to 2 heating stages |
| Central air conditioning | Yes | Up to 2 cooling stages |
| Heat pump with auxiliary/emergency heat | Yes | O/B reversing valve configurable |
| Boiler (hot water radiators) | Yes | Fan control not available |
| Humidifier or dehumidifier | Yes | Uses the ACC+ and ACC- terminals |
| Millivolt systems (some gas fireplaces) | No | |
| Line voltage (120/240 V) heaters | No | Use model KT2-100L |

<!-- pagebreak -->

## 4. Installation

### 4.1 Remove your old thermostat

1. Turn off power at the breaker. Confirm the system is off by changing the old thermostat's setting; nothing should start.
2. Take a photo of the existing wiring before disconnecting anything.
3. Label each wire with the supplied stickers using the letter of the terminal it was connected to (for example R, W, Y, G, C).
4. Disconnect the wires and remove the old wall plate.

### 4.2 Wire the Kestrel T2

| Terminal | Typical wire colour | Function |
|---|---|---|
| R / Rh | Red | 24 V power (heating) |
| Rc | Red | 24 V power (cooling), if separate transformer |
| C | Blue or black | Common wire, required for continuous power |
| W1 | White | Heat stage 1 |
| W2 | Brown | Heat stage 2 or auxiliary heat |
| Y1 | Yellow | Cool stage 1 or compressor |
| Y2 | Light blue | Cool stage 2 |
| G | Green | Fan |
| O/B | Orange or dark blue | Heat pump reversing valve |
| ACC+ / ACC- | Varies | Humidifier, dehumidifier or ventilator |

Wire colours are not standardized. Always follow the terminal letters on your old thermostat rather than the colours.

If your system has no C wire, install the C-wire adapter (CWA-1) at the furnace control board, following the separate leaflet in the box. Without a C wire the thermostat runs on its battery and may show error **E04**.

### 4.3 Power on and setup

Mount the display, turn the power back on and follow the on-screen setup. The setup wizard asks for your system type, Wi-Fi network and the Kestrel Home app pairing code. Setup takes about 10 minutes.

<!-- pagebreak -->

## 5. Using the Thermostat

### 5.1 Modes

- **Heat**, **Cool**, **Auto** (switches between heat and cool automatically) and **Off**.
- In Auto mode, the heat and cool setpoints must be at least **3 F (1.5 C)** apart. This is called the deadband.
- **Eco mode** widens the temperature range when nobody is home: by default heating holds 62 F (17 C) and cooling holds 80 F (27 C).

### 5.2 Schedules

You can create up to **8 schedule periods per day** in the app or on the device. The thermostat learns how long your home takes to warm up or cool down and starts early so it reaches the target temperature at the scheduled time (Early Start). Early Start can be turned off in Settings > Schedule.

### 5.3 Temperature hold

Press and hold the dial for 2 seconds to hold the current setpoint. Holds last until the next schedule period, or for 2, 4 or 8 hours, or permanently until cancelled.

### 5.4 Filter reminders

The thermostat counts system run time and reminds you to change the air filter after **300 hours** of runtime (about 3 months for typical use). The interval can be changed between 100 and 1,000 hours.

## 6. Error Codes

| Code | Meaning | What to do |
|---|---|---|
| E01 | Internal temperature sensor failure | Restart the thermostat. If the error persists, contact support for a replacement. |
| E02 | No power on the R or Rh wire | Check that the breaker and furnace door switch are on, and that the R wire is fully inserted. |
| E03 | No signal from heating stage (W1) | Check the W1 wire connection. Check the furnace fuse (usually 3 A or 5 A). |
| E04 | Low battery / no C wire detected | Connect a C wire or install the CWA-1 adapter. |
| E05 | Cooling did not start within 10 minutes | Check the Y1 wire. Check the outdoor unit's breaker and disconnect switch. |
| E06 | Wi-Fi network not found | Check the router is on; the T2 supports 2.4 GHz networks only. |
| E07 | Wi-Fi password rejected | Re-enter the password in Settings > Network. |
| E08 | Cloud connection lost for over 24 hours | The thermostat keeps working locally. Check the internet connection. |
| E09 | Humidity sensor out of range | Clean the vents on the side of the unit. Restart. |
| E10 | Heat pump O/B setting mismatch | Change O/B setting between "O on cool" and "B on heat" in Settings > Equipment. |
| E11 | Firmware update failed | Leave the thermostat powered; it retries automatically after 1 hour. |
| E12 | Temperature outside safe range (below 40 F / above 95 F) | Check the heating or cooling system immediately; the thermostat sends an alert to the app. |

<!-- pagebreak -->

## 7. Maintenance and Reset

- Clean the display with a dry microfibre cloth. Do not spray cleaners directly on the unit.
- **Restart:** Settings > Device > Restart, or remove the display from the wall plate for 10 seconds.
- **Factory reset:** Settings > Device > Factory Reset, or hold the dial pressed for **20 seconds** until the screen shows a countdown. A factory reset erases schedules, Wi-Fi settings and the app link, but keeps the wiring configuration.

## 8. Technical Specifications

| Specification | KT2-100 |
|---|---|
| Power | 24 V AC, 50/60 Hz, via C wire; 0.6 W typical |
| Battery | Rechargeable lithium-ion, backup only |
| Display | 2.4 inch colour LCD, 320 x 240 |
| Temperature accuracy | +/- 0.5 F (0.3 C) |
| Setpoint range | 45 to 90 F (7 to 32 C) |
| Wireless | Wi-Fi 802.11 b/g/n 2.4 GHz; Bluetooth LE 5.0 |
| Dimensions | 84 x 84 x 24 mm |
| Operating temperature | 32 to 104 F (0 to 40 C) |

## 9. Warranty and Support

The Kestrel T2 comes with a **3-year limited warranty** from the date of purchase, extended to 5 years if installed by a Kestrel Certified Installer and registered within 60 days. The warranty does not cover damage caused by incorrect wiring, including connecting the KT2-100 to line voltage.

Support: support@kestrelhome.example or 1-888-555-0123, Monday to Saturday, 7 a.m. to 9 p.m. Eastern Time. Have your device serial number ready; it is printed on the back of the display and starts with "KT2".
