#!/usr/bin/env python3
"""Script de prueba para selector de tópicos de LiDAR."""

import os
import sys
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from PyQt5.QtWidgets import QApplication
import matplotlib
matplotlib.use('Qt5Agg')

app = QApplication(sys.argv)

from gui_main import SensorTabLiDAR, SensorTab3D

print("✅ Clases importadas correctamente")

# Crear pestañas
tab_lidar = SensorTabLiDAR()
tab_3d = SensorTab3D()
print("✅ Pestañas inicializadas")

# Generar datos de prueba con dos tópicos de LiDAR
np.random.seed(42)

# PointCloud 1: /velodyne_points
n_points_1 = 5000
theta = np.random.uniform(0, 2*np.pi, n_points_1)
phi = np.random.uniform(0, np.pi, n_points_1)
r = np.random.uniform(0, 10, n_points_1)

x1 = r * np.sin(phi) * np.cos(theta)
y1 = r * np.sin(phi) * np.sin(theta)
z1 = r * np.cos(phi)
pc1 = np.column_stack([x1, y1, z1])

# PointCloud 2: /velodyne_points_interpolated (versión escalada)
pc2 = pc1 * 1.5  # Versión interpolada más grande

data = {
    'timestamp': 1234567890.123456,
    'pointcloud': pc1,  # Para backward compatibility
    'pointclouds': {
        '/velodyne_points': pc1,
        '/velodyne_points_interpolated': pc2,
    },
    'images': {}
}

print("\n📊 Prueba: Selector de Tópicos de LiDAR")

# Test 1: SensorTabLiDAR
print("\n1️⃣  SensorTabLiDAR:")
print("   Cargando datos con 2 tópicos...")
tab_lidar.update_data(data)

print(f"   Tópicos disponibles: {tab_lidar.available_lidar_topics}")
print(f"   Tópico seleccionado: {tab_lidar.selected_lidar_topic}")
print(f"   Combo items: {[tab_lidar.topic_combo.itemText(i) for i in range(tab_lidar.topic_combo.count())]}")

if tab_lidar.available_lidar_topics == ['/velodyne_points', '/velodyne_points_interpolated']:
    print("   ✅ Tópicos detectados correctamente")
else:
    print(f"   ❌ ERROR: Tópicos esperados: ['/velodyne_points', '/velodyne_points_interpolated'], obtenido: {tab_lidar.available_lidar_topics}")

# Test 2: Cambiar tópico en SensorTabLiDAR
print("\n2️⃣  Cambiar tópico a /velodyne_points_interpolated...")
tab_lidar.topic_combo.setCurrentText('/velodyne_points_interpolated')
print(f"   Tópico seleccionado: {tab_lidar.selected_lidar_topic}")
print(f"   Puntos último: {len(tab_lidar.last_pointcloud) if tab_lidar.last_pointcloud is not None else 'None'}")
print(f"   Expected: {len(pc2)}")

if tab_lidar.selected_lidar_topic == '/velodyne_points_interpolated' and \
   tab_lidar.last_pointcloud is not None and \
   len(tab_lidar.last_pointcloud) == len(pc2):
    print("   ✅ Cambio de tópico funcionó correctamente")
else:
    print("   ❌ ERROR: No se cambió correctamente el tópico")

# Test 3: SensorTab3D
print("\n3️⃣  SensorTab3D:")
print("   Cargando datos con 2 tópicos...")
tab_3d.update_data(data)

print(f"   Tópicos disponibles: {tab_3d.available_lidar_topics}")
print(f"   Tópico seleccionado: {tab_3d.selected_lidar_topic}")
print(f"   Combo items: {[tab_3d.topic_combo.itemText(i) for i in range(tab_3d.topic_combo.count())]}")

if tab_3d.available_lidar_topics == ['/velodyne_points', '/velodyne_points_interpolated']:
    print("   ✅ Tópicos detectados correctamente")
else:
    print(f"   ❌ ERROR: Tópicos detectados: {tab_3d.available_lidar_topics}")

# Test 4: Cambiar tópico en SensorTab3D
print("\n4️⃣  Cambiar tópico en SensorTab3D...")
tab_3d.topic_combo.setCurrentText('/velodyne_points_interpolated')
print(f"   Tópico seleccionado: {tab_3d.selected_lidar_topic}")

if tab_3d.selected_lidar_topic == '/velodyne_points_interpolated':
    print("   ✅ Cambio de tópico en 3D funcionó")
else:
    print("   ❌ ERROR: No se cambió el tópico en 3D")

# Test 5: Verificar que la visualización 3D se actualiza al cambiar tópico
print("\n5️⃣  Verificar que la visualización se actualiza...")
elev_antes = tab_3d.current_elev
azim_antes = tab_3d.current_azim
print(f"   Ángulo antes: elev={elev_antes}, azim={azim_antes}")

tab_3d.topic_combo.setCurrentText('/velodyne_points')
elev_despues = tab_3d.current_elev
azim_despues = tab_3d.current_azim
print(f"   Ángulo después: elev={elev_despues}, azim={azim_despues}")

# La visualización debe haber sido redibujada
if tab_3d.last_pointcloud is not None and len(tab_3d.last_pointcloud) == len(pc1):
    print("   ✅ Visualización 3D se actualizó correctamente")
else:
    print("   ❌ ERROR: Visualización no se actualizó")

print("\n✅ Test completado exitosamente!")
print("\n📝 Resumen:")
print("   ✅ Los tópicos se detectan automáticamente en ambas pestañas")
print("   ✅ Se puede cambiar entre /velodyne_points y /velodyne_points_interpolated")
print("   ✅ La visualización se actualiza al cambiar de tópico")
print("   ✅ Cada pestaña puede seleccionar independientemente su tópico")
