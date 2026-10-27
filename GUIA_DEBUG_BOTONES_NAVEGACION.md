# 🎬 Guía: Usar Botones de Navegación en Modo ROS En Vivo

## 📋 Problema

Los botones de navegación no tienen efecto en la reproducción del bag.

## 🔍 Debugging

Ahora hay **logging detallado** para ver qué está pasando:

### Paso 1: Ejecuta la GUI con salida de consola

```bash
cd /home/lucassilva/workspace/src/calibrator_gui
python3 scripts/gui_main.py 2>&1 | tee debug.log
```

### Paso 2: Espera a que se acumulen frames

En otra terminal, lanza el pipeline:
```bash
roslaunch rosbag_launcher play_zed_lidar.launch
```

Espera ~10 segundos para que se acumulen frames en el buffer.

### Paso 3: Haz clic en "Siguiente ⏭"

Mira la consola. Deberías ver:
```
[NAVIGATE] Frame cambió: 0 → 1 (steps=1)
[DISPLAY] Actualizando frame 1, timestamp=1234567.89
```

Si ves esto, el botón **SÍ funciona** y el problema está en la visualización.

## 📊 Qué buscar en el log

### ✅ Funcionamiento correcto:
```
[NAVIGATE] Frame cambió: 0 → 1 (steps=1)
[DISPLAY] Actualizando frame 1, timestamp=1234567.89
```

### ❌ No cambia de frame:
```
[NAVIGATE] Frame cambió: 0 → 0 (steps=1)
```
→ **Problema**: No hay frames en el historial o `advance_frame()` alcanzó el límite

### ❌ Sin historial:
```
[ADVANCE] Frame history vacío
```
→ **Problema**: Callbacks no están guardando frames

### ❌ Sin datos en display:
```
[DISPLAY] Sin timestamp - sin datos aún
```
→ **Problema**: El frame existe pero no tiene datos

## 🔧 Posibles Causas y Soluciones

### Causa 1: No hay frames en el buffer
**Síntoma**: `[ADVANCE] Frame history vacío`

**Solución**:
1. Espera más tiempo (~15 segundos)
2. Verifica que el pipeline ROS está corriendo
3. Busca en el log: `[INFO] Publishing bag contents` en la terminal del launch

### Causa 2: Historial no se llena
**Síntoma**: Frame count sigue siendo 0/0

**Solución**: 
1. El callback `_on_pointcloud()` podría no estar siendo llamado
2. Verifica que `/velodyne_points` tiene datos:
   ```bash
   rostopic echo /velodyne_points -n 5
   ```
3. Si no hay datos, el bag podría estar vacío o el launch no está reproduciendo

### Causa 3: Botones no responden
**Síntoma**: Al hacer clic no pasa nada en la consola

**Solución**:
1. Verifica que estás en "modo ROS En Vivo" (debe decir "🔴 ROS En Vivo" en la GUI)
2. Los botones solo funcionan en modo ROS, no en modo .bag
3. Intenta hacer clic varias veces

### Causa 4: Visualización no cambia
**Síntoma**: Frame cambia en consola pero no en la pantalla

**Solución**:
1. Verifica que estás viendo la pestaña LiDAR o 3D
2. Los datos podrían ser iguales entre frames (verifica timestamp)
3. La visualización podría necesitar más datos antes de renderizar

## 🧪 Test Manual

### Test 1: Verificar que los frames se acumulan
```bash
# En consola, busca logs como:
# [DISPLAY] Actualizando frame 0, timestamp=...
# [DISPLAY] Actualizando frame 1, timestamp=...
# [DISPLAY] Actualizando frame 2, timestamp=...

# Si el timestamp cambia, los frames se están guardando
```

### Test 2: Verificar que los botones navegan
```bash
# Haz clic en "Siguiente ⏭"
# Deberías ver en consola:
[NAVIGATE] Frame cambió: 5 → 6 (steps=1)

# Haz clic en "Anterior ⏮"
# Deberías ver:
[NAVIGATE] Frame cambió: 6 → 5 (steps=-1)
```

### Test 3: Verificar reproducción automática
```bash
# Haz clic en "▶ Reproducir"
# En consola deberías ver:
[PLAYBACK] Iniciando reproducción automática

# Y luego frames incrementando automáticamente:
[NAVIGATE] Frame cambió: 5 → 6 (steps=1)
[DISPLAY] Actualizando frame 6, timestamp=...
[NAVIGATE] Frame cambió: 6 → 7 (steps=1)
[DISPLAY] Actualizando frame 7, timestamp=...
...

# Haz clic en "⏸ Pausar"
# Deberías ver:
[PLAYBACK] Pausando reproducción
```

## 📝 Reporte de Problemas

Si después de este debugging siguen sin funcionar, recopila:

1. **Terminal output**: `tee debug.log` (últimas 50 líneas)
2. **Estado GUI**: ¿Modo ROS o Bag?
3. **Botones que probaste**: ¿Cuál?
4. **Frame count**: ¿Qué dice en el label?
5. **Logs esperados vs reales**: 

```bash
# Ejecutar en otra terminal para copiar logs
tail -50 debug.log | grep -E "\[NAVIGATE\]|\[PLAYBACK\]|\[DISPLAY\]"
```

## 🎯 Checklist

- [ ] GUI abierta en modo ROS En Vivo (label dice "🔴 ROS En Vivo")
- [ ] Botones visibles (⏮, ▶, ⏭)
- [ ] Pipeline ROS lanzado y reproduciendo (`play_zed_lidar.launch`)
- [ ] Frame count > 0 (dice "Frame: X/Total")
- [ ] Console muestra `[NAVIGATE]`, `[DISPLAY]`, o `[PLAYBACK]` logs
- [ ] Timestamp en label cambia cuando haces clic

Si todo está ✅, los botones deberían funcionar.

---

**Próximo paso**: Ejecuta con este debugging y comparte los logs para diagnosticar.

