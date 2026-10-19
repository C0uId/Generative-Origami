"""Per-cell memoization of pure motion queries; no new geometric assumptions."""
import numpy as np


class MemoizedMotion:
    def __init__(self, motion):
        self.uncached_motion = motion
        self._triangles = {}
        self._boxes = {}
        self._chords = {}
        self._joints = {}

    def __getattr__(self, name):
        return getattr(self.uncached_motion, name)

    def triangle(self, panel, t):
        key = (int(panel),float(t))
        if key not in self._triangles:
            self._triangles[key] = self.uncached_motion.triangle(panel,t).copy()
        return self._triangles[key].copy()

    def vertex_bounds(self, panel, a=0., b=1.):
        key = (int(panel),float(a),float(b))
        if key not in self._boxes:
            lo,hi = self.uncached_motion.vertex_bounds(panel,a,b)
            self._boxes[key] = (lo.copy(),hi.copy())
        return tuple(x.copy() for x in self._boxes[key])

    def chord_error_bound(self, panel, a=0., b=1.):
        key = (int(panel),float(a),float(b))
        if key not in self._chords:
            self._chords[key] = self.uncached_motion.chord_error_bound(panel,a,b)
        return self._chords[key]

    def joint_bounds(self, a=0., b=1.):
        key = (float(a),float(b))
        if key not in self._joints:
            lo,hi = self.uncached_motion.joint_bounds(a,b)
            self._joints[key] = (lo.copy(),hi.copy())
        return tuple(x.copy() for x in self._joints[key])