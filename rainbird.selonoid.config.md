rainbird configuation:

https://www.lowes.com/pd/Rain-Bird-0-75-in-Plastic-Electric-Inline-Irrigation-Valve/1057907?store=2600&cm_mmc=shp-_-c-_-prd-_-plb-_-ggl-_-CRP_SHP_LIA_PLB_Online_High_Priority(A-D%2BPriority+Items+CL3)-_-1057907-_-local-_-0-_-0&gad_source=1&gad_campaignid=21218170278&gbraid=0AAAAAD2B2W96kt88Rk4ZX2jsJiZgN4zT_&gclid=CjwKCAjw49vEBhAVEiwADnMbbIKRmfPwNIEmJqeg4BnVA8j91VVdy0ZtCPhV4Ck7CjtRwJ-Ij6a2zBoCQU0QAvD_BwE&gclsrc=aw.ds

Short answer: yes—but not directly from the Pi’s pins. That Rain Bird valve is almost certainly a **24 VAC, non-latching solenoid**. A Raspberry Pi can’t supply that voltage or current, so you’ll add a small interface (relay/SSR or a sprinkler HAT) and a 24 VAC supply.

Here’s a simple, reliable setup:

### What you need

* **Raspberry Pi** (any model with GPIO)
* **Opto-isolated relay module** (5 V logic, single channel). A mechanical relay is simplest; make sure its **contacts are rated for at least 1 A at 24 VAC**.
* **24 VAC “sprinkler” transformer** (often 24 VAC, 500–1000 mA)
* **Two wires to the valve** (polarity doesn’t matter for an AC non-latching valve)
* Optional: fuse on the 24 VAC line, weatherproof enclosure, strain relief.

### Wiring (text diagram)

* Pi 5 V → relay module VCC
* Pi GND → relay module GND
* Pi GPIO (e.g., GPIO17) → relay module IN
* 24 VAC transformer **one lead** → relay **COM** contact
* Relay **NO** contact → **one valve lead**
* Transformer **other lead** → **other valve lead**

When the relay closes, it completes the 24 VAC circuit through the valve and it opens.

> Avoid MOSFETs for this—those are for DC. For 24 VAC, use a relay or an AC-rated solid-state relay. If you do pick a solid-state relay, choose a **DC control / AC load** type and check it switches reliably at low voltage (some SSRs expect 120–240 VAC).

### Python example

```python
# Works on Raspberry Pi OS
# If you prefer gpiozero, see the alt snippet below.
import RPi.GPIO as GPIO
import time

RELAY_PIN = 17  # BCM numbering

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

def valve_on():
    GPIO.output(RELAY_PIN, GPIO.HIGH)  # Some relay boards are LOW-active; flip if needed

def valve_off():
    GPIO.output(RELAY_PIN, GPIO.LOW)

try:
    valve_on()
    print("Valve ON for 10 seconds...")
    time.sleep(10)
finally:
    valve_off()
    GPIO.cleanup()
    print("Valve OFF and GPIO cleaned up.")
```

**gpiozero version (nicer):**

```python
from gpiozero import OutputDevice
from time import sleep

# Set active_high=False if your relay is LOW-triggered
relay = OutputDevice(17, active_high=True, initial_value=False)

relay.on()      # valve on
sleep(10)
relay.off()     # valve off
```

### Good to know

* **Check your exact model**: Most Rain Bird garden valves are 24 VAC non-latching. If yours is a **latching DC valve**, you’d need a different driver (brief polarity-reversing pulses via an H-bridge), not a steady 24 VAC.
* **Current**: Typical hold current is a few hundred mA at 24 VAC; inrush can be higher. Pick a relay with comfortable margin.
* **Safety**: The 24 VAC transformer’s **primary is mains**—keep that side enclosed. Put the Pi and relay in a dry, ventilated enclosure; route the 24 VAC and valve wires with strain relief.
* **Multiple zones?** Consider a purpose-built board like **OpenSprinkler Pi** (HAT) or a multi-relay board; they handle 24 VAC distribution cleanly and come with software.

If you want, tell me which Rain Bird model number you have and I’ll double-check whether it’s the standard 24 VAC type and sketch wiring specific to that module/relay you plan to use.
