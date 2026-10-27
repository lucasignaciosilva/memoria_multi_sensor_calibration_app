# Visor Interactivo de Rosbag 3D - Proyecto de Calibración

**Estado del Proyecto**: 50% completado (Fases 1-3 de 6)  
**Última actualización**: Sesión actual  
**Lenguaje**: Python 3 + PyQt5  
**Plataforma**: ROS + rosbag  

---

## 📋 Descripción General

Aplicación de escritorio interactiva para visualizar, navegar y analizar datos de archivos rosbag en tiempo real. Diseñada específicamente para calibración de sensores multi-modal (LiDAR, Cámaras RGB, Cámara térmica, IMU) con interfaz 3D interactiva.

**Casos de uso principales**:
- Análisis de trayectorias de objetos detectados
- Calibración de sensores (alignment, timestamps)
- Validación de algoritmos de detección multi-sensor
- Generación de datasets etiquetados con coordenadas calibradas

---

## 🎯 Características Implementadas

### ✅ Fase 1: Indexación Rápida (VALIDADA)
- Carga de metadatos en 2.52 segundos (vs 97s original)
- Soporte para modo lazy (sin iterar mensajes)
- Detección automática de todos los tópicos
- Información de tipos y conteos

```python
indexer = BagIndexer('archivo.bag')  # 2.52s
print(f"Tópicos: {indexer.topics()}")  # 11 tópicos
print(f"Mensajes: {indexer.total_messages}")  # 196,929
```

### ✅ Fase 2: Búsqueda Multi-Tópico (VALIDADA)
- Búsqueda eficiente en lista de tópicos específicos
- Windowed search (±2s) evita cargar todo el bag
- Precisión: ±0.02 segundos típicamente
- Tiempo: <100ms por búsqueda

```python
topic, entry = indexer.get_closest_message_in_topics(
    ['/velodyne_points', '/camera/image'],
    1759431822.485  # timestamp objetivo
)
```

### ✅ Fase 3: Navegación Eficiente (VALIDADA)
- Operaciones O(1) para navegación frame-a-frame
- Rango configurable independiente
- Saltos directos o por porcentaje
- Integración con búsqueda por timestamp

```python
nav = FrameNavigator(indexer)
nav.set_range(0, 10000)
nav.next()
nav.goto(500)
nav.jump_to_percent(50.0)
progress = nav.get_progress_percent()  # 50.0%
```

---

## 📁 Estructura del Proyecto

```
calibrator_gui/
├── scripts/
│   ├── rosbag_backend/
│   │   ├── __init__.py
│   │   ├── bag_indexer.py        # ✓ Fase 1
│   │   ├── frame_navigator.py    # ✓ Fase 3
│   │   ├── message_loader.py     # ⏳ Fase 4
│   │   ├── test_bag_quick.py
│   │   └── test_bag_indexer.py
│   ├── demo_search_in_topics.py      # ✓ Fase 2
│   ├── demo_frame_navigation.py      # ✓ Fase 3
│   ├── demo_message_loading.py       # ⏳ Fase 4
│   └── calibrator_gui.py             # ⏳ Fase 5
├── src/
│   └── main.cpp                  # Placeholder C++
├── CMakeLists.txt
├── package.xml
├── claude.md                     # Especificación original
├── FASE_1_VALIDADA.md
├── FASE_2_SEARCH_VALIDADA.md
├── FASE_3_NAVIGATOR_VALIDADA.md
├── FASE_4_GUIA.md
├── RESUMEN_PROGRESO.md           # ← Este archivo
└── README.md                     # ← Este archivo
```

---

## 🚀 Instalación y Uso

### Requisitos
```bash
# Sistema
- Python 3.8+
- ROS (Melodic, Noetic, o Humble)
- rosbag, rospy

# Paquetes Python
pip install PyQt5 numpy pyyaml
pip install sensor_msgs
```

### Setup del Proyecto
```bash
cd ~/workspace/src/calibrator_gui
```

### Ejecutar Demostraciones

#### Demo 1: Búsqueda Multi-Tópico
```bash
python3 scripts/demo_search_in_topics.py /ruta/al/archivo.bag
# Busca mensajes más cercanos en lista de tópicos
# Tiempo: < 5 segundos para 3 búsquedas
```

#### Demo 2: Navegación de Frames
```bash
python3 scripts/demo_frame_navigation.py /ruta/al/archivo.bag
# Demuestra next(), prev(), goto(), jump_to_percent()
# Tiempo: < 2 segundos
```

### Testing
```bash
# Test rápido (metadata only)
python3 scripts/test_bag_quick.py /ruta/archivo.bag

# Test completo (carga índice completo)
python3 scripts/test_bag_indexer.py /ruta/archivo.bag
```

---

## 📊 Rendimiento Validado

### Bolsa de Prueba
```
Archivo: zed_flir_velodyne_2025-10-02-16-03-32.bag
Tamaño: ~5 GB
Duración: 1119.40 segundos (~18.6 minutos)
Mensajes: 196,929
Tópicos: 11
```

### Benchmarks

| Operación | Tiempo | Complejidad |
|-----------|--------|------------|
| **Fase 1**: Indexar (lazy) | 2.52s | O(1) |
| **Fase 1**: Indexar (full) | ~90s | O(n) |
| **Fase 2**: Búsqueda | 100ms | O(k log n) |
| **Fase 3**: next/prev/goto | <1ms | O(1) |
| **Fase 3**: jump_to_percent | 1ms | O(1) |
| **Total demo**: Fases 1-3 | <5s | - |

---

## 🔄 Pipeline de Fases

```
┌──────────────────────────────────────────────────────────┐
│ FASES COMPLETADAS (✓)                                     │
└──────────────────────────────────────────────────────────┘

Fase 1: BagIndexer
  └─> Metadata extraction (2.52s para 196k msgs)
  └─> Lazy vs full index modes
  └─> Topics discovery

    ⬇️

Fase 2: Search
  └─> Windowed search en tópicos específicos (<100ms)
  └─> Integración con Fase 1
  └─> Precision ±0.02s

    ⬇️

Fase 3: FrameNavigator
  └─> O(1) navigation (next/prev/goto)
  └─> Range management
  └─> Progress tracking

┌──────────────────────────────────────────────────────────┐
│ PRÓXIMAS FASES (⏳)                                       │
└──────────────────────────────────────────────────────────┘

Fase 4: MessageLoader
  └─> Carga datos reales de sensores
  └─> PointCloud2 → numpy arrays
  └─> Image → numpy arrays
  └─> IMU → dict
  └─> Caché inteligente

    ⬇️

Fase 5: GUI + Playback
  └─> PyQt5 interfaz
  └─> Timeline slider
  └─> 3D Canvas para visualización
  └─> Pestañas de sensores
  └─> Play/pause/stop

    ⬇️

Fase 6: Calibration Export
  └─> Guardar coordenadas calibradas
  └─> YAML format multi-detector
  └─> Validación de datos
```

---

## 💡 Arquitectura de Datos

```
rosbag file
    ↓
[BagIndexer] → metadata + lazy loading
    ↓
[Search] → find closest msg in topics
    ↓
[FrameNavigator] → O(1) frame navigation
    ↓
[MessageLoader] → convert to numpy (PointCloud, Image, IMU)
    ↓
[GUI/Canvas] → render 3D + images
    ↓
[Export] → save calibration YAML
```

---

## 📖 Documentación Detallada

- **[claude.md](claude.md)** - Especificación original del proyecto
- **[FASE_1_VALIDADA.md](FASE_1_VALIDADA.md)** - Detalles de indexación
- **[FASE_2_SEARCH_VALIDADA.md](FASE_2_SEARCH_VALIDADA.md)** - Búsqueda multi-tópico
- **[FASE_3_NAVIGATOR_VALIDADA.md](FASE_3_NAVIGATOR_VALIDADA.md)** - Navegación eficiente
- **[FASE_4_GUIA.md](FASE_4_GUIA.md)** - Guía para implementar Fase 4
- **[RESUMEN_PROGRESO.md](RESUMEN_PROGRESO.md)** - Estado general del proyecto

---

## 🧑‍💻 API Principal

### BagIndexer
```python
from scripts.rosbag_backend import BagIndexer

indexer = BagIndexer('archivo.bag')  # lazy_index=True (default)

# Propiedades
indexer.total_messages      # int: 196929
indexer.topics()            # List[str]: ['/velodyne_points', ...]
indexer._topics_info        # Dict: {topic: {type, message_count, ...}}
indexer._info              # Dict: {start_time, end_time, duration, ...}

# Métodos
topic, entry = indexer.get_closest_message_in_topics(topics, timestamp)
```

### FrameNavigator
```python
from scripts.rosbag_backend import FrameNavigator

nav = FrameNavigator(indexer)

# Métodos de navegación (O(1))
nav.set_range(start_idx, end_idx)
nav.next()
nav.prev()
nav.goto(frame_idx)
nav.jump_to_percent(percent)  # 0-100
nav.goto_by_timestamp(timestamp)

# Propiedades
nav.current_index           # int: índice actual
nav.range_start / range_end # int: rango de trabajo
nav.get_progress_percent()  # float: 0-100
nav.get_current_position()  # FramePosition: información completa
```

### MessageLoader (próximo)
```python
loader = MessageLoader(indexer, nav)

pc = loader.load_pointcloud(topic)   # np.ndarray (n, 3)
img = loader.load_image(topic)       # np.ndarray (H, W, C)
imu = loader.load_imu(topic)         # Dict {accel, angular_vel}

frame_data = loader.get_current_frame_data()  # Dict: todas las anteriores
```

---

## 🎓 Lecciones Aprendidas

1. **Compilados > Python**: `rosbag info` (C++) es 38x más rápido
2. **Windowed search**: Reducir ventana a ±2s = evitar cargar todo el bag
3. **O(1) operations**: Crítico para UI responsiva (slider, navegación)
4. **Lazy loading**: Essential para bags grandes (no iterar todos los mensajes)
5. **Modularización**: Cada fase independiente, fácil de integrar

---

## 🐛 Troubleshooting

### "rosbag not found"
```bash
source /opt/ros/noetic/setup.bash  # (o tu ROS distro)
```

### "Timeout en navegación"
- Asegurar que `lazy_index=True` en BagIndexer
- No cargar índice completo sin necesidad

### "PointCloud2 conversion error"
- Verificar que `sensor_msgs` esté instalado
- Confirmar que el tópico contiene mensajes PointCloud2

---

## 📝 Próximos Pasos

1. **Fase 4** (1-2 horas)
   - Implementar MessageLoader
   - Conversiones de sensores (PointCloud2, Image, IMU)
   - Testing con cargas reales

2. **Fase 5** (3-4 horas)
   - Crear GUI PyQt5
   - Timeline slider
   - 3D Canvas para visualización
   - Integración con FrameNavigator

3. **Fase 6** (1 hora)
   - Export YAML
   - Multi-detector support
   - Validación

---

## 📞 Soporte y Contacto

Para preguntas sobre las fases completadas, consultar:
- Documentación en markdown de cada fase
- Code comments en los archivos Python
- Ejemplos en scripts `demo_*.py`

Para continuar la implementación:
- Ver [FASE_4_GUIA.md](FASE_4_GUIA.md) para instrucciones detalladas
- Basarse en estructura de Fases 1-3 para consistencia

---

## 📄 Licencia

Proyecto desarrollado con fines educativos y de investigación en robótica.

---

**Última actualización**: Sesión actual  
**Próxima sesión**: Comenzar Fase 4 (Message Loader)  
**Progreso**: ██████░░░░ 50% (3/6 fases)
