# Smart Stop Sign Concept

## Goal

Create a proof-of-concept traffic control environment where vehicles and the intersection cooperate instead of relying only on passive stop signs.

## Intended Hardware Model

- **LiDAR/object sensing:** Detect vehicles approaching, waiting, entering, and clearing the intersection.
- **V2X messaging:** Receive approach direction, intent, and queue status from connected vehicles.
- **Smart sign output:** Display a clear permission signal for the active approach.
- **Controller policy:** Maintain deterministic ordering so drivers and vehicles can understand who moves next.

## Simulator Role

`src/smart_stop_sign_sim.py` represents the controller logic and visual behavior before hardware is complete. Each spawned vehicle approximates a detected or connected vehicle. The controller queues vehicles by approach direction, grants the green indicator to one direction, and waits for the active vehicle to clear the intersection before granting the next approach.

## Development Notes

- Keep simulator behavior explainable; this project is meant to demonstrate ordered right-of-way behavior.
- Hardware integrations should preserve the same state concepts: detected, queued, granted, entering, clearing, and complete.
- Future work can add confidence values, LiDAR zones, V2X packet simulation, emergency priority, and logging.
