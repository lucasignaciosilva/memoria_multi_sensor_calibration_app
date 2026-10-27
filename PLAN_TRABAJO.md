# Plan de Trabajo Incremental - Visor Interactivo de Rosbag 3D

## Objetivo Inicial (Prioridad Alta)
Lograr un MVP que:
- lea un archivo rosbag,
- permita navegar por frames,
- y visualice los datos de forma simple y verificable.

## Estrategia de Eficiencia (Primero metadatos, luego carga bajo demanda)

### Idea central
Separar el flujo en dos capas:
1. **Indexado rapido de metadatos** (una sola pasada):
   - topic
   - timestamp del mensaje en bag
   - timestamp/header del mensaje (si existe)
   - tipo de mensaje
   - `frame_id` del header (si existe)
   - posicion de mensaje para acceso posterior (offset o indice interno)
2. **Lectura on-demand de payload**:
   - solo cargar y parsear el mensaje completo cuando el usuario selecciona ese frame/topic.

### Beneficios
- arranque rapido de la UI aunque el bag sea grande,
- menos uso de RAM,
- navegación fluida por timeline,
- facilita filtros por topic y rango temporal sin reprocesar todo.

## Fase 1 - Infraestructura minima de rosbag

### Entregables
- `bag_indexer.py` (o modulo equivalente): construye indice de metadatos.
- estructura de datos de indice (por topic y por frame global).
- manejo robusto de errores (archivo inexistente/corrupto/topic vacio).

### Pruebas intermedias
1. Abrir bag valido y listar topics con conteo de mensajes.
2. Validar que timestamps estén ordenados.
3. Verificar captura de header cuando existe (`frame_id`, `stamp`).
4. Probar error controlado con bag invalido.

### Criterio de salida
- generar un resumen de indice en consola/UI en menos de unos segundos para bags medianos.

## Fase 2 - Navegación de frames sobre el indice

### Entregables
- `frame_navigator.py` (o componente equivalente):
  - `next()`, `prev()`, `goto(i)`
  - `set_range(start, end)`
  - consulta por topic activo
- sincronización con timeline (frame actual / total).

### Pruebas intermedias
1. Navegación secuencial sin saltos incorrectos.
2. `goto` fuera de rango responde con validación, no con crash.
3. Rango (`start < end`) aplicado correctamente.
4. Cambio de topic reutiliza indice sin reindexar bag.

### Criterio de salida
- navegación estable en indice completo sin cargar payload completo en memoria.

## Fase 3 - Visualización MVP 3D LiDAR en Qt (primera visual útil)

### Entregables
- vista 3D inicial para topic LiDAR en Qt (nube de puntos en espacio XYZ).
- controles base de camara 3D (orbita/rotacion, zoom y paneo).
- panel de estado con:
  - topic
  - timestamp bag/header
  - frame_id
  - cantidad de puntos
- carga lazy del mensaje al cambiar de frame.

### Pruebas intermedias
1. Cambiar frame actualiza visualización.
2. La nube se visualiza en 3D con ejes de referencia y transformacion consistente.
3. Frames vacíos se muestran sin error.
4. Rendimiento aceptable al recorrer 100+ frames.
5. Cambio de topic no bloquea la UI.

### Criterio de salida
- demo funcional: abrir bag -> elegir topic -> navegar frames -> ver nube LiDAR en 3D.

## Fase 4 - Controles de reproducción y UX

### Entregables
- slider timeline + botones `prev/next/play/pause`.
- reproducción con timer respetando rango activo.
- estado visual: `frame X / N`.

### Pruebas intermedias
1. Play avanza y se detiene al final del rango.
2. Pause conserva frame actual.
3. Slider y teclado permanecen sincronizados.

## Fase 5 - Integración de pestañas de sensores

### Entregables
- pestaña LiDAR funcional completa.
- pestañas Camara/IMU/GPS/3D conectadas al indice de metadatos (aunque inicialmente con vista simplificada).
- carga por demanda por topic.

### Pruebas intermedias
1. Cambiar pestaña conserva estado global de navegación.
2. Cada pestaña muestra metadata correcta del topic.
3. Sin reindexado completo al cambiar pestaña.

## Fase 6 - Exportación YAML (formato objetivo del proyecto)

### Entregables
- exportador YAML compatible con estructura definida en `claude.md`.
- soporte para puntos reales en LiDAR y `.nan` en detectores sin dato.

### Pruebas intermedias
1. YAML se genera con estructura valida.
2. Se puede volver a cargar/parsear sin errores.
3. Repetir export para múltiples frames conserva consistencia.

## Arquitectura propuesta (modular)
- `rosbag_indexer.py`: indexado de metadatos.
- `message_loader.py`: carga de payload bajo demanda.
- `frame_navigator.py`: lógica de navegación y rango.
- `sensor_adapters/`: adaptadores por tipo de topic (PointCloud2, Image, IMU, GPS).
- `ui/`: componentes PyQt5 (timeline, tabs, panel estado, canvas).
- `exporters/yaml_exporter.py`: persistencia final.

## Plan de pruebas por sprint

### Sprint 1 (MVP minimo)
- Fase 1 + Fase 2 + visualización 3D inicial de Fase 3.
- Meta: ya navegar y visualizar algo real del bag.

### Sprint 2
- completar UX de Fase 4 y robustecer Fase 3.

### Sprint 3
- pestañas multi-sensor + exportación YAML.

## Riesgos y mitigaciones
- Bags muy grandes: usar indice ligero + lazy loading + cache LRU de mensajes.
- UI bloqueada por lectura: mover carga pesada a worker thread.
- Inconsistencia de headers entre topics: fallback a timestamp de bag cuando no exista `header.stamp`.

## Definición de "Hecho" para la primera entrega
- Se abre un rosbag.
- Se listan topics y metadatos principales.
- Se navega por frames con controles basicos.
- Se visualiza LiDAR (al menos en 2D) frame a frame.
- No hay bloqueos ni crashes en casos comunes.
