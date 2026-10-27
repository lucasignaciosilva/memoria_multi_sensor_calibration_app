#!/usr/bin/env python3
"""
Ejemplo de uso: Navegación por frames usando FrameNavigator.
"""

import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

from rosbag_backend import BagIndexer
from rosbag_backend.frame_navigator import FrameNavigator


def demo_frame_navigation(bag_path: str):
    """Demuestra navegación de frames."""
    print("=" * 70)
    print("DEMO: Navegación de Frames")
    print("=" * 70)
    
    # Inicializar indexer
    print("\n[INICIALIZANDO] Cargando bag...")
    indexer = BagIndexer(bag_path)
    print(f"✓ Bag cargado: {Path(bag_path).name}")
    print(f"✓ Mensajes totales: {indexer.total_messages}")
    print(f"✓ Duración: {indexer._info['duration']:.2f} segundos")
    
    # Crear navegador
    nav = FrameNavigator(indexer)
    print(f"\n✓ Navigator inicializado")
    
    # DEMO 1: Configurar rango reducido
    print("\n" + "-" * 70)
    print("DEMO 1: Establecer rango 0-1000")
    print("-" * 70)
    
    nav.set_range(0, 1000)
    pos = nav.get_current_position()
    print(f"\n✓ Rango actual: [{pos.range_start}, {pos.range_end}]")
    print(f"✓ Mensajes en rango: {pos.message_count}")
    print(f"✓ Posición actual: {pos.global_index}/{pos.message_count}")
    print(f"✓ Progreso: {nav.get_progress_percent():.1f}%")
    
    # DEMO 2: Navegar forward
    print("\n" + "-" * 70)
    print("DEMO 2: Navegar hacia adelante (next x 5)")
    print("-" * 70)
    
    for i in range(5):
        nav.next()
        print(f"  Frame {i+1}: índice={nav.current_index}, progreso={nav.get_progress_percent():.1f}%")
    
    # DEMO 3: Navegar backward (fast)
    print("\n" + "-" * 70)
    print("DEMO 3: Navegar hacia atrás (prev x 3)")
    print("-" * 70)
    print("  (Omitido para acelerar demo)")
    
    # DEMO 4: Saltar a índice específico
    print("\n" + "-" * 70)
    print("DEMO 4: Saltar a índice 500")
    print("-" * 70)
    
    nav.goto(500)
    print(f"✓ Saltó a índice {nav.current_index}")
    print(f"  Progreso: {nav.get_progress_percent():.1f}%")
    
    # DEMO 5: Saltar a porcentaje
    print("\n" + "-" * 70)
    print("DEMO 5: Saltar al 50% del rango")
    print("-" * 70)
    
    nav.jump_to_percent(50.0)
    print(f"✓ Saltó al 50%: índice={nav.current_index}, progreso={nav.get_progress_percent():.1f}%")
    
    # DEMO 6: Búsqueda por timestamp
    print("\n" + "-" * 70)
    print("DEMO 6: Buscar por timestamp")
    print("-" * 70)
    
    mid_time = indexer._info['start_time'] + (indexer._info['duration'] / 2)
    print(f"✓ Buscando timestamp: {mid_time:.3f}")
    
    entry = nav.goto_by_timestamp(mid_time)
    if entry:
        print(f"  Encontrado: índice={nav.current_index}, ts={entry.bag_timestamp:.3f}, diff={(entry.bag_timestamp - mid_time):.6f}s")
    
    # DEMO 7: Expandir rango
    print("\n" + "-" * 70)
    print("DEMO 7: Expandir rango a 0-10000")
    print("-" * 70)
    
    nav.set_range(0, min(10000, indexer.total_messages - 1))
    print(f"✓ Nuevo rango: [{nav.range_start}, {nav.range_end}], mensajes={nav.range_end - nav.range_start + 1}")
    
    # DEMO 8: Error handling - índice fuera de rango
    print("\n" + "-" * 70)
    print("DEMO 8: Validación de rangos")
    print("-" * 70)
    
    try:
        nav.goto(20000)
        print("✗ Debería haber lanzado excepción")
    except ValueError as e:
        print(f"✓ Excepción capturada (esperado)")
    
    print("\n" + "=" * 70)
    print("DEMO COMPLETADO ✓")
    print("=" * 70)


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 demo_frame_navigation.py <ruta_al_rosbag>")
        print("\nEjemplo:")
        print("  python3 demo_frame_navigation.py /ruta/mi_archivo.bag")
        sys.exit(1)
    
    bag_path = sys.argv[1]
    demo_frame_navigation(bag_path)


if __name__ == "__main__":
    main()
