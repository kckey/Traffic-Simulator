# Smart Stop Sign Traffic Simulator

Pygame proof-of-concept simulator for a smart stop sign environment where connected vehicles coordinate with infrastructure sensing.

This project is ongoing and currently in the hardware development stage. The simulator models the intended control behavior: vehicles approach a four-way stop, queue by direction, and receive an ordered right-of-way signal from a smart intersection controller. It is meant to communicate the V2X plus LiDAR concept before the hardware implementation is complete.

## Concept

- Vehicles communicate approach intent through a V2X-style queue model.
- A smart stop sign controller assigns right-of-way in a clear, ordered sequence.
- LiDAR-style detection is represented by vehicle presence, queue state, and intersection occupancy.
- Direction-specific green indicators show which approach has permission to move.
- The side panel exposes queue status, throughput, active grant state, and controls for spawning vehicles.

## Repository Layout

```text
src/
  smart_stop_sign_sim.py       Current Pygame proof-of-concept simulator
legacy/
  4way_tkinter_prototype.py    Earlier Tkinter prototype
docs/
  concept.md                   Hardware-development concept notes
```

## Run

Install Pygame:

```bash
python3 -m pip install pygame
```

Start the simulator:

```bash
python3 src/smart_stop_sign_sim.py
```

## Controls

- `A` or left arrow: spawn a westbound approach vehicle
- `D` or right arrow: spawn an eastbound approach vehicle
- `W` or up arrow: spawn a northbound approach vehicle
- `S` or down arrow: spawn a southbound approach vehicle
- Use the side-panel buttons to spawn vehicles by direction

## Hardware Direction

The simulation is designed to inform a physical smart-stop-sign prototype using roadside sensing, vehicle communication, and a deterministic right-of-way policy. The next development step is mapping simulator state transitions to hardware events from LiDAR/object detection and V2X messages.
