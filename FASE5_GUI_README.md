# Fase 5: GUI Interactiva PyQt5 - Guía de Ejecución

## 📋 Requisitos

- Python 3.8+
- PyQt5
- rosbag + rospy
- numpy
- cv_bridge
- opencv-python o opencv-python-headless

## 🚀 Ejecución del GUI

### Opción 1: Ejecución directa (requiere X11 display)

```bash
cd /home/lucassilva/workspace/src/calibrator_gui
python3 scripts/gui_main.py
```

### Opción 2: Usando script wrapper (recomendado)

```bash
cd /home/lucassilva/workspace/src/calibrator_gui
bash run_gui.sh
```

El script wrapper:
- Configura Qt plugins automáticamente
- Usa Xvfb si no hay display disponible
- Maneja conflictos entre cv2 y PyQt5

### Opción 3: En servidor remoto (SSH con X11 forwarding)

```bash
# En tu máquina local
ssh -X usuario@host

# Luego ejecutar
bash run_gui.sh
```

## 🔧 Solución de problemas

### Error: "Cannot load the Qt platform plugin"

**Solución**: El script wrapper ya lo maneja automáticamente. Si continúa:

```bash
export QT_QPA_PLATFORM_PLUGIN_PATH="/home/lucassilva/.local/lib/python3.8/site-packages/PyQt5/Qt5/plugins"
python3 scripts/gui_main.py
```

### Error: "QObject::moveToThread"

**Solución**: Ya está resuelta en la versión actual. El GUI usa threads separados para cargar bags.

### Sin display X11

**Solución automática**: 
- Si tienes Xvfb instalado: se lanza automáticamente
- Si no: usa offscreen mode (sin interfaz gráfica visible)

Para instalar Xvfb en Ubuntu/Debian:
```bash
sudo apt-get install xvfb
```

## 📂 Archivos Principales

- `scripts/gui_main.py`: Aplicación principal
- `scripts/rosbag_backend/`: Backend de Fases 1-4
- `run_gui.sh`: Script de lanzamiento recomendado

## ✨ Características Implementadas

### Interfaz Principal
- ✅ Ventana principal con menús y controles
- ✅ 5 pestañas de sensores (Cámara, LiDAR, IMU, GPS, 3D)
- ✅ Timeline deslizable
- ✅ Controles Play/Pause

### Integración Backend
- ✅ BagIndexer (Fase 1): Indexación rápida
- ✅ FrameNavigator (Fase 3): Navegación O(1)
- ✅ MessageLoader (Fase 4): Carga de sensores
- ✅ Actualizaciones en tiempo real

### Controles
- ✅ Selector de rango de frames
- ✅ Navegación por timeline
- ✅ Reproducción automática
- ✅ Carga asíncrona de bags

## 🎯 Flujo de Trabajo

1. Iniciar GUI: `bash run_gui.sh`
2. Cargar archivo: Click en "📂 Abrir Bag"
3. Seleccionar rango (opcional): Ajustar frame inicial/final y click "✓ Aplicar"
4. Reproducir: Click "▶ Play" o usar timeline
5. Navegar: Mover slider o presionar "⏸ Pause" para frame específico
6. Cambiar vistas: Click en pestañas (Cámara, LiDAR, IMU, GPS, 3D)

## 📊 Pestañas de Sensores

### 📷 Cámara
- Muestra imagen en tiempo real
- Timestamp del frame
- Resolución y frecuencia

### 📡 LiDAR  
- Número de puntos capturados
- Rango de detección (min/max)
- Estadísticas XYZ

### ⚡ IMU
- Aceleración (X, Y, Z)
- Velocidad angular (Giroscopio)

### 🌍 GPS
- Latitud, Longitud, Precisión
- (Actualmente con valores de ejemplo)

### 🎲 Vista 3D
- Visualización tridimensional
- Controles: Rotar, Trasladar, Zoom
- Contador de objetos

## 🔄 Threading

El GUI usa un sistema de threads para:
- **Thread principal**: Interfaz Qt
- **Thread worker**: Carga de bags (no bloquea UI)

Esto permite que la interfaz permanezca responsiva durante la carga de archivos grandes.

## 📝 Próximos Pasos

- Fase 6: Exportación a YAML
- Mejoras 3D: Canvas con OpenGL
- Controles avanzados: Mouse y teclado
- Optimización de rendering

## ℹ️ Información de Versión

- **Fase**: 5/6
- **Estado**: Implementación completa, lista para probar
- **Backend integrado**: Fases 1-4 (BagIndexer, FrameNavigator, MessageLoader)
- **Última actualización**: 23 Abril 2026

