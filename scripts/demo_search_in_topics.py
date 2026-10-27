#!/usr/bin/env python3
"""
Ejemplo de uso: Buscar el mensaje más cercano a un timestamp 
en una lista de tópicos específicos.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rosbag_backend import BagIndexer


def demo_search_in_topics(bag_path: str):
    """Demuestra búsqueda de mensajes en una lista de tópicos."""
    print("=" * 70)
    print("DEMO: Búsqueda en lista de tópicos + timestamp")
    print("=" * 70)
    
    # Abrir bag (lazy_index=True por defecto, rápido)
    print("\n[INICIALIZANDO] Cargando metadatos...")
    indexer = BagIndexer(bag_path)  # lazy_index=True
    print(f"✓ Bag cargado: {Path(bag_path).name}")
    print(f"✓ Mensajes totales: {indexer.total_messages}")
    
    # Listar todos los topics disponibles
    print("\n" + "-" * 70)
    print("TOPICS DISPONIBLES:")
    print("-" * 70)
    all_topics = indexer.topics()
    for i, topic in enumerate(all_topics, 1):
        info = indexer._topics_info[topic]
        print(f"  {i}. {topic}")
        print(f"     Tipo: {info['type']}, Mensajes: {info['message_count']}")
    
    # Ejemplo 1: Buscar en lista específica de tópicos
    print("\n" + "-" * 70)
    print("EJEMPLO 1: Buscar en lista de tópicos Velodyne + ZED")
    print("-" * 70)
    
    search_topics_1 = [
        "/velodyne_points",
        "/zed/zed_node/left/image_rect_color",
        "/zed/zed_node/depth/depth_registered"
    ]
    
    target_time_1 = indexer._info['start_time'] + 10.0
    
    print(f"\n✓ Parámetros de búsqueda:")
    print(f"  Tópicos: {search_topics_1}")
    print(f"  Timestamp objetivo: {target_time_1:.3f}")
    
    result1 = indexer.get_closest_message_in_topics(
        search_topics_1,
        target_time_1
    )
    
    if result1:
        topic, entry = result1
        print(f"\n✓ RESULTADO:")
        print(f"  Tópico ganador: {topic}")
        print(f"  Timestamp real: {entry.bag_timestamp:.3f}")
        print(f"  Diferencia: {abs(entry.bag_timestamp - target_time_1):.6f} segundos")
        print(f"  Frame ID: {entry.frame_id}")
    else:
        print("✗ No se encontró mensaje")
    
    # Ejemplo 2: Buscar en lista de cámaras térmicas
    print("\n" + "-" * 70)
    print("EJEMPLO 2: Buscar en lista de cámaras + FLIR")
    print("-" * 70)
    
    search_topics_2 = [
        "/phm/thermal_camera/image",
        "/zed/zed_node/left/image_rect_color",
        "/zed/zed_node/right/image_rect_color"
    ]
    
    target_time_2 = indexer._info['start_time'] + 50.0
    
    print(f"\n✓ Parámetros de búsqueda:")
    print(f"  Tópicos: {search_topics_2}")
    print(f"  Timestamp objetivo: {target_time_2:.3f}")
    
    result2 = indexer.get_closest_message_in_topics(
        search_topics_2,
        target_time_2
    )
    
    if result2:
        topic, entry = result2
        print(f"\n✓ RESULTADO:")
        print(f"  Tópico ganador: {topic}")
        print(f"  Timestamp real: {entry.bag_timestamp:.3f}")
        print(f"  Diferencia: {abs(entry.bag_timestamp - target_time_2):.6f} segundos")
    else:
        print("✗ No se encontró mensaje")
    
    # Ejemplo 3: Buscar al final del bag
    print("\n" + "-" * 70)
    print("EJEMPLO 3: Buscar al final del bag (Near end)")
    print("-" * 70)
    
    search_topics_3 = [
        "/velodyne_packets",
        "/velodyne_points",
        "/zed/zed_node/depth/camera_info"
    ]
    
    target_time_3 = indexer._info['end_time'] - 5.0
    
    print(f"\n✓ Parámetros de búsqueda:")
    print(f"  Tópicos: {search_topics_3}")
    print(f"  Timestamp objetivo: {target_time_3:.3f}")
    
    result3 = indexer.get_closest_message_in_topics(
        search_topics_3,
        target_time_3
    )
    
    if result3:
        topic, entry = result3
        print(f"\n✓ RESULTADO:")
        print(f"  Tópico ganador: {topic}")
        print(f"  Timestamp real: {entry.bag_timestamp:.3f}")
        print(f"  Diferencia: {abs(entry.bag_timestamp - target_time_3):.6f} segundos")
    else:
        print("✗ No se encontró mensaje")


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 demo_search_in_topics.py <ruta_al_rosbag>")
        print("\nEjemplo:")
        print("  python3 demo_search_in_topics.py /ruta/mi_archivo.bag")
        sys.exit(1)
    
    bag_path = sys.argv[1]
    demo_search_in_topics(bag_path)


if __name__ == "__main__":
    main()

