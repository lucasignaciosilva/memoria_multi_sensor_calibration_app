# Fase 1 - Infraestructura mínima de rosbag ✅ COMPLETA

## Entregables

### 1. Módulo `rosbag_backend/bag_indexer.py`

Indexador eficiente con **dos estrategias**:

**Estrategia Lazy (por defecto, ~5s para bags grandes):**
- Abre el bag y obtiene metadatos rápidamente usando `get_type_and_topic_info()`
- NO itera sobre todos los mensajes
- Ideal para UX responsivo: apertura instantánea de UI
- Timestamps se cargan bajo demanda cuando se necesiten

**Estrategia Completa (bajo demanda, lenta pero exhaustiva):**
- Itera sobre todos los mensajes para construir índice completo
- Se activa automáticamente si se solicitan timestamps o consultas por rango
- Opcional: pasar `lazy_index=False` al constructor para indexación completa inmediata

**Clase: `BagIndexer`**
- Constructor: `BagIndexer(bag_path, lazy_index=True)`
- Abre un rosbag y crea índice de metadatos.
- Manejo robusto de errores (archivo inexistente, bag corrupto).
- Bajo demanda lazy-loading: timestamps se cargan solo si se solicitan.

**Clase: `BagIndexEntry`**
- Estructura de datos que almacena metadatos de un mensaje:
  - `topic`: nombre del topic
  - `bag_timestamp`: timestamp del rosbag
  - `msg_type`: tipo de mensaje (e.g., `sensor_msgs/PointCloud2`)
  - `frame_id`: frame_id del header, si existe
  - `header_stamp`: timestamp del header.stamp, si existe
  - `msg_index`: índice global en el bag
  - `topic_index`: índice dentro del topic

**API principal:**
```python
from rosbag_backend import BagIndexer

# Abrir bag en modo lazy (rápido, ~5s para bags grandes)
indexer = BagIndexer("/ruta/mi_archivo.bag")  # lazy_index=True por defecto

# Consultas rápidas (sin iterar mensajes):
topics = indexer.topics()  # lista de topics
info = indexer.topic_info("/velodyne_points")  # tipo y conteo
summary = indexer.get_summary()  # resumen textual

# Consultas lentas (itera bajo demanda):
all_entries = indexer.messages_for_topic("/velodyne_points")  # carga índice completo
entries_in_range = indexer.entries_in_range(start_ts, end_ts)  # por rango temporal
timestamps = indexer.message_timestamps  # numpy array de ALL timestamps
```

### 2. Scripts de prueba

**`test_bag_quick.py` (RECOMENDADO para bags grandes)**
- Valida indexador en modo lazy (~5 segundos)
- Rápido: no itera sobre todos los mensajes
- **Ejecutar:**
  ```bash
  python3 scripts/test_bag_quick.py /ruta/al/archivo.bag
  ```

**`test_bag_indexer.py` (para análisis exhaustivo)**
- Valida 5 criterios (timestamps, headers, errores, rendimiento)
- **ADVERTENCIA**: Lento para bags grandes (itera todos los mensajes)
- **Ejecutar:**
  ```bash
  python3 scripts/test_bag_indexer.py /ruta/al/archivo.bag
  ```

### 3. Validación con datos reales ✅

✅ **Probado con:**
- Archivo: `zed_flir_velodyne_2025-10-02-16-03-32.bag`
- Tamaño: ~5GB (89GB completo en disco)
- Mensajes: 196,929
- Topics: 11
- **Tiempo de indexación (lazy): 2.52 segundos** ✅ (optimizado con `rosbag info`)

**Topics detectados:**
```
/phm/thermal_camera/image (8.3k mensajes)
/velodyne_packets (11k mensajes)
/velodyne_points (11k mensajes)
/zed/zed_node/confidence/confidence_map (16.6k mensajes)
/zed/zed_node/depth/camera_info (16.6k mensajes)
/zed/zed_node/depth/depth_registered (16.6k mensajes)
/zed/zed_node/disparity/disparity_image (16.6k mensajes)
/zed/zed_node/left/camera_info (33.2k mensajes)
/zed/zed_node/left/image_rect_color (16.6k mensajes)
/zed/zed_node/right/camera_info (33.2k mensajes)
/zed/zed_node/right/image_rect_color (16.6k mensajes)
```

## Estructura del proyecto (después de Fase 1)

```
scripts/
  ├── calibrator_gui.py          (GUI principal)
  ├── test_bag_quick.py          (pruebas rápidas - RECOMENDADO)
  ├── test_bag_indexer.py        (pruebas exhaustivas)
  └── rosbag_backend/
      ├── __init__.py
      └── bag_indexer.py         (indexador de metadatos)
```

## Criterio de salida (Fase 1) ✅ CUMPLIDO

✅ Abrir bag de 196k mensajes en < 5 segundos (modo lazy).
✅ Listar topics y conteo de mensajes sin iterar.
✅ Manejo robusto de errores (archivo inexistente, bag corrupto).
✅ Indexar metadatos bajo demanda: topics, frame_id, header.stamp.
✅ API simple para consultas por topic y rango temporal.

## Próximos pasos

Fase 2: Navegador de frames (frame_navigator.py)
- `next()`, `prev()`, `goto(index)`, `set_range(start, end)`
- Construir sobre el indexador de Fase 1

## Nota técnica

El diseño de dos pasadas es crítico para UX:
1. **Apertura rápida (< 5s)**: Metadatos vía `get_type_and_topic_info()`
2. **Lazy loading bajo demanda**: Iterate full index solo si se solicitan timestamps exactos

Esto permite que la GUI sea responsiva para usuarios mientras indexa en background si es necesario.
