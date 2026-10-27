# Fase 1 - Infraestructura mínima de rosbag

## Entregables

### 1. Módulo `rosbag_backend/bag_indexer.py`

Indexador eficiente que construye metadatos sin cargar mensajes completos en memoria.

**Clase: `BagIndexer`**
- Abre un rosbag y crea un índice de metadatos en una sola pasada.
- Proporciona acceso rápido por topic, rango temporal, frame_id, etc.
- Manejo robusto de errores (archivo inexistente, bag corrupto, etc.).

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

# Abrir bag
indexer = BagIndexer("/ruta/mi_archivo.bag")

# Consultas
topics = indexer.topics()  # lista de topics
entries = indexer.messages_for_topic("/velodyne_points")  # mensajes de un topic
entries_in_range = indexer.entries_in_range(start_ts, end_ts)  # por rango temporal
summary = indexer.get_summary()  # resumen textual
timestamps = indexer.message_timestamps  # numpy array de timestamps
```

### 2. Script de prueba `test_bag_indexer.py`

Valida los 5 criterios de la Fase 1:

1. **Test 1**: Abrir bag válido y listar topics con conteo.
2. **Test 2**: Validar que timestamps estén ordenados.
3. **Test 3**: Verificar captura de header (`frame_id`, `stamp`).
4. **Test 4**: Probar error controlado con bag inválido.
5. **Test 5**: Medir rendimiento de indexación.

**Ejecutar:**
```bash
python3 scripts/test_bag_indexer.py /ruta/al/archivo.bag
```

## Estructura del proyecto (después de Fase 1)

```
scripts/
  ├── calibrator_gui.py          (GUI principal)
  ├── test_bag_indexer.py        (pruebas de Fase 1)
  └── rosbag_backend/
      ├── __init__.py
      └── bag_indexer.py         (indexador de metadatos)
```

## Criterio de salida (Fase 1)

✅ Generar resumen de índice en consola en menos de 5 segundos para bags medianos.
✅ Manejar errores robustamente (archivo inexistente, bag corrupto).
✅ Indexar metadatos: topics, timestamps, frame_id, header.stamp.
✅ Proporcionar API simple para consultas por topic y rango temporal.

## Próximos pasos

Con Fase 1 completa y validada, puedes:
- Conectar el indexador a la GUI de PyQt5 en calibrator_gui.py.
- Implementar Fase 2 (navegación de frames).
- Crear módulo `message_loader.py` para cargar mensajes bajo demanda.
