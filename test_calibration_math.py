#!/usr/bin/env python3
"""Test de depuración para la matemática del patrón de calibración.

Este test no depende de PyQt. Verifica:
- La geometría base del patrón en XY.
- La vista visual vertical con offset de 90° en X.
- El caso de doble rotación, útil para detectar por qué la GUI puede aplanar o
  mover la máscara al plano equivocado.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

import numpy as np

from debug_calibration_math import CalibrationPatternMath


def span(arr: np.ndarray, axis: int) -> float:
    return float(arr[:, axis].max() - arr[:, axis].min())


def main() -> int:
    base = CalibrationPatternMath(center_x=1.9, center_y=-0.02, center_z=0.25)

    logical = base.logical_centers()
    display = base.display_centers()

    print("Test 1: patrón base sin rotación lógica")
    print(f"  logical spans: X={span(logical, 0):.6f}, Y={span(logical, 1):.6f}, Z={span(logical, 2):.6f}")
    print(f"  display spans: X={span(display, 0):.6f}, Y={span(display, 1):.6f}, Z={span(display, 2):.6f}")

    assert np.isclose(span(logical, 2), 0.0), "Sin rotación lógica, Z debe quedar constante"
    assert span(display, 2) > 0.0, "La vista visual vertical debe hacer variar Z"

    vertical = CalibrationPatternMath(center_x=1.9, center_y=-0.02, center_z=0.25, rotation_x=90.0)
    logical_v = vertical.logical_centers()
    display_v = vertical.display_centers()

    print("\nTest 2: rotación lógica de 90° en X")
    print(f"  logical spans: X={span(logical_v, 0):.6f}, Y={span(logical_v, 1):.6f}, Z={span(logical_v, 2):.6f}")
    print(f"  display spans: X={span(display_v, 0):.6f}, Y={span(display_v, 1):.6f}, Z={span(display_v, 2):.6f}")

    assert span(logical_v, 2) > 0.0, "Con rx=90°, la máscara lógica debe salir del plano XY"
    assert np.isclose(span(display_v, 2), 0.0, atol=1e-8), (
        "Con rx=90° + offset visual de 90°, la vista queda doble-rotada y Z puede quedar constante"
    )

    print("\nTest 3: detección de doble rotación")
    if np.isclose(span(display_v, 2), 0.0, atol=1e-8):
        print("  OK: el test detecta el caso de doble rotación (rx real + offset visual).");
    else:
        print("  WARNING: no se detectó la doble rotación esperada")

    print("\n✅ Test completado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())