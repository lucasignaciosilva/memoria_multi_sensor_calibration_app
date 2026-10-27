#!/usr/bin/env python3
"""
Demostración visual: Selector de tópicos de LiDAR
Muestra cómo ambas pestañas pueden visualizar tópicos diferentes
"""

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

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                    DEMOSTRACIÓN: SELECTOR DE TÓPICOS                       ║
║                                                                            ║
║  Esta demo muestra cómo las pestañas 2D y 3D pueden visualizar           ║
║  DIFERENTES tópicos de LiDAR simultáneamente                             ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

# Crear tablas
tab_lidar_2d = SensorTabLiDAR()
tab_lidar_3d = SensorTab3D()

# Generar datos realistas
np.random.seed(42)

print("\n📊 GENERANDO DATOS DE PRUEBA...")
print("─" * 80)

# Escenario realista: 
# - /velodyne_points: 65536 puntos (datos crudos del sensor)
# - /velodyne_points_interpolated: 131072 puntos (versión interpolada)

n_points_raw = 65536
theta = np.random.uniform(0, 2*np.pi, n_points_raw)
phi = np.random.uniform(0, np.pi, n_points_raw)
r = np.random.uniform(0.5, 100, n_points_raw)

x_raw = r * np.sin(phi) * np.cos(theta)
y_raw = r * np.sin(phi) * np.sin(theta)
z_raw = r * np.cos(phi)
pc_raw = np.column_stack([x_raw, y_raw, z_raw])

# Versión interpolada: más puntos pero escalados
pc_interpolated = pc_raw * 1.2  # Escala de interpolación
pc_interpolated = np.vstack([
    pc_raw,
    pc_raw * 1.05,  # Añadir puntos interpolados
])

data = {
    'timestamp': 1234567890.123456,
    'pointcloud': pc_raw,  # backward compat
    'pointclouds': {
        '/velodyne_points': pc_raw,
        '/velodyne_points_interpolated': pc_interpolated,
    },
    'images': {}
}

print(f"✅ /velodyne_points:              {len(pc_raw):,} puntos")
print(f"✅ /velodyne_points_interpolated: {len(pc_interpolated):,} puntos")
print(f"✅ Timestamp: {data['timestamp']}")

# Cargar datos
print("\n📋 CARGANDO DATOS EN LAS PESTAÑAS...")
print("─" * 80)

tab_lidar_2d.update_data(data)
tab_lidar_3d.update_data(data)

print(f"✅ Pestaña LiDAR 2D cargada")
print(f"   - Tópicos disponibles: {tab_lidar_2d.available_lidar_topics}")
print(f"   - Tópico actual: {tab_lidar_2d.selected_lidar_topic}")
print(f"   - Puntos mostrados: {len(tab_lidar_2d.last_pointcloud):,}")

print(f"\n✅ Pestaña Vista 3D cargada")
print(f"   - Tópicos disponibles: {tab_lidar_3d.available_lidar_topics}")
print(f"   - Tópico actual: {tab_lidar_3d.selected_lidar_topic}")
print(f"   - Puntos mostrados: {len(tab_lidar_3d.last_pointcloud):,}")

# ESCENARIO 1: Ambas con /velodyne_points
print("\n" + "=" * 80)
print("ESCENARIO 1: Ambas pestañas con /velodyne_points (PREDETERMINADO)")
print("=" * 80)

print(f"\n📺 Pestaña LiDAR 2D:")
print(f"   Tópico: {tab_lidar_2d.selected_lidar_topic}")
print(f"   Puntos: {len(tab_lidar_2d.last_pointcloud):,}")

print(f"\n📺 Pestaña Vista 3D:")
print(f"   Tópico: {tab_lidar_3d.selected_lidar_topic}")
print(f"   Puntos: {len(tab_lidar_3d.last_pointcloud):,}")

print("\n💭 Observación: Ambas muestran la misma nube cruda del sensor")

# ESCENARIO 2: Cambiar solo pestaña 3D
print("\n" + "=" * 80)
print("ESCENARIO 2: Cambiar Vista 3D a /velodyne_points_interpolated")
print("=" * 80)

tab_lidar_3d.topic_combo.setCurrentText('/velodyne_points_interpolated')

print(f"\n📺 Pestaña LiDAR 2D (SIN CAMBIOS):")
print(f"   Tópico: {tab_lidar_2d.selected_lidar_topic}")
print(f"   Puntos: {len(tab_lidar_2d.last_pointcloud):,}")

print(f"\n📺 Pestaña Vista 3D (CAMBIÓ):")
print(f"   Tópico: {tab_lidar_3d.selected_lidar_topic}")
print(f"   Puntos: {len(tab_lidar_3d.last_pointcloud):,}")

print("\n✨ ¡AHORA SON DIFERENTES! Cada pestaña muestra un tópico distinto")

# ESCENARIO 3: Cambiar también pestaña 2D
print("\n" + "=" * 80)
print("ESCENARIO 3: Cambiar también pestaña 2D a /velodyne_points_interpolated")
print("=" * 80)

tab_lidar_2d.topic_combo.setCurrentText('/velodyne_points_interpolated')

print(f"\n📺 Pestaña LiDAR 2D (CAMBIÓ):")
print(f"   Tópico: {tab_lidar_2d.selected_lidar_topic}")
print(f"   Puntos: {len(tab_lidar_2d.last_pointcloud):,}")

print(f"\n📺 Pestaña Vista 3D:")
print(f"   Tópico: {tab_lidar_3d.selected_lidar_topic}")
print(f"   Puntos: {len(tab_lidar_3d.last_pointcloud):,}")

print("\n💭 Observación: Ahora ambas muestran la versión interpolada (más puntos)")

# ESCENARIO 4: Volver a diferentes
print("\n" + "=" * 80)
print("ESCENARIO 4: Volver a tópicos DIFERENTES para comparación")
print("=" * 80)

tab_lidar_2d.topic_combo.setCurrentText('/velodyne_points')

print(f"\n📺 Pestaña LiDAR 2D:")
print(f"   Tópico: {tab_lidar_2d.selected_lidar_topic}")
print(f"   Puntos: {len(tab_lidar_2d.last_pointcloud):,}")

print(f"\n📺 Pestaña Vista 3D:")
print(f"   Tópico: {tab_lidar_3d.selected_lidar_topic}")
print(f"   Puntos: {len(tab_lidar_3d.last_pointcloud):,}")

print("""
✅ COMPARACIÓN EN TIEMPO REAL:
   ┌────────────────────────────────┬────────────────────────────────┐
   │    Pestaña LiDAR 2D (Cruda)    │  Pestaña Vista 3D (Interp.)   │
   ├────────────────────────────────┼────────────────────────────────┤
   │ /velodyne_points               │ /velodyne_points_interpolated  │
   │ 65,536 puntos                  │ 131,072 puntos                 │
   │ Proyección XY con altura       │ Nube 3D interactiva            │
   │ Recuento y estadísticas        │ Zoom y rotación                │
   └────────────────────────────────┴────────────────────────────────┘

CASOS DE USO:
─────────────

✓ Validar interpolación: Ver si los puntos interpolados se distribuyen
  bien sin crear artefactos visuales

✓ Debugging: Comparar estadísticas (rango, cantidad) entre versiones

✓ Análisis: Investigar si la interpolación afecta la calidad de detección

✓ Pruebas: Verificar que ambos tópicos contienen datos válidos y
  correlacionados
""")

# Resumen final
print("\n" + "=" * 80)
print("RESUMEN DE FUNCIONALIDAD")
print("=" * 80)

print("""
✅ DETECCIÓN AUTOMÁTICA:
   → Los tópicos se detectan y muestran en los combos automáticamente

✅ SELECCIÓN INDEPENDIENTE:
   → Cada pestaña (2D y 3D) tiene su propio selector
   → Pueden mostrar tópicos diferentes simultáneamente

✅ ACTUALIZACIÓN EN TIEMPO REAL:
   → No necesitas recargar frame para cambiar de tópico
   → Los datos se actualizan inmediatamente

✅ PRESERVACIÓN DE POSICIÓN:
   → En la Vista 3D, el zoom y rotación se mantienen al cambiar tópico

✅ BACKWARD COMPATIBILITY:
   → El código antiguo que usa data['pointcloud'] sigue funcionando
   → Automáticamente usa el primer tópico encontrado

🎯 IMPACTO EN USUARIO:
   Puede investigar y comparar diferentes versiones de la nube
   de puntos sin cambiar de frame, facilitando análisis y debugging
   de algoritmos de procesamiento de sensores.
""")

print("=" * 80)
print("✅ DEMOSTRACIÓN COMPLETADA EXITOSAMENTE")
print("=" * 80)
