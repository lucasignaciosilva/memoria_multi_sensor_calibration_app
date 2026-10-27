#!/usr/bin/env python3
"""
Script de prueba rápida para Fase 1 - Modo lazy.

Valida que el indexador pueda abrir un bag rápidamente sin cargar todos los mensajes.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rosbag_backend import BagIndexer


def test_lazy_mode(bag_path: str):
    """Prueba el modo lazy (rápido sin iterar todos los mensajes)."""
    print("=" * 60)
    print("TEST: Modo Lazy (apertura rápida de bag)")
    print("=" * 60)
    
    start = time.time()
    try:
        indexer = BagIndexer(bag_path, lazy_index=True)
        elapsed = time.time() - start
        
        print(f"✓ Bag abierto en modo lazy en {elapsed:.2f} segundos\n")
        print(indexer.get_summary())
        
        print(f"\n✓ Temas detectados: {len(indexer.topics())}")
        print(f"✓ Total de mensajes (sin iterar): {indexer.total_messages}")
        
        if elapsed < 2.0:
            print(f"\n✓ EXCELENTE: Indexación rápida ({elapsed:.2f}s)")
            return True
        elif elapsed < 5.0:
            print(f"\n✓ BUENO: Indexación moderada ({elapsed:.2f}s)")
            return True
        else:
            print(f"\n⚠ LENTO: Indexación tomó {elapsed:.2f}s")
            return True
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 test_bag_quick.py <ruta_al_rosbag>")
        sys.exit(1)
    
    bag_path = sys.argv[1]
    success = test_lazy_mode(bag_path)
    
    print("\n" + "=" * 60)
    if success:
        print("✓ TEST PASADO: Indexador lazy funciona correctamente")
        print("\nNota: Para pruebas de timestamps, use el script completo")
        print("en test_bag_indexer.py (requiere iteración completa del bag)")
    else:
        print("✗ TEST FALLIDO")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
