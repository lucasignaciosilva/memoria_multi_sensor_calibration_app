#!/usr/bin/env python3
"""
Test Rápido de Fase 4: Message Loading
Versión optimizada con diagnóstico detallado.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rosbag_backend import BagIndexer, FrameNavigator, MessageLoader


def quick_test(bag_path: str):
    """Test rápido de message loading."""
    print("=" * 80)
    print("QUICK TEST: Message Loading (Fase 4)")
    print("=" * 80)
    
    # Paso 1: Cargar indexer
    print("\n[1/5] Cargando bag...")
    start = time.time()
    indexer = BagIndexer(bag_path)
    t1 = time.time() - start
    print(f"✓ {t1:.2f}s - {indexer.total_messages} mensajes, {len(indexer.topics())} tópicos")
    
    # Paso 2: Crear navegador
    print("\n[2/5] Creando navegador...")
    nav = FrameNavigator(indexer)
    nav.set_range(0, min(500, indexer.total_messages - 1))
    pos = nav.get_current_position()
    print(f"✓ Rango: {pos.range_start}-{pos.range_end}, Timestamp: {pos.timestamp:.6f}")
    
    # Paso 3: Crear loader
    print("\n[3/5] Creando message loader...")
    start = time.time()
    loader = MessageLoader(indexer, nav, cache_size=20)
    t3 = time.time() - start
    print(f"✓ {t3:.3f}s")
    
    sensors = loader.get_sensor_topics()
    print(f"  Sensores identificados:")
    for sensor_type, topics in sensors.items():
        print(f"    • {sensor_type}: {len(topics)} tópico(s)")
        for topic in topics[:2]:  # Mostrar primeros 2
            print(f"        - {topic}")
    
    # Paso 4: Probar carga de datos
    print("\n[4/5] Probando carga de datos...")
    
    nav.goto(0)
    pos = nav.get_current_position()
    print(f"\n  Frame 0 (timestamp: {pos.timestamp:.6f})")
    
    # Intentar cargar cada tipo de sensor
    test_results = {
        'pointcloud': None,
        'image': None,
        'imu': None,
    }
    
    # PointCloud
    if 'pointcloud' in sensors:
        topic = sensors['pointcloud'][0]
        print(f"\n  → Cargando PointCloud desde {topic}")
        start = time.time()
        pc = loader.load_pointcloud(topic)
        elapsed = time.time() - start
        if pc is not None:
            print(f"    ✓ {elapsed*1000:.1f}ms, shape: {pc.shape}, dtype: {pc.dtype}")
            test_results['pointcloud'] = pc
        else:
            print(f"    ✗ Retornó None en {elapsed*1000:.1f}ms")
    
    # Image
    if 'image' in sensors:
        topic = sensors['image'][0]
        print(f"\n  → Cargando Image desde {topic}")
        start = time.time()
        img = loader.load_image(topic)
        elapsed = time.time() - start
        if img is not None:
            print(f"    ✓ {elapsed*1000:.1f}ms, shape: {img.shape}, dtype: {img.dtype}")
            test_results['image'] = img
        else:
            print(f"    ✗ Retornó None en {elapsed*1000:.1f}ms")
    
    # IMU
    if 'imu' in sensors:
        topic = sensors['imu'][0]
        print(f"\n  → Cargando IMU desde {topic}")
        start = time.time()
        imu = loader.load_imu(topic)
        elapsed = time.time() - start
        if imu is not None:
            print(f"    ✓ {elapsed*1000:.1f}ms, accel shape: {imu['accel'].shape}")
            test_results['imu'] = imu
        else:
            print(f"    ✗ Retornó None en {elapsed*1000:.1f}ms")
    
    # Paso 5: Resumen
    print("\n[5/5] RESUMEN")
    print("-" * 80)
    
    successful = sum(1 for v in test_results.values() if v is not None)
    
    print(f"\n✓ Cargas exitosas: {successful}")
    if test_results['pointcloud'] is not None:
        print(f"  • PointCloud: {len(test_results['pointcloud'])} puntos")
    if test_results['image'] is not None:
        print(f"  • Imagen: {test_results['image'].shape}")
    if test_results['imu'] is not None:
        print(f"  • IMU: {test_results['imu']['accel']}")
    
    print("\n" + "=" * 80)
    if successful > 0:
        print(f"✅ TEST EXITOSO - {successful} sensor(es) cargados correctamente")
    else:
        print("⚠ TEST PARCIAL - Los sensores se detectaron pero no se cargaron datos")
    print("=" * 80)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python3 test_message_loading_quick.py <ruta_a_bag>")
        sys.exit(1)
    
    bag_path = sys.argv[1]
    if not Path(bag_path).exists():
        print(f"✗ Archivo no encontrado: {bag_path}")
        sys.exit(1)
    
    quick_test(bag_path)
