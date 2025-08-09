Here’s exactly how to wire your Raspberry Pi 4, HiLetgo 5 V relay module, and Rain Bird 24 VAC valve safely:

**Parts needed:**

* Raspberry Pi 4 with good quality 5 V, 3 A PSU
* HiLetgo 5 V one‑channel relay module (jumper set to **LOW trigger**)
* 24 VAC irrigation transformer (for the Rain Bird valve)
* Two lengths of wire for valve power
* Jumper wires for Pi → relay

**Wiring diagram:**

```
   Raspberry Pi 4 (BCM)
   +----------------------------+
   | [5V pin 4] --------------+  |
   |                          |  |
   | [GND pin 6] ---------+   |  |
   |                      |   |  |
   | [GPIO18 pin 12] ---+ |   |  |
   +--------------------|---|--+
                        |   |
                        v   v
                  +-----+---+-----+
                  | Relay Module  |
                  |               |
                  | VCC   GND   IN|
                  |  |     |    | |
                  |  |     |    | |
   24VAC HOT ---- COM    NO      |
                  |       |      |
   24VAC NEUTRAL ----------------+
                          |
                     Rain Bird Valve
```

**Step-by-step wiring:**

1. **Relay power (coil side):**

   * Relay **VCC** → Pi **5 V pin** (physical pin 4)
   * Relay **GND** → Pi **GND pin** (physical pin 6)

2. **Relay control:**

   * Relay **IN** → Pi GPIO pin (e.g., GPIO18, physical pin 12)
   * Jumper set to **LOW trigger** (LOW = ON)

3. **Valve power (contact side):**

   * Transformer **hot lead** → relay **COM**
   * Relay **NO** → one solenoid lead
   * Transformer **neutral lead** → other solenoid lead

4. **Isolation:** The 24 VAC circuit is fully isolated from the Pi’s electronics except through the relay’s contacts.

5. **Noise suppression (recommended):** Install an RC snubber or MOV across the valve leads.

**Operation:**

* GPIO18 LOW → Relay energizes → Valve opens
* GPIO18 HIGH → Relay de‑energizes → Valve closes
