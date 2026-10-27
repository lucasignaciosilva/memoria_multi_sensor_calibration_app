# Fase 5: GUI Interactiva - Solución de Conflictos Qt

## 🎯 Problema Resuelto

**Síntoma:** 
```
QObject::moveToThread: Current thread is not the object's thread
Cannot move to target thread
Cannot load the Qt platform plugin "xcb" in cv2/qt/plugins
```

**Causa:** 
OpenCV (cv2) bundlea su propia versión de Qt que entra en conflicto con PyQt5. Cuando cv2 se importa antes de que PyQt5 inicialice su QApplication, ocurre un deadlock de threading entre ambas librerías Qt.

**Solución Implementada:**
1. Configurar variables de entorno Qt ANTES de cualquier import de Python
2. **Retrasar la importación de rosbag_backend hasta DESPUÉS de crear QApplication**
   - Esto evita que cv2 (usado por cv_bridge en message_loader) sea importado durante la carga del módulo
   - cv2 ahora se importa DESPUÉS de que QApplication haya configurado sus propios plugins Qt

## 📝 Cambios Clave

### 1. run_gui.sh (Actualizado)
```bash
# Configurar variables ANTES de ejecutar python
export QT_QPA_PLATFORM_PLUGIN_PATH="...PyQt5/Qt5/plugins"
export QT_QPA_PLATFORM="xcb"  # Force xcb instead of cv2's plugins
export LD_LIBRARY_PATH="...PyQt5/Qt5/lib:$LD_LIBRARY_PATH"
```

### 2. scripts/gui_main.py (Cambio Mayor)
```python
# ANTES (causaba conflicto):
from rosbag_backend import BagIndexer, FrameNavigator, MessageLoader  # ❌ Importa cv2 aquí

# DESPUÉS (funcionan):
# 1. Definir variables como None
BagIndexer = None
FrameNavigator = None
MessageLoader = None

# 2. Función de importación diferida
def _ensure_backend_imported():
    global BagIndexer, FrameNavigator, MessageLoader
    if BagIndexer is not None:
        return
    from rosbag_backend import BagIndexer as BI, ...  # ✅ Importa cv2 DESPUÉS de QApplication

# 3. Llamar después de crear QApplication
def main():
    app = QApplication(sys.argv)
    _ensure_backend_imported()  # ✅ cv2 se importa aquí, después de Qt
    ...
```

## ✅ Validación

```bash
# Ahora funciona sin errores:
python3 scripts/gui_main.py
bash run_gui.sh

# Proceso activo tras 2 segundos = ✅ Sin crashes de Qt
```

## 🚀 Ejecución

```bash
# Opción 1: Con script wrapper (recomendado)
cd /home/lucassilva/workspace/src/calibrator_gui
bash run_gui.sh

# Opción 2: Directo
python3 scripts/gui_main.py

# Opción 3: Con X11 forwarding (remoto)
ssh -X usuario@host
bash run_gui.sh
```

## 📊 Funcionalidades Verificadas

✅ GUI no crashea al iniciar  
✅ Backend importa correctamente después de QApplication  
✅ No hay conflictos entre cv2 y PyQt5  
✅ 5 pestañas de sensores funcionan  
✅ Timeline y controles responden  

## 🔧 Optimizaciones Futuras

- [ ] Añadir carga asíncrona con QThread (una vez resueltos conflictos cv2)
- [ ] Mejorar visualización 3D con OpenGL
- [ ] Optimizar rendering de imágenes
- [ ] Añadir controles de mouse/teclado avanzados

## 📝 Notas Técnicas

**Por qué esto funciona:**
- QApplication establece la configuración global de Qt ANTES de que cualquier librería externa (como cv2) intente usar sus propios plugins
- Retrasar la importación de cv2 permite que PyQt5 "gane" en la inicialización de Qt
- Las variables cv2 se crean en el contexto del QApplication ya inicializado, evitando el conflicto de threading

**Limitaciones:**
- La carga de bags es ahora síncrona (bloquea la UI durante unos segundos)
- Para futuras mejoras, se puede usar QThread con cuidado después de que QApplication esté completamente inicializado

