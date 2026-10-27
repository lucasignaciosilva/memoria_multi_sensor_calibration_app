#!/usr/bin/env python3
"""
Test de diagnósticos - ver qué está pasando con frame counter y tópicos
"""
import sys
sys.path.insert(0, 'scripts')

import glob
from pathlib import Path

# Buscar un bag
bags = []
try:
    # Buscar en /tmp primero
    bags = glob.glob('/tmp/**/*.bag', recursive=True)
    if not bags:
        bags = glob.glob('/home/**/*.bag', recursive=True)[:1]
except:
    pass

if not bags:
    print("❌ No se encontró ningún bag para testing")
    print("   Busca manualmente un .bag y ejecuta:")
    print("   python3 test_diagnostics.py /ruta/al/archivo.bag")
    sys.exit(1)

bag_file = bags[0]
print(f"✅ Usando bag: {bag_file}")

try:
    from rosbag_backend import BagIndexer, FrameNavigator, MessageLoader
    
    # Cargar
    indexer = BagIndexer(bag_file)
    nav = FrameNavigator(indexer)
    loader = MessageLoader(indexer, nav)
    
    print(f"\n📊 FRAME COUNTER TEST:")
    print(f"   Total messages: {indexer.total_messages}")
    print(f"   Max allowed index: {indexer.total_messages - 1}")
    print(f"   Navegator range_end: {nav.range_end}")
    
    # Ir al último frame
    nav.goto(indexer.total_messages - 1)
    print(f"   Current index after goto(max): {nav.current_index}")
    
    pos = nav.get_current_position()
    current_idx = pos.global_index
    total = indexer.total_messages
    display_frame = f"Frame: {current_idx + 1}/{total}"
    print(f"   Display: {display_frame}")
    print(f"   ✓ Correcto" if current_idx + 1 <= total else f"   ✗ ERROR: {current_idx + 1} > {total}")
    
    print(f"\n🎥 TOPIC DETECTION TEST:")
    
    # Cargar datos del primer frame
    nav.goto(0)
    data = loader.get_current_frame_data()
    
    print(f"   Data keys: {list(data.keys())}")
    
    rgb_topics = []
    thermal_topics = []
    lidar_topics = []
    
    if 'images' in data and data['images']:
        print(f"   ✓ 'images' encontrada con {len(data['images'])} tópicos")
        for topic in data['images'].keys():
            if 'thermal' in topic.lower() or 'flir' in topic.lower():
                thermal_topics.append(topic)
            else:
                rgb_topics.append(topic)
        print(f"     - RGB: {rgb_topics}")
        print(f"     - Thermal: {thermal_topics}")
    else:
        print(f"   ✗ 'images' no encontrada o vacía")
    
    if 'pointclouds' in data and data['pointclouds']:
        lidar_topics = list(data['pointclouds'].keys())
        print(f"   ✓ 'pointclouds' encontrada: {lidar_topics}")
    elif 'pointcloud' in data and data['pointcloud'] is not None:
        print(f"   ✓ 'pointcloud' encontrada")
        lidar_topics = ["PointCloud2"]
    else:
        print(f"   ✗ LiDAR no encontrado")
    
    print(f"\n   RESUMEN:")
    print(f"   RGB topics: {len(rgb_topics)}")
    print(f"   Thermal topics: {len(thermal_topics)}")
    print(f"   LiDAR topics: {len(lidar_topics)}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
