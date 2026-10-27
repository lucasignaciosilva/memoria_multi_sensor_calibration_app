#!/usr/bin/env python3
"""
Script de prueba para validar bag_indexer (Fase 1).

Ejecutar:
  python3 test_bag_indexer.py <ruta_al_rosbag>
"""

import sys
from pathlib import Path

# Agregar scripts al path
sys.path.insert(0, str(Path(__file__).parent))

from rosbag_backend import BagIndexer


def test_valid_bag(bag_path: str):
    """Test 1: Abrir bag válido y listar topics con conteo."""
    print("=" * 60)
    print("TEST 1: Abrir bag válido y listar topics")
    print("=" * 60)
    
    try:
        indexer = BagIndexer(bag_path)
        print(f"✓ Bag abierto exitosamente: {bag_path}\n")
        
        print(indexer.get_summary())
        return indexer, True
    except Exception as e:
        print(f"✗ Error al abrir bag: {e}")
        return None, False


def test_timestamps_ordered(indexer: BagIndexer) -> bool:
    """Test 2: Validar que timestamps estén ordenados."""
    print("\n" + "=" * 60)
    print("TEST 2: Validar timestamps ordenados")
    print("=" * 60)
    
    try:
        timestamps = indexer.message_timestamps
        is_ordered = all(timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1))
        
        if is_ordered:
            print(f"✓ Timestamps ordenados correctamente ({len(timestamps)} mensajes)")
            print(f"  Rango: {timestamps[0]:.3f} - {timestamps[-1]:.3f} s")
            return True
        else:
            print("✗ Timestamps NO están ordenados")
            return False
    except Exception as e:
        print(f"✗ Error validando timestamps: {e}")
        return False


def test_header_extraction(indexer: BagIndexer) -> bool:
    """Test 3: Verificar captura de header cuando existe."""
    print("\n" + "=" * 60)
    print("TEST 3: Verificar captura de header (frame_id, stamp)")
    print("=" * 60)
    
    try:
        entries_with_frame_id = [e for e in indexer._entries if e.frame_id is not None]
        entries_with_stamp = [e for e in indexer._entries if e.header_stamp is not None]
        
        print(f"✓ Entradas con frame_id: {len(entries_with_frame_id)}/{len(indexer._entries)}")
        print(f"✓ Entradas con header_stamp: {len(entries_with_stamp)}/{len(indexer._entries)}")
        
        if entries_with_frame_id:
            sample = entries_with_frame_id[0]
            print(f"\n  Ejemplo de entrada con frame_id:")
            print(f"    Topic: {sample.topic}")
            print(f"    Frame ID: {sample.frame_id}")
            print(f"    Header Stamp: {sample.header_stamp}")
        
        return True
    except Exception as e:
        print(f"✗ Error extrayendo headers: {e}")
        return False


def test_error_invalid_bag() -> bool:
    """Test 4: Probar error controlado con bag inválido."""
    print("\n" + "=" * 60)
    print("TEST 4: Error controlado con bag inválido")
    print("=" * 60)
    
    try:
        indexer = BagIndexer("/ruta/inexistente/archivo.bag")
        print("✗ No se capturó error esperado")
        return False
    except FileNotFoundError as e:
        print(f"✓ Error capturado correctamente (FileNotFoundError): {e}")
        return True
    except Exception as e:
        print(f"✗ Error inesperado: {e}")
        return False


def test_performance(bag_path: str) -> bool:
    """Test 5: Verificar rendimiento de indexación."""
    print("\n" + "=" * 60)
    print("TEST 5: Rendimiento de indexación")
    print("=" * 60)
    
    import time
    
    try:
        start = time.time()
        indexer = BagIndexer(bag_path)
        elapsed = time.time() - start
        
        print(f"✓ Indexación completada en {elapsed:.2f} segundos")
        print(f"  Mensajes/segundo: {indexer.total_messages / elapsed:.1f}")
        
        if elapsed < 5.0:
            print(f"✓ Rendimiento aceptable para bag de {indexer.total_messages} mensajes")
            return True
        else:
            print(f"⚠ Indexación lenta para bag de {indexer.total_messages} mensajes")
            return True  # No es fallo, solo advertencia
    except Exception as e:
        print(f"✗ Error en prueba de rendimiento: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 test_bag_indexer.py <ruta_al_rosbag>")
        print("\nEjemplo:")
        print("  python3 test_bag_indexer.py /ruta/mi_archivo.bag")
        sys.exit(1)
    
    bag_path = sys.argv[1]
    
    # Ejecutar pruebas
    results = {}
    
    indexer, success = test_valid_bag(bag_path)
    results["Test 1: Abrir bag"] = success
    
    if success:
        results["Test 2: Timestamps ordenados"] = test_timestamps_ordered(indexer)
        results["Test 3: Extracción de headers"] = test_header_extraction(indexer)
        results["Test 5: Rendimiento"] = test_performance(bag_path)
    
    results["Test 4: Error con bag inválido"] = test_error_invalid_bag()
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} pruebas pasadas")
    
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
