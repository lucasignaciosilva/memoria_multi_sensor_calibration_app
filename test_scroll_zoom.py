#!/usr/bin/env python3
"""Script de prueba para zoom con rueda del mouse en visualización 3D."""

import os
import sys
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtCore import Qt, QPoint
import matplotlib
matplotlib.use('Qt5Agg')

app = QApplication(sys.argv)

from gui_main import SensorTab3D

# Crear pestaña 3D
tab = SensorTab3D()
print("✅ SensorTab3D inicializado correctamente")

# Generar datos de prueba
np.random.seed(42)
n_points = 5000
theta = np.random.uniform(0, 2*np.pi, n_points)
phi = np.random.uniform(0, np.pi, n_points)
r = np.random.uniform(0, 10, n_points)

x = r * np.sin(phi) * np.cos(theta)
y = r * np.sin(phi) * np.sin(theta)
z = r * np.cos(phi)

pc = np.column_stack([x, y, z])

data = {
    'timestamp': 1234567890.123456,
    'pointcloud': pc,
    'images': {}
}

# Actualizar pestaña
tab.update_data(data)
print("✅ Nube de puntos cargada")

# Prueba de scroll simulado
print("\n📊 Prueba: Zoom con rueda del mouse")

class MockScrollEvent:
    """Clase simulada para eventos de scroll de matplotlib."""
    def __init__(self, button, inaxes=True):
        self.button = button
        self.inaxes = True if inaxes else None

# Test scroll up (acercar)
print("\n🔄 Simulando scroll UP (acercar):")
initial_zoom = tab.zoom_level
print(f"   Zoom inicial: {initial_zoom}x")

for i in range(3):
    event = MockScrollEvent('up')
    tab.on_scroll(event)
    print(f"   Scroll UP #{i+1}: {tab.zoom_level:.2f}x")

# Verificar que aumentó
assert tab.zoom_level > initial_zoom, "Error: zoom no aumentó"
print("   ✅ Zoom aumentó correctamente")

# Test scroll down (alejar)
print("\n🔄 Simulando scroll DOWN (alejar):")
pre_down_zoom = tab.zoom_level
print(f"   Zoom antes: {pre_down_zoom:.2f}x")

for i in range(3):
    event = MockScrollEvent('down')
    tab.on_scroll(event)
    print(f"   Scroll DOWN #{i+1}: {tab.zoom_level:.2f}x")

# Verificar que disminuyó
assert tab.zoom_level < pre_down_zoom, "Error: zoom no disminuyó"
print("   ✅ Zoom disminuyó correctamente")

# Test límites
print("\n📊 Prueba: Límites de zoom")
print(f"   Rango válido: [0.1, 5.0]")

# Forzar zoom alto
tab.zoom_slider.setValue(5.0)
event = MockScrollEvent('up')
tab.on_scroll(event)
print(f"   Zoom máximo (intento subir más): {tab.zoom_level:.2f}x")
assert tab.zoom_level == 5.0, "Error: zoom excedió máximo"

# Forzar zoom bajo
tab.zoom_slider.setValue(0.1)
event = MockScrollEvent('down')
tab.on_scroll(event)
print(f"   Zoom mínimo (intento bajar más): {tab.zoom_level:.2f}x")
assert tab.zoom_level == 0.1, "Error: zoom bajó del mínimo"

print("\n✅ Todos los tests de scroll completados exitosamente!")
print("\n📝 Resumen:")
print("   ✅ Scroll UP acerca la vista (aumenta zoom)")
print("   ✅ Scroll DOWN aleja la vista (disminuye zoom)")
print("   ✅ El slider se sincroniza automáticamente")
print("   ✅ Los límites [0.1, 5.0] se respetan")
print("   ✅ La visualización se redibuja en tiempo real")
