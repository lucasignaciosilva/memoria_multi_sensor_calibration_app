#!/usr/bin/env python3
"""scripts/compare_pattern_points.py
Compara dos archivos YAML (o dos entradas YAML) que contienen puntos de patrón
para medir la diferencia entre coordenadas (euclidiana) por punto.

Uso:
    python3 scripts/compare_pattern_points.py fileA.yaml fileB.yaml \
        --key "/lidar_detector/lidar_pattern" 

También puedes pasar rutas a dos archivos creados por la GUI.
"""
import sys
import argparse
import yaml
import math
from pathlib import Path


def load_points_from_yaml(path: Path, key: str):
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    # Key puede ser una ruta tipo /a/b
    parts = [p for p in key.split('/') if p]
    cur = data
    try:
        for p in parts:
            cur = cur[p]
    except Exception:
        # Intentar buscar key exacta
        cur = data.get(key, None)
    if cur is None:
        raise ValueError(f"No se encontró la clave {key} en {path}")
    # cur es una lista de frames; tomamos el primero
    if isinstance(cur, list) and len(cur) > 0:
        frame = cur[0]
    elif isinstance(cur, dict):
        frame = cur
    else:
        raise ValueError("Formato inesperado en YAML bajo la clave requerida")

    points = frame.get('points', [])
    if not points:
        # soporte formato donde points es lista de dicts con x,y,z
        raise ValueError("No se encontraron puntos en la entrada (esperado 'points')")
    # Normalizar a lista de triples
    triples = []
    for p in points:
        if isinstance(p, dict):
            x = float(p.get('x', float('nan')))
            y = float(p.get('y', float('nan')))
            z = float(p.get('z', float('nan')))
            triples.append((x, y, z))
        elif isinstance(p, (list, tuple)) and len(p) >= 3:
            triples.append((float(p[0]), float(p[1]), float(p[2])))
    return triples


def euclid(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('fileA', help='Primer archivo YAML (p. ej. velodyne export)')
    p.add_argument('fileB', help='Segundo archivo YAML (p. ej. disparity export)')
    p.add_argument('--key', default='/lidar_detector/lidar_pattern', help='Clave YAML donde están los puntos')
    args = p.parse_args()

    a = Path(args.fileA)
    b = Path(args.fileB)
    if not a.exists() or not b.exists():
        print('Uno de los archivos no existe')
        sys.exit(1)

    ptsA = load_points_from_yaml(a, args.key)
    ptsB = load_points_from_yaml(b, args.key)

    n = min(len(ptsA), len(ptsB))
    if n == 0:
        print('No hay puntos para comparar')
        sys.exit(1)

    diffs = [euclid(ptsA[i], ptsB[i]) for i in range(n)]
    print(f'Comparando {n} puntos (usando key {args.key})')
    for i, d in enumerate(diffs):
        print(f'  Punto {i+1}: diff = {d:.6f} m')
    import statistics
    print(f'  Mean: {statistics.mean(diffs):.6f} m')
    print(f'  Max:  {max(diffs):.6f} m')

if __name__ == '__main__':
    main()
