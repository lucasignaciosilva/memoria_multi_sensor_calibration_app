#!/usr/bin/env python3
"""debug_calibration_math.py

Depuración matemática del patrón de calibración sin GUI.

Objetivos:
- Verificar cómo cambian los 4 centros al aplicar rotaciones X/Y/Z.
- Comparar rotación lógica (real) vs. rotación visual (offset de 90° en X).
- Detectar si una exportación está intercambiando ejes o dejando Z constante.

Uso:
    python3 scripts/debug_calibration_math.py
    python3 scripts/debug_calibration_math.py --rx 90 --ry 0 --rz 0 --scale 1.0
    python3 scripts/debug_calibration_math.py --center 1.9 -0.02 0.25 --rx 0 --ry 0 --rz 0
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import List

import numpy as np


def rotation_matrix_xyz(rx_deg: float, ry_deg: float, rz_deg: float) -> np.ndarray:
    rx = math.radians(rx_deg)
    ry = math.radians(ry_deg)
    rz = math.radians(rz_deg)

    rx_m = np.array([
        [1.0, 0.0, 0.0],
        [0.0, math.cos(rx), -math.sin(rx)],
        [0.0, math.sin(rx), math.cos(rx)],
    ])

    ry_m = np.array([
        [math.cos(ry), 0.0, math.sin(ry)],
        [0.0, 1.0, 0.0],
        [-math.sin(ry), 0.0, math.cos(ry)],
    ])

    rz_m = np.array([
        [math.cos(rz), -math.sin(rz), 0.0],
        [math.sin(rz), math.cos(rz), 0.0],
        [0.0, 0.0, 1.0],
    ])

    return rz_m @ ry_m @ rx_m


@dataclass
class CalibrationPatternMath:
    square_side: float = 0.24
    circle_radius: float = 0.075
    center_x: float = 0.0
    center_y: float = 0.0
    center_z: float = 0.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    display_rotation_offset_x: float = 90.0

    def local_centers(self) -> np.ndarray:
        half_side = self.square_side / 2.0
        return np.array([
            [-half_side, -half_side, 0.0],
            [ half_side, -half_side, 0.0],
            [ half_side,  half_side, 0.0],
            [-half_side,  half_side, 0.0],
        ], dtype=float)

    def centers(self, rx: float, ry: float, rz: float, scale: float = 1.0) -> np.ndarray:
        local = self.local_centers() * scale
        r = rotation_matrix_xyz(rx, ry, rz)
        world = np.array([r @ p for p in local], dtype=float)
        return world + np.array([self.center_x, self.center_y, self.center_z], dtype=float)

    def logical_centers(self, scale: float = 1.0) -> np.ndarray:
        return self.centers(self.rotation_x, self.rotation_y, self.rotation_z, scale)

    def display_centers(self, scale: float = 1.0) -> np.ndarray:
        return self.centers(
            self.rotation_x + self.display_rotation_offset_x,
            self.rotation_y,
            self.rotation_z,
            scale,
        )


def summarize(name: str, pts: np.ndarray) -> None:
    print(f"\n== {name} ==")
    for i, p in enumerate(pts, start=1):
        print(f"  #{i}: X={p[0]: .6f}  Y={p[1]: .6f}  Z={p[2]: .6f}")
    if len(pts) > 0:
        print("  ranges:")
        print(f"    X: {pts[:,0].min(): .6f} -> {pts[:,0].max(): .6f}")
        print(f"    Y: {pts[:,1].min(): .6f} -> {pts[:,1].max(): .6f}")
        print(f"    Z: {pts[:,2].min(): .6f} -> {pts[:,2].max(): .6f}")


def axis_sanity_check(pts: np.ndarray) -> List[str]:
    issues: List[str] = []
    z_span = float(pts[:, 2].max() - pts[:, 2].min()) if len(pts) else 0.0
    y_span = float(pts[:, 1].max() - pts[:, 1].min()) if len(pts) else 0.0
    x_span = float(pts[:, 0].max() - pts[:, 0].min()) if len(pts) else 0.0

    if z_span < 1e-6:
        issues.append("Z quedó constante: puede faltar la rotación visual o estar usando el centro en lugar de los 4 puntos.")
    if x_span < 1e-6:
        issues.append("X quedó constante: posible giro de 90° alrededor de Y o swap de ejes.")
    if y_span < 1e-6:
        issues.append("Y quedó constante: esto puede ser normal si la máscara está vertical en el plano XZ.")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--center", nargs=3, type=float, default=[0.0, 0.0, 0.0], metavar=("X", "Y", "Z"))
    parser.add_argument("--rx", type=float, default=0.0)
    parser.add_argument("--ry", type=float, default=0.0)
    parser.add_argument("--rz", type=float, default=0.0)
    parser.add_argument("--scale", type=float, default=1.0)
    args = parser.parse_args()

    pattern = CalibrationPatternMath(
        center_x=args.center[0],
        center_y=args.center[1],
        center_z=args.center[2],
        rotation_x=args.rx,
        rotation_y=args.ry,
        rotation_z=args.rz,
    )

    print("CalibrationPatternMath debug")
    print(f"  center=({pattern.center_x:.6f}, {pattern.center_y:.6f}, {pattern.center_z:.6f})")
    print(f"  rotation logical=({pattern.rotation_x:.2f}, {pattern.rotation_y:.2f}, {pattern.rotation_z:.2f}) deg")
    print(f"  display offset X={pattern.display_rotation_offset_x:.2f} deg")
    print(f"  scale={args.scale:.3f}")

    local = pattern.local_centers() * args.scale
    summarize("Local centers (before rotation)", local)

    logical = pattern.logical_centers(args.scale)
    summarize("Logical centers (saved/calculated from real rotations)", logical)

    display = pattern.display_centers(args.scale)
    summarize("Display centers (what the GUI should show for vertical mask)", display)

    print("\nAxis sanity checks:")
    for label, pts in [("logical", logical), ("display", display)]:
        issues = axis_sanity_check(pts)
        if issues:
            print(f"  {label}: suspicious")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print(f"  {label}: OK")

    print("\nExpected behavior quick check:")
    print("  - With rx=90°, the display view should move the square from XY plane to XZ plane.")
    print("  - If all Z are equal in 'display', the visual offset is not being applied or the wrong points are being saved.")
    print("  - If logical Z changes but display Z does not, the bug is in the GUI rendering path, not the math.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())