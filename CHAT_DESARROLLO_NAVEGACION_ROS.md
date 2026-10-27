# Chat de Desarrollo: Navegación en Modo ROS En Vivo
**Fecha**: Abril 28, 2026  
**Tema**: Implementación de controles de navegación adelante/atrás para reproducción de bag en modo ROS En Vivo

---

## 📋 Resumen Ejecutivo

Se implementó un sistema completo de navegación de frames para modo ROS En Vivo que permite:
- Reproducir frames en tiempo real (como una película)
- Retroceder/adelantar frame a frame
- Reproducción automática con pausa/play
- Buffer de 500 frames para navegación

**Status**: ✅ Implementación completa | ⚠️ Debugging en progreso

---

## 🔍 Problema Inicial

El usuario quería poder "adelantar y retroceder en el bag que está leyendo ROS". 

En modo ROS En Vivo, la GUI recibía datos en streaming continuo, pero no había forma de navegar por frames ya capturados.

---

## 💡 Solución Diseñada

### Arquitectura de Buffer
```
ROSLiveListener:
┌─────────────────────────────────┐
│ frame_history (OrderedDict)     │
├─────────────────────────────────┤
│ [Frame 0] → [Frame 1] → ...     │
│           current_frame_index   │
│           (índice actual)       │
│ Max 500 frames en memoria       │
└─────────────────────────────────┘
```

### Flujo de Datos
```
ROS Topics → Callbacks → frame_history
                              ↓
                    navigate_to_frame()
                              ↓
                    get_current_frame_data()
                              ↓
                         GUI Display
```

---

## 🛠️ Cambios Implementados

### 1. **ROSLiveListener** (`ros_live_listener.py`)

#### Nuevo en `__init__`:
```python
self.frame_history = OrderedDict()  # Historial completo
self.current_frame_index = -1       # Índice actual
self.cache_size = cache_size        # Buffer máximo (500 frames)
```

#### Nuevos métodos:
- `get_total_frames()` - Cantidad de frames capturados
- `get_current_frame_index()` - Frame actual
- `navigate_to_frame(index)` - Ir a frame específico
- `advance_frame(steps)` - Avanzar/retroceder N frames
- `get_frame(index)` - Obtener datos de frame específico

#### Cambio en callbacks:
Cuando llega un PointCloud2, ahora también guarda un snapshot en el historial:
```python
# Agregar al historial con índice
frame_copy = {
    'timestamp': ...,
    'pointclouds': {},
    'images': {},
    'imu': None,
    'available_sensors': set(),
}
self.frame_history[frame_idx] = frame_copy
self.current_frame_index = frame_idx

# Mantener tamaño máximo del buffer
if len(self.frame_history) > self.cache_size:
    oldest_key = next(iter(self.frame_history))
    del self.frame_history[oldest_key]
```

### 2. **GUI** (`gui_main.py`)

#### Nuevos atributos en `__init__`:
```python
self.btn_prev = None      # Botón "⏮ Anterior"
self.btn_play_pause = None # Botón "▶ Reproducir"
self.btn_next = None      # Botón "Siguiente ⏭"
self.is_playing = False   # Estado de reproducción
self.playback_timer = None # Timer para auto-reproducción
```

#### Nuevos en `create_range_panel()`:
```python
# Botones de navegación (ocultos en modo bag, visibles en ROS)
self.btn_prev = QPushButton("⏮ Anterior")
self.btn_prev.hide()
self.btn_prev.clicked.connect(lambda: self.on_navigate_frame(-1))

self.btn_play_pause = QPushButton("▶ Reproducir")
self.btn_play_pause.hide()
self.btn_play_pause.clicked.connect(self.on_toggle_playback)

self.btn_next = QPushButton("Siguiente ⏭")
self.btn_next.hide()
self.btn_next.clicked.connect(lambda: self.on_navigate_frame(1))
```

#### Nuevos métodos:
```python
def on_navigate_frame(self, steps: int = 1):
    """Navega N frames adelante/atrás en modo ROS."""
    if not self.is_ros_mode or self.ros_live_loader is None:
        return
    
    self.ros_live_loader.advance_frame(steps)
    self.update_display_ros()

def on_toggle_playback(self):
    """Activa/desactiva reproducción automática en modo ROS."""
    if not self.is_ros_mode:
        return
    
    self.is_playing = not self.is_playing
    
    if self.is_playing:
        self.btn_play_pause.setText("⏸ Pausar")
        if not hasattr(self, 'playback_timer'):
            self.playback_timer = QTimer()
            self.playback_timer.timeout.connect(lambda: self.on_navigate_frame(1))
        self.playback_timer.start(100)  # 10 FPS
    else:
        self.btn_play_pause.setText("▶ Reproducir")
        if hasattr(self, 'playback_timer'):
            self.playback_timer.stop()
```

#### Actualización de `update_display_ros()`:
```python
# Mostrar frame actual/total en label
current_idx = self.ros_live_loader.get_current_frame_index()
total_frames = self.ros_live_loader.get_total_frames()
self.label_total_frames.setText(f"Frame: {current_idx + 1}/{total_frames}")
```

#### En `_connect_ros_live()`:
```python
# Mostrar controles de navegación para modo ROS
self.btn_prev.show()
self.btn_play_pause.show()
self.btn_next.show()
```

#### En `_open_bag_file()`:
```python
# Ocultar controles de navegación de ROS (no necesarios en modo bag)
self.btn_prev.hide()
self.btn_play_pause.hide()
self.btn_next.hide()
```

---

## 🧪 Validación Realizada

✅ **Sintaxis**: Sin errores en ambos archivos
✅ **Importaciones**: ROSLiveListener carga correctamente
✅ **Estructura**: Métodos presentes y correctamente nombrados
✅ **Thread-safety**: Locks en ROSLiveListener para acceso seguro

---

## ⚠️ Problema Reportado

Después de la implementación, el usuario reportó:
> "Los botones anterior, reproducir/pausar y siguiente no tienen efecto en la reproducción del bag"

### Posibles Causas:
1. **Timer no está actualizado**: `update_display_ros()` se llama desde `on_navigate_frame()` pero el timer principal (`ros_update_timer`) también está activo
2. **Frame index no se mantiene**: Después de navegar manualmente, el timer automático podría estar adelantando un frame extra
3. **Display no se actualiza**: Las pestañas no están mostrando datos del frame navegado
4. **Orden de ejecución**: `on_navigate_frame()` → `advance_frame()` → `update_display_ros()` pero podría haber race conditions

---

## 🔧 Debugging Sugerido

### Paso 1: Verificar que `advance_frame()` funciona
```python
# Agregar logging en on_navigate_frame()
def on_navigate_frame(self, steps: int = 1):
    old_idx = self.ros_live_loader.get_current_frame_index()
    self.ros_live_loader.advance_frame(steps)
    new_idx = self.ros_live_loader.get_current_frame_index()
    print(f"Navigate: {old_idx} → {new_idx} (steps={steps})")
    self.update_display_ros()
```

### Paso 2: Verificar que `update_display_ros()` renderiza
```python
# Agregar logging en update_display_ros()
def update_display_ros(self):
    data = self.ros_live_loader.get_current_frame_data()
    idx = self.ros_live_loader.get_current_frame_index()
    total = self.ros_live_loader.get_total_frames()
    print(f"Display update: Frame {idx}/{total}, timestamp={data['timestamp']}")
    # ... resto del código
```

### Paso 3: Verificar sincronización de timers
```python
# El ros_update_timer podría estar interfiriendo
# Posible solución: Detener timer principal cuando se navega manualmente
def on_navigate_frame(self, steps: int = 1):
    # Pausar actualización automática mientras navegamos
    if hasattr(self, 'ros_update_timer') and self.ros_update_timer.isActive():
        self.ros_update_timer.stop()
    
    self.ros_live_loader.advance_frame(steps)
    self.update_display_ros()
    
    # Reanudar actualización automática si no estamos en reproducción
    if not self.is_playing and hasattr(self, 'ros_update_timer'):
        self.ros_update_timer.start()
```

---

## � Debugging Implementado (Sesión 2)

Para diagnosticar por qué los botones no funcionan, se agregó **logging detallado** en:

### En `on_navigate_frame()`:
```python
old_idx = self.ros_live_loader.get_current_frame_index()
self.ros_live_loader.advance_frame(steps)
new_idx = self.ros_live_loader.get_current_frame_index()
print(f"[NAVIGATE] Frame cambió: {old_idx} → {new_idx} (steps={steps})")
```

### En `on_toggle_playback()`:
```python
print("[PLAYBACK] Iniciando reproducción automática")
# o
print("[PLAYBACK] Pausando reproducción")
```

### En `update_display_ros()`:
```python
print(f"[DISPLAY] Actualizando frame {current_idx}, timestamp={data['timestamp']}")
print(f"[DISPLAY] Sin timestamp - sin datos aún")
```

### En `advance_frame()` de ROSLiveListener:
```python
print(f"[ADVANCE] Pos: {current_pos} → {new_pos}, Frame: ... → {new_index}, moved={moved}")
print(f"[ADVANCE] Frame history vacío")
```

### Cómo usar el debugging:
```bash
python3 scripts/gui_main.py 2>&1 | tee debug.log

# En otra terminal:
tail -f debug.log | grep -E "\[NAVIGATE\]|\[DISPLAY\]|\[PLAYBACK\]"
```

### Qué buscar:
- ✅ `[NAVIGATE] Frame cambió: 0 → 1` = botón funciona
- ❌ `[NAVIGATE] Frame cambió: 0 → 0` = no hay frames o límite alcanzado
- ✅ `[DISPLAY] Actualizando frame 1` = display se actualiza
- ❌ `[DISPLAY] Sin timestamp` = frame sin datos

---

## 📚 Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `scripts/rosbag_backend/ros_live_listener.py` | +90 líneas: Buffer de frames, métodos de navegación |
| `scripts/gui_main.py` | +100 líneas: Botones, métodos, lógica de reproducción |
| `GUIA_DEBUG_BOTONES_NAVEGACION.md` | Nueva guía de debugging |

---

## 🎯 Próximos Pasos

1. ✅ **Implementar logging detallado** (Hecho)
2. ⏳ **Ejecutar con debugging y capturar logs**
3. ⏳ **Diagnosticar causa raíz**
4. ⏳ **Aplicar fix específico**
5. ⏳ **Validar funcionamiento**

---

## 📊 Archivos Finales

| Archivo | Propósito | Estado |
|---------|-----------|--------|
| `CHAT_DESARROLLO_NAVEGACION_ROS.md` | Este archivo | ✅ Documentación completa |
| `GUIA_DEBUG_BOTONES_NAVEGACION.md` | Debugging step-by-step | ✅ Listo para usar |
| `scripts/gui_main.py` | GUI con logging | ✅ Logging agregado |
| `scripts/rosbag_backend/ros_live_listener.py` | Buffer con logging | ✅ Logging agregado |

---

## 🔗 Referencias

- **Módulo ROSLiveListener**: `scripts/rosbag_backend/ros_live_listener.py` (~300 líneas)
- **Módulo GUI**: `scripts/gui_main.py` (~1600 líneas)
- **Test de lógica**: `test_dual_mode_logic.py`
- **Guía de debugging**: `GUIA_DEBUG_BOTONES_NAVEGACION.md`

---

**Status**: 🟡 Implementación completa, debugging en progreso  
**Próxima acción**: Ejecutar con logging y diagnosticar causa raíz

