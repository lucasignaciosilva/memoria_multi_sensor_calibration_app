#!/usr/bin/env python3
"""
Script de diagnóstico: Muestra todos los tópicos de LiDAR disponibles en el rosbag
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

import rosbag

def diagnosticar_bag(bag_path):
    """Diagnostica tópicos disponibles en un rosbag."""
    
    print("\n" + "=" * 80)
    print(f"DIAGNÓSTICO DE ROSBAG: {bag_path}")
    print("=" * 80)
    
    try:
        bag = rosbag.Bag(bag_path)
    except Exception as e:
        print(f"❌ ERROR: No se puede abrir el rosbag: {e}")
        return
    
    print(f"\n📊 Información general:")
    print(f"   Total de mensajes: {bag.get_message_count()}")
    print(f"   Duración: {(bag.get_end_time() - bag.get_start_time()):.2f} segundos")
    
    # Obtener todos los tópicos
    all_topics = bag.get_type_and_message_count()
    
    print(f"\n📋 Todos los tópicos en el bag:")
    print("   " + "-" * 76)
    
    lidar_topics = []
    for topic, (msg_type, count) in sorted(all_topics.items()):
        print(f"   {topic:40} | {msg_type:30} | {count:5} msgs")
        
        # Detectar tópicos de LiDAR
        if 'PointCloud2' in msg_type or 'velodyne' in topic.lower():
            lidar_topics.append(topic)
    
    print("   " + "-" * 76)
    
    # Resumen de tópicos LiDAR
    print(f"\n🎯 Tópicos de LiDAR (PointCloud2) disponibles:")
    if lidar_topics:
        for topic in lidar_topics:
            count = all_topics[topic][1]
            print(f"   ✅ {topic:50} ({count} mensajes)")
    else:
        print(f"   ❌ No se encontraron tópicos de LiDAR")
    
    bag.close()
    
    print("\n" + "=" * 80)
    if lidar_topics:
        print(f"📝 Resumen: Se encontraron {len(lidar_topics)} tópico(s) de LiDAR")
        print("\n💡 Notas:")
        print("   - El selector mostrará SOLO estos tópicos")
        print("   - Si esperas más tópicos, verifica que el rosbag sea correcto")
        print("   - Puedes tener rosbags diferentes con tópicos distintos")
    else:
        print("⚠️  ADVERTENCIA: No hay tópicos de LiDAR en este rosbag")
        print("   - Verifica que estés abriendo el rosbag correcto")
        print("   - Si es intencional, necesitarás un rosbag con datos de LiDAR")
    
    print("=" * 80 + "\n")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        bag_path = sys.argv[1]
    else:
        # Buscar rosbag en ubicaciones comunes
        common_paths = [
            '/home/lucassilva/Downloads',
            '/home/lucassilva/workspace',
            '.',
        ]
        
        bag_path = None
        for base_path in common_paths:
            path_obj = Path(base_path)
            bags = list(path_obj.rglob('*.bag'))
            if bags:
                # Tomar el primer bag encontrado
                bag_path = str(bags[0])
                break
        
        if not bag_path:
            print("\n❌ ERROR: No se encontró archivo .bag")
            print("\n📝 Uso:")
            print("   python3 diagnostico_topicos.py <ruta/al/archivo.bag>")
            print("\nEjemplo:")
            print("   python3 diagnostico_topicos.py ~/Downloads/mi_rosbag.bag")
            sys.exit(1)
    
    diagnosticar_bag(bag_path)
