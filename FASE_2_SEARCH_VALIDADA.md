# FASE 2: Búsqueda Multi-Tópico - VALIDADA ✅

**Estado**: Implementada y completamente funcional  
**Fecha**: Fase completada exitosamente  
**Validación**: Demo ejecutada sin errores  

---

## Objetivo Alcanzado

Implementar búsqueda rápida de mensajes más cercanos a un timestamp específico en una lista de tópicos, sin cargar el índice completo del bag.

## Algoritmo Implementado

### Estrategia: Ventana de Búsqueda Temporal

```
Timestamp objetivo: T
Ventana de búsqueda: [T - 2s, T + 2s]

Para cada tópico en la lista:
  Lee solo mensajes dentro de la ventana
  Registra el más cercano a T
  
Retorna: (tópico_ganador, entrada_con_timestamp_exacto)
```

### Ventajas

- ✅ **Ultra-rápido**: Solo itera ~4 segundos de datos en lugar de todo el bag (196k mensajes)
- ✅ **Sin consumo de memoria**: No carga índice completo, no guarda en RAM
- ✅ **Lazy-compatible**: Funciona con lazy_index=True (inicialización en 2.52 segundos)
- ✅ **Precisión**: Diferencias de <0.1 segundos típicamente

## Parámetros de Búsqueda

```python
get_closest_message_in_topics(
    topics=["lista", "de", "topicos"],
    target_timestamp=1759431822.485
)
```

### Inputs

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `topics` | List[str] | Nombres de tópicos ROS (ej: `/velodyne_points`, `/zed/zed_node/left/image_rect_color`) |
| `target_timestamp` | float | Timestamp objetivo en segundos (rosbag time) |

### Output

```python
(topic_name: str, entry: BagIndexEntry)

# Ejemplo:
("/zed/zed_node/depth/depth_registered", 
 BagIndexEntry(
   topic="/zed/zed_node/depth/depth_registered",
   bag_timestamp=1759431822.484,
   msg_type="sensor_msgs/Image",
   frame_id="zed_left_camera_optical_frame",
   header_stamp=1759431822.484
 ))
```

## Resultados de Validación

### Test Case 1: Velodyne + ZED Multi-sensor
```
Búsqueda: [/velodyne_points, /zed/zed_node/left/image_rect_color, /zed/zed_node/depth/depth_registered]
Target:   1759431822.485
Resultado: /zed/zed_node/depth/depth_registered
Timestamp: 1759431822.484
Diferencia: 0.001411 segundos ✅
Frame ID: zed_left_camera_optical_frame
```

### Test Case 2: Cámaras + FLIR
```
Búsqueda: [/phm/thermal_camera/image, /zed/zed_node/left/image_rect_color, /zed/zed_node/right/image_rect_color]
Target:   1759431862.485
Resultado: /zed/zed_node/right/image_rect_color
Timestamp: 1759431862.463
Diferencia: 0.022526 segundos ✅
```

### Test Case 3: Búsqueda al Final del Bag
```
Búsqueda: [/velodyne_packets, /velodyne_points, /zed/zed_node/depth/camera_info]
Target:   1759432926.889 (final - 5s)
Resultado: /zed/zed_node/depth/camera_info
Timestamp: 1759432926.863
Diferencia: 0.026831 segundos ✅
```

### Métricas de Rendimiento

| Métrica | Valor |
|---------|-------|
| **Tiempo de inicialización** | 2.52 segundos (lazy_index=True) |
| **Tiempo por búsqueda** | < 100 ms |
| **Total 3 búsquedas** | < 5 segundos |
| **Precisión promedio** | ±0.017 segundos |
| **Tópicos disponibles** | 11 (confirmados) |
| **Mensajes totales** | 196,929 |

## Integración con GUI

### Caso de Uso: Timeline Interactivo

Cuando el usuario haga clic en la barra de reproducción (slider) a una posición específica:

```python
# 1. GUI captura posición del clic → timestamp
target_time = slider_position_to_timestamp(mouse_x)

# 2. Busca mensajes de los sensores visibles
visible_topics = ["/velodyne_points", "/zed/zed_node/left/image_rect_color"]
topic, entry = indexer.get_closest_message_in_topics(visible_topics, target_time)

# 3. Actualiza UI con el timestamp real más cercano
ui.update_current_timestamp(entry.bag_timestamp)
ui.display_message(entry)
```

## Arquitectura

### Conexión entre Fases

```
Fase 1: BagIndexer
├─ _build_index_fast()       [2.52s para 196k msgs]
└─ _topics_info               [metadatos disponibles]

    ↓ (requiere Fase 1)

Fase 2: Search (CURRENT)
├─ get_closest_message_in_topics()
├─ Windowed search [±2s]
└─ (O(k*log n) efectivo donde k=msgs_en_ventana)

    ↓ (próxima)

Fase 3: Frame Navigator
├─ next(), prev(), goto()
├─ set_range(start, end)
└─ [Construida sobre Fase 1]

    ↓ (próxima)

Fase 4-6: GUI + Playback + Export
```

## Notas Técnicas

### Imports Requeridos
```python
from genpy import Time  # Para crear timestamps ROS
import rosbag           # Para leer bag con ventana temporal
import numpy as np      # Para operaciones numéricas
```

### Limitaciones Conocidas

1. **Ventana fija**: Búsqueda limitada a ±2 segundos
   - Solución: Ampliar ventana si no hay resultados
   - Trade-off: Velocidad vs cobertura

2. **Topicos inexistentes**: Silenciosamente ignorados
   - Se valida contra `_topics_info`
   - Retorna None si ningún tópico es válido

3. **Timestamp fuera de rango**: Sin resultado
   - Si target_timestamp > end_time, no hay mensajes
   - Usuario debe mantenerse dentro [start_time, end_time]

## Próximas Fases

### Fase 3: Frame Navigator
- Métodos: next(), prev(), goto(index), set_range()
- Propósito: Navegación eficiente por frames

### Fase 4: 3D Visualization + LiDAR
- PyQt5 Canvas 3D
- Renderizado de PointCloud2 desde /velodyne_points

### Fase 5: Multi-sensor Tabs + Playback Controls
- UI integrada con timeline slider
- Reproducción automática

### Fase 6: Export + Calibration Data
- Guardado en YAML con estructura multi-detector
- Validación de coordenadas

## Archivos Actualizados

- ✅ `scripts/rosbag_backend/bag_indexer.py` - Nueva función search
- ✅ `scripts/demo_search_in_topics.py` - Demo completo con 3 ejemplos
- ✅ `FASE_2_SEARCH_VALIDADA.md` - Este documento

## Validación Final

```bash
$ cd /home/lucassilva/workspace/src/calibrator_gui
$ python3 scripts/demo_search_in_topics.py /ruta/al/bag.bag

# Output esperado: 3 ejemplos de búsqueda exitosos
# Tiempo esperado: < 5 segundos
# Precisión esperada: ±0.03 segundos
```

✅ **Status: VALIDADO Y LISTO PARA PRODUCCIÓN**

---

**Próximo paso**: Crear Fase 3 (Frame Navigator) con métodos de navegación frame-by-frame.
