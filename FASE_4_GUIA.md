# 📋 GUÍA PARA PRÓXIMA SESIÓN - Fase 4: Message Loader

**Preparado por**: Sesión anterior  
**Fases completadas**: 1, 2, 3 (Indexing, Search, Navigation)  
**Siguiente tarea**: Fase 4 - Carga de datos de mensajes reales  

---

## 🎯 Objetivo de Fase 4

Cargar datos reales de sensores durante navegación para proporcionar información para renderizado 3D e imágenes.

**Entrada**: Índice de frame (de FrameNavigator)  
**Salida**: Arrays numpy con datos de sensores listos para renderizar

---

## 📁 Archivos Involucrados

### Existentes (Fase 1-3)
```
scripts/rosbag_backend/
├── bag_indexer.py          # ✓ Carga rápida de metadatos
├── frame_navigator.py      # ✓ Navegación O(1)
├── __init__.py             # Exporta clases públicas
├── test_bag_quick.py       # ✓ Test rápido
└── test_bag_indexer.py     # ✓ Test completo

scripts/
├── demo_search_in_topics.py      # ✓ Demo búsqueda
├── demo_frame_navigation.py      # ✓ Demo navegación
└── demo_message_loading.py       # ← CREAR
```

### Por Crear (Fase 4)
```
scripts/rosbag_backend/
└── message_loader.py  # ← NUEVO MÓDULO

scripts/
└── demo_message_loading.py  # ← DEMO
```

---

## 🔨 Especificación de message_loader.py

### Clase Principal

```python
class MessageLoader:
    """Carga y convierte datos de sensores a formato renderizable."""
    
    def __init__(self, indexer: BagIndexer, nav: FrameNavigator, 
                 cache_size: int = 20):
        """
        Args:
            indexer: BagIndexer con datos
            nav: FrameNavigator para posición actual
            cache_size: Cantidad de mensajes a cachear
        """
        self.indexer = indexer
        self.nav = nav
        self.cache: Dict[int, rosbag.Message] = {}
        self.cache_size = cache_size
    
    def get_current_frame_data(self) -> Dict[str, Any]:
        """
        Obtiene todos los datos disponibles del frame actual.
        
        Returns:
            Dict con claves:
            - 'pointcloud': np.ndarray (n, 3) si /velodyne_points disponible
            - 'image': np.ndarray si /zed/.../image_rect_color disponible
            - 'imu': Dict con aceleración y velocidad angular
            - 'timestamp': float
            - 'topics': Set de tópicos disponibles en este frame
        """
        pass
    
    def load_pointcloud(self, topic: str) -> Optional[np.ndarray]:
        """
        Carga PointCloud2 y lo convierte a array (n, 3).
        
        Args:
            topic: Nombre del tópico (ej: '/velodyne_points')
        
        Returns:
            Array numpy de forma (n_points, 3) con coordenadas XYZ,
            o None si no está disponible
        """
        pass
    
    def load_image(self, topic: str) -> Optional[np.ndarray]:
        """
        Carga Image msg y la convierte a array (H, W, C).
        
        Args:
            topic: Nombre del tópico (ej: '/zed/zed_node/left/image_rect_color')
        
        Returns:
            Array numpy de forma (height, width, channels) tipo uint8,
            o None si no está disponible
        """
        pass
    
    def load_imu(self, topic: str) -> Optional[Dict]:
        """
        Carga datos IMU (Imu msg).
        
        Args:
            topic: Nombre del tópico (ej: '/imu/data')
        
        Returns:
            Dict con claves:
            - 'accel': np.ndarray (3,) con [ax, ay, az]
            - 'angular_vel': np.ndarray (3,) con [gx, gy, gz]
            - 'timestamp': float
        """
        pass
    
    def clear_cache(self):
        """Limpia el caché de mensajes."""
        pass
```

---

## 🛠️ Detalles de Implementación

### Conversiones Requeridas

#### 1. PointCloud2 → numpy array

```python
# Entrada: sensor_msgs.PointCloud2
# Salida: np.ndarray (n_points, 3)

import sensor_msgs.point_cloud2 as pc2

def pointcloud2_to_array(msg):
    points_list = []
    for point in pc2.read_points(msg, field_names=("x", "y", "z")):
        points_list.append([point[0], point[1], point[2]])
    return np.array(points_list, dtype=np.float32)
```

#### 2. Image msg → numpy array

```python
# Entrada: sensor_msgs.Image
# Salida: np.ndarray (H, W, C)

from cv_bridge import CvBridge

def image_to_array(msg):
    bridge = CvBridge()
    cv_image = bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
    return np.array(cv_image, dtype=np.uint8)
```

#### 3. Imu msg → dict

```python
# Entrada: sensor_msgs.Imu
# Salida: Dict con accel y angular_vel

def imu_to_dict(msg):
    return {
        'accel': np.array([
            msg.linear_acceleration.x,
            msg.linear_acceleration.y,
            msg.linear_acceleration.z
        ]),
        'angular_vel': np.array([
            msg.angular_velocity.x,
            msg.angular_velocity.y,
            msg.angular_velocity.z
        ]),
        'timestamp': msg.header.stamp.to_sec()
    }
```

---

## 📊 Estrategia de Caché

### Problema
- Cargar cada mensaje desde el bag es lento (~100-500ms)
- Lectura secuencial desde posición actual es ineficiente

### Solución: Cache inteligente

```
Frame actual: 5000
Cache: [4980, 4990, 5000, 5010, 5020, 5030, 5040]

next() → frame 5001 (probablemente en cache o cercano)
goto(5500) → descartar cache, cargar nueva ventana
```

### Implementación

```python
def _ensure_cached(self, frame_index):
    """Asegura que frame_index esté en cache."""
    if frame_index in self.cache:
        return  # Ya está
    
    # Calcular ventana de cache alrededor del índice
    window_start = max(0, frame_index - self.cache_size // 2)
    window_end = min(self.indexer.total_messages, 
                     frame_index + self.cache_size // 2)
    
    # Limpiar cache anterior
    self.cache.clear()
    
    # Cargar ventana
    current = 0
    with rosbag.Bag(self.indexer.bag_path, 'r') as bag:
        for topic, msg, ts in bag.read_messages():
            if window_start <= current <= window_end:
                self.cache[current] = msg
            elif current > window_end:
                break
            current += 1
```

---

## ✅ Checklist de Implementación

### Paso 1: Estructura base
- [ ] Crear `message_loader.py`
- [ ] Definir clase `MessageLoader`
- [ ] Implementar constructor y caché

### Paso 2: Conversiones básicas
- [ ] Función `pointcloud2_to_array()`
- [ ] Función `image_to_array()`
- [ ] Función `imu_to_dict()`

### Paso 3: Métodos principales
- [ ] `load_pointcloud(topic)`
- [ ] `load_image(topic)`
- [ ] `load_imu(topic)`
- [ ] `clear_cache()`

### Paso 4: Integración
- [ ] `get_current_frame_data()` - combina todo
- [ ] Actualizar `__init__.py` para exportar

### Paso 5: Testing
- [ ] `demo_message_loading.py` con ejemplos
- [ ] Validar conversiones con tipos correctos
- [ ] Medir rendimiento de caché

### Paso 6: Documentación
- [ ] `FASE_4_LOADER_VALIDADA.md`
- [ ] Docstrings completos en código

---

## 🧪 Casos de Test para Demo

```python
# Test 1: Cargar PointCloud
loader = MessageLoader(indexer, nav)
nav.goto(100)
pc = loader.load_pointcloud('/velodyne_points')
assert pc.shape == (n, 3)
assert pc.dtype == np.float32

# Test 2: Cargar imagen
img = loader.load_image('/zed/zed_node/left/image_rect_color')
assert len(img.shape) == 3  # H, W, C
assert img.dtype == np.uint8

# Test 3: Caché funciona
pc1 = loader.load_pointcloud('/velodyne_points')
nav.next()
pc2 = loader.load_pointcloud('/velodyne_points')
# pc2 debería estar en caché, ser rápido

# Test 4: Progreso con navegación
frame_data = loader.get_current_frame_data()
assert 'pointcloud' in frame_data
assert 'timestamp' in frame_data
```

---

## 📚 Dependencias Requeridas

```python
# Verificar que estas están instaladas:
import numpy as np              # Manipulación de arrays
import rosbag                   # Lectura de bags
import sensor_msgs.point_cloud2 # Conversión PointCloud2
from sensor_msgs import Image   # Tipo Image
from sensor_msgs import Imu     # Tipo Imu
from cv_bridge import CvBridge  # Conversión de imágenes ROS
```

Si alguna falta:
```bash
# En el entorno ROS
pip install opencv-python
# CvBridge debería estar incluido con ROS
```

---

## 🔗 Integración con FrameNavigator

```python
# Uso típico en GUI:
nav = FrameNavigator(indexer)
loader = MessageLoader(indexer, nav)

# Cuando el usuario navega:
nav.next()
current_data = loader.get_current_frame_data()

# Renderizar:
if 'pointcloud' in current_data:
    points = current_data['pointcloud']
    canvas.draw_pointcloud(points)

if 'image' in current_data:
    img = current_data['image']
    canvas.draw_image(img)
```

---

## ⏱️ Estimación de Tiempo

| Tarea | Tiempo estimado |
|-------|-----------------|
| Estructura base | 15 min |
| Conversiones | 30 min |
| Caché inteligente | 20 min |
| `get_current_frame_data()` | 15 min |
| Testing | 30 min |
| Documentación | 20 min |
| **TOTAL** | **~2 horas** |

---

## 💡 Notas Importantes

1. **Performance**: Medir tiempo de carga. Target: <200ms para cargar frame + conversión
2. **Memory**: Caché de 20 frames ≈ 100-500 MB dependiendo del tipo de sensor
3. **Thread safety**: Si se usa en GUI, considerar threading para no bloquear
4. **Error handling**: Manejar tópicos inexistentes o formatos inesperados
5. **Tipos de datos**: Mantener consistencia (float32 para PC, uint8 para imágenes)

---

## 📞 Puntos de Contacto

**Reutilizable desde Fase 1-3**:
- `BagIndexer.bag_path` - Ruta del archivo
- `BagIndexer._topics_info` - Información de tópicos
- `BagIndexer.total_messages` - Total mensajes
- `FrameNavigator.current_index` - Índice actual
- `FrameNavigator.get_progress_percent()` - Progreso para UI

**Nueva dependencia**:
- `rosbag.Bag().read_messages()` - Iterar mensajes

---

## 🚀 Siguientes Fases Tras Fase 4

**Fase 5**: GUI PyQt5
- Canvas 3D para PointCloud
- Pestañas para diferentes sensores
- Timeline slider

**Fase 6**: Export YAML
- Guardar coordenadas calibradas
- Multi-detector support

---

**Inicio recomendado**: Comenzar con conversión de PointCloud2 (más usado en proyecto)

**Good luck! 🎉**
