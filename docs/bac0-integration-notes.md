# BAC0 / bacpypes3 integration notes

Real gotchas we hit building a BACnet device + client against
`BAC0 2025.9.15` / `bacpypes3 0.0.106`, and how we fixed each. These are
general BACnet programming lessons — nothing here is specific to any lab.

## 1. Releasing a priority with BACnet NULL — it's literal `null`, not `None`

Writing `presentValue` on a commandable object takes a priority slot. To
release it you write BACnet **NULL**. In this BAC0 build the write-string parser
wants the literal lowercase token `null`; passing Python `None` raises
`ValueError`.

    # release priority 8 on a binary output
    await client._write(f"{addr} binaryOutput {inst} presentValue null - 8")

## 2. Object instances are 0-based

A device's first two binary outputs are instances **0 and 1**, not 1 and 2.
Off-by-one here silently targets the wrong object (or none).

## 3. Register your local objects once, as a batch

`add_objects_to_application()` registers **all** currently-pending objects, not
just the one you call it on. Call it per-object and you register duplicates —
build every object first, then call it a single time.

    ai = analog_input(name="Room_Temperature", ...)
    av = analog_value(name="Temperature_Setpoint", ...)
    bo = binary_output(name="AC_Output", ...)
    bo.add_objects_to_application(dev)   # registers ai, av, and bo together — once

## 4. `write()` is fire-and-forget; await `_write()` when the result matters

`write()` returns before the write is confirmed. When the value must have landed
before the next step, use the awaited form (and read it back to confirm).

    await client._write(f"{addr} analogValue {inst} presentValue 25.0")

## 5. A written priority *holds* until you release it

Writing `presentValue` doesn't just set a value — it pins that priority level
until explicitly released. To fully return an object to its auto/relinquished
state, clear **all 16** priority levels with NULL (see #1), not just the one you
wrote.

    for p in range(1, 17):
        await client._write(f"{addr} binaryOutput {inst} presentValue null - {p}")

## 6. On a switched LAN, unicast BACnet is invisible to a network tap

BACnet point reads/writes to a specific device are unicast, so a passive tap
elsewhere on a switched network won't see them. Any monitoring or detection has
to run **on the device** (or on its port), not from a bystander host.
