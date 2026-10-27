#!/usr/bin/env python3
"""
Demo de Fase 4: Message Loading
Demuestra carga de datos reales de sensores desde un rosbag.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rosbag_backend import BagIndexer, FrameNavigator, MessageLoader


def demo_message_loading(bag_path: str):
    """Demuestra carga de datos de sensores."""
    print("=" * 80)
    print("DEMO: Message Loading (Fase 4)")
    print("=" * 80)
    
    # Inicializar componentes
    print("\n[INICIALIZANDO] Cargando bag...")
    start = time.time()
    indexer = BagIndexer(bag_path)
    print(f"✓ BagIndexer: {time.time() - start:.2f}s")
    print(f"  Mensajes totales: {indexer.total_messages}")
    
    print("\n[INICIALIZANDO] Creando navegador...")
    nav = FrameNavigator(indexer)
    nav.set_range(0, min(1000, indexer.total_messages - 1))
    print(f"✓ FrameNavigator: rango 0-{nav.get_current_position().range_end}")
    
    print("\n[INICIALIZANDO] Creando cargador de mensajes...")
    start = time.time()
    loader = MessageLoader(indexer, nav, cache_size=30)
    print(f"✓ MessageLoader inicializado en {time.time() - start:.2f}s")
    
    # Mostrar sensores disponibles
    print("\n" + "-" * 80)
    print("SENSORES DISPONIBLES")
    print("-" * 80)
    sensors = loader.get_sensor_topics()
    if sensors:
        for sensor_type, topics in sensors.items():
            print(f"\n  {sensor_type.upper()}:")
            for topic in topics:
                msg_type = indexer._topics_info[topic].get('type', 'unknown')
                print(f"    • {topic} ({msg_type})")
    else:
        print("  ⚠ No se detectaron sensores")

    # DEMO 1: Cargar datos del frame actual
    print("\n" + "-" * 80)
    print("DEMO 1: Cargar datos del frame actual (frame 0)")
    print("-" * 80)
    
    nav.goto(0)
    start = time.time()
    frame_data = loader.get_current_frame_data()
    load_time = time.time() - start
    
    print(f"\n✓ Frame data cargado en {load_time:.3f}s")
    print(f"  Frame index: {frame_data['position'].global_index}")
    print(f"  Timestamp: {frame_data['timestamp']:.6f}")
    print(f"  Sensores disponibles: {frame_data['available_sensors']}")
    
    if frame_data['pointcloud'] is not None:
        pc = frame_data['pointcloud']
        print(f"  PointCloud: {pc.shape} {pc.dtype}")
        print(f"    X range: [{pc[:, 0].min():.2f}, {pc[:, 0].max():.2f}]")
        print(f"    Y range: [{pc[:, 1].min():.2f}, {pc[:, 1].max():.2f}]")
        print(f"    Z range: [{pc[:, 2].min():.2f}, {pc[:, 2].max():.2f}]")
    
    if frame_data['images']:
        print(f"  Imágenes: {len(frame_data['images'])} encontrada(s)")
        for topic, img in frame_data['images'].items():
            print(f"    • {topic}: {img.shape} {img.dtype}")
    
    if frame_data['imu'] is not None:
        imu = frame_data['imu']
        print(f"  IMU:")
        print(f"    Aceleración: {imu['accel']}")
        print(f"    Velocidad angular: {imu['angular_vel']}")

    # DEMO 2: Navegar con caché
    print("\n" + "-" * 80)
    print("DEMO 2: Navegación con caché inteligente")
    print("-" * 80)
    
    nav.goto(0)
    times = []
    
    for i in range(5):
        start = time.time()
        frame_data = loader.get_current_frame_data()
        elapsed = time.time() - start
        times.append(elapsed)
        
        if frame_data['pointcloud'] is not None:
            n_points = len(frame_data['pointcloud'])
        else:
            n_points = 0
        
        print(f"\n  Frame {i}: {elapsed*1000:.1f}ms (PointCloud: {n_points} pts)")
        if i < 4:
            nav.next()
    
    avg_time = sum(times) / len(times)
    print(f"\n✓ Tiempo promedio por frame: {avg_time*1000:.1f}ms")
    
    # DEMO 3: Cache info
    print("\n" + "-" * 80)
    print("DEMO 3: Información del caché")
    print("-" * 80)
    
    cache_info = loader.get_cache_info()
    print(f"\n  Tamaño cache actual: {cache_info['size']}/{cache_info['max_size']}")
    print(f"  Uso memoria (est): {cache_info['memory_usage_mb']:.1f} MB")

    # DEMO 4: Navegar a diferentes posiciones
    print("\n" + "-" * 80)
    print("DEMO 4: Saltos de navegación")
    print("-" * 80)
    
    test_positions = [50, 100, 200, 500]
    
    for pos in test_positions:
        if pos <= nav.get_current_position().range_end:
            start = time.time()
            nav.goto(pos)
            frame_data = loader.get_current_frame_data()
            elapsed = time.time() - start
            
            print(f"\n  goto({pos}): {elapsed*1000:.1f}ms")
            if frame_data['pointcloud'] is not None:
                n_points = len(frame_data['pointcloud'])
                print(f"    PointCloud: {n_points} pts")

    # DEMO 5: Prueba de todas las conversiones disponibles
    print("\n" + "-" * 80)
    print("DEMO 5: Prueba de conversiones individuales")
    print("-" * 80)
    
    nav.goto(0)
    
    # Probar PointCloud
    if 'pointcloud' in sensors:
        start = time.time()
        for topic in sensors['pointcloud']:
            pc = loader.load_pointcloud(topic)
            elapsed = time.time() - start
            if pc is not None:
                print(f"\n  PointCloud ({topic}): {elapsed*1000:.1f}ms")
                print(f"    Shape: {pc.shape}, dtype: {pc.dtype}")
            break
    
    # Probar Image
    if 'image' in sensors:
        start = time.time()
        for topic in sensors['image']:
            img = loader.load_image(topic)
            elapsed = time.time() - start
            if img is not None:
                print(f"\n  Image ({topic}): {elapsed*1000:.1f}ms")
                print(f"    Shape: {img.shape}, dtype: {img.dtype}")
            break
    
    # Probar IMU
    if 'imu' in sensors:
        start = time.time()
        for topic in sensors['imu']:
            imu = loader.load_imu(topic)
            elapsed = time.time() - start
            if imu is not None:
                print(f"\n  IMU ({topic}): {elapsed*1000:.1f}ms")
                print(f"    Accel shape: {imu['accel'].shape}")
                print(f"    Angular vel shape: {imu['angular_vel'].shape}")
            break

    # Limpiar
    print("\n" + "-" * 80)
    print("CLEANUP")
    print("-" * 80)
    loader.clear_cache()
    print("✓ Cache limpiado")

    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETADA EXITOSAMENTE")
    print("=" * 80)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python3 demo_message_loading.py <ruta_a_bag>")
        print("\nEjemplo:")
        print("  python3 demo_message_loading.py /ruta/archivo.bag")
        sys.exit(1)
    
    bag_path = sys.argv[1]
    
    if not Path(bag_path).exists():
        print(f"✗ Archivo no encontrado: {bag_path}")
        sys.exit(1)
    
    demo_message_loading(bag_path)
