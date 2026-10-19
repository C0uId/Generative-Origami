# Replaceable native CCD adapter ABI

The current build uses the Python/reference backend. No third-party library is vendored or compiled into this project. The local build probe is stored with the experiment results.

To integrate a C++ implementation, provide an importable `generative_origami._tight_inclusion` extension with `vertex_face` and `edge_edge` methods. Both receive `start` and `end` NumPy-compatible arrays of shape `(4,3)` and keyword parameters `minimum_separation`, `tolerance`, `max_subdivisions`, `numerical_error`.

- Vertex-face point order: moving vertex, triangle corner0, corner1, corner2.
- Edge-edge order: first edge endpoint0/1, second edge endpoint0/1.
- Time scope is the entire normalized `[0,1]` interval.
- Return `False` only for a proven no-hit result; `True` means a conservative possible hit. Alternatively return the `CCDResult` schema from `ccd_adapter.py`.
- A safe partial interval is not a safe full query. Backend exceptions and invalid results become `UNCERTAIN`.
- Map the adapter budget to the actual library's iteration settings and retain its numerical error filters. Report unresolved/native tolerance exhaustion conservatively.

Upstream [Tight-Inclusion documentation](https://github.com/Continuous-Collision-Detection/Tight-Inclusion) describes the vertex-face/edge-edge queries and false=no-collision / true=possible-hit semantics. Our interface is inspired by those semantics; the Python implementation is a distance/projection bound reference, **not** a reimplementation or binary of its interval root finder.

The outer certifier always evaluates the true curved FK trajectory. Vertex chords are passed only as surrogates, with both panels' curvature error added to minimum separation. Replacing the backend must preserve that inflation. The curved-to-linear conservative strategy is also discussed in [Rigid-IPC](https://ipc-sim.github.io/rigid-ipc/assets/rigid_ipc_paper.pdf).

Try `python certify_motion.py --backend native`. If the extension is absent this exits3 with an explicit error; it never silently changes to the reference implementation. Use `--backend reference` explicitly for the supplied runnable implementation.