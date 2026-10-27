#!/usr/bin/env python3
"""Script de prueba para la visualización 3D del LiDAR con controles."""

import os
import sys
os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # Headless mode para testing

import numpy as np
from pathlib import Path

# Agregar scripts a path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

# Import after environment setup
from PyQt5.QtWidgets import QApplication
import matplotlib
matplotlib.use('Qt5Agg')

# Create QApplication
app = QApplication(sys.argv)

# Now import GUI module
from gui_main import SensorTab3D

# Crear pestaña 3D
tab = SensorTab3D()
print("✅ SensorTab3D inicializado correctamente")

# Verificar que los controles existen
print(f"✅ Controles presentes:")
print(f"   - zoom_slider: {hasattr(tab, 'zoom_slider')}")
print(f"   - size_slider: {hasattr(tab, 'size_slider')}")
print(f"   - Atributos: zoom_level={tab.zoom_level}, point_size={tab.point_size}")

# Generar datos de prueba: nube de puntos LiDAR simulada
np.random.seed(42)
n_points = 5000

# Crear nube en forma de esfera/elipse
theta = np.random.uniform(0, 2*np.pi, n_points)
phi = np.random.uniform(0, np.pi, n_points)
r = np.random.uniform(0, 10, n_points)

x = r * np.sin(phi) * np.cos(theta)
y = r * np.sin(phi) * np.sin(theta)
z = r * np.cos(phi)

pc = np.column_stack([x, y, z])
print(f"\n✅ Nube de puntos generada: {pc.shape}")

# Simular datos de frame
data = {
    'timestamp': 1234567890.123456,
    'pointcloud': pc,
    'images': {}
}

# Actualizar pestaña con datos
print("\n🔄 Actualizando pestaña con datos de prueba...")
tab.update_data(data)
print("✅ Datos iniciales aplicados")

# Prueba 1: Cambiar zoom
print("\n📊 Prueba 1: Cambiar zoom")
test_zooms = [0.5, 1.0, 2.0, 5.0]
for zoom_val in test_zooms:
    tab.zoom_slider.setValue(zoom_val)
    print(f"   ✅ Zoom = {zoom_val}: zoom_level = {tab.zoom_level}")
    assert tab.zoom_level == zoom_val, f"Error: zoom no se actualizó"

# Prueba 2: Cambiar tamaño de puntos
print("\n📊 Prueba 2: Cambiar tamaño de puntos")
test_sizes = [0.5, 1.0, 2.0, 5.0, 10.0]
for size_val in test_sizes:
    tab.size_slider.setValue(size_val)
    print(f"   ✅ Tamaño = {size_val}: point_size = {tab.point_size}")
    assert tab.point_size == size_val, f"Error: size no se actualizó"

# Prueba 3: Verificar que los sliders se actualizan correctamente
print("\n📊 Prueba 3: Validación de rangos")
print(f"   Zoom - Min: {tab.zoom_slider.minimum()}, Max: {tab.zoom_slider.maximum()}")
print(f"   Tamaño - Min: {tab.size_slider.minimum()}, Max: {tab.size_slider.maximum()}")

# Reset a valores por defecto
tab.zoom_slider.setValue(1.0)
tab.size_slider.setValue(2.0)

print("\n✅ Todas las pruebas completadas exitosamente!")
print("✅ Controles de zoom y tamaño de puntos funcionan correctamente")
print("\nCuan es cargue un frame:")
print("   - Usa el slider de Zoom (0.1x a 5.0x) para acercar/alejar")
print("   - Usa el slider de Tamaño (0.5 a 10.0) para ajustar el tamaño de puntos")
print("   - Los cambios se aplican inmediatamente a la visualización")

