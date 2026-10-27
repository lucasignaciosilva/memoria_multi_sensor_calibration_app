## 📡 Selector de Tópicos de LiDAR

### ¿Qué es?

El selector de tópicos permite cambiar entre diferentes fuentes de datos de LiDAR en tiempo real. En el archivo rosbag, puede haber múltiples tópicos que publiquen nubes de puntos:

- `/velodyne_points`: Nube de puntos cruda del sensor Velodyne
- `/velodyne_points_interpolated`: Versión interpolada/procesada de la nube de puntos

### Ubicación

#### En la pestaña "LiDAR" (2D):
```
┌─────────────────────────────────────────┐
│ 📡 Información de LiDAR                 │
├─────────────────────────────────────────┤
│ Tópico: [/velodyne_points ▼]  ← AQUÍ   │
├─────────────────────────────────────────┤
│ Timestamp: ...                          │
│ Puntos: ...                             │
│ Rango: ...                              │
└─────────────────────────────────────────┘
│                                         │
│  Visualización 2D (Proyección XY)      │
│                                         │
│                                         │
```

#### En la pestaña "Vista 3D":
```
┌─────────────────────────────────────────┐
│ 📡 Tópico LiDAR: [/velodyne_points ▼]  │  ← AQUÍ
├─────────────────────────────────────────┤
│                                         │
│  Visualización 3D (Canvas Matplotlib)   │
│                                         │
│                                         │
└─────────────────────────────────────────┘
```

### Cómo usar

#### 1. Detectar tópicos disponibles
Al cargar un frame con datos de LiDAR, el sistema automáticamente:
- Escanea todos los tópicos de PointCloud2 disponibles
- Los agrega al selector desplegable
- Muestra el primero encontrado por defecto

#### 2. Cambiar entre tópicos
**Opción 1: Clic en el selector**
```
1. Haz clic en el combo box del tópico
2. Se abre la lista de opciones disponibles
3. Selecciona el tópico deseado
4. La visualización se actualiza automáticamente
```

**Opción 2: Teclado**
```
1. Presiona Tab para navegar hasta el combo
2. Usa Arrow Up/Down para cambiar
3. Presiona Enter para confirmar
```

#### 3. Visualización independiente
**Característica importante**: Ambas pestañas (2D y 3D) pueden mostrar **tópicos diferentes** simultáneamente:

```
Escenario:
─────────
- Pestaña LiDAR (2D): Mostrando /velodyne_points
- Pestaña Vista 3D:  Mostrando /velodyne_points_interpolated

Esto permite:
✓ Comparar visualmente dos versiones de la misma nube
✓ Validar procesamiento de interpolación
✓ Investigar diferencias en puntos/rango
```

### Información mostrada

Cuando cambias de tópico, se actualiza automáticamente:

#### En pestaña LiDAR (2D):
- ✅ Número de puntos (puede variar según tópico)
- ✅ Rango máximo en metros
- ✅ Rango promedio
- ✅ Estadísticas X, Y, Z

#### En pestaña Vista 3D:
- ✅ Recuento de puntos actual
- ✅ Visualización 3D con nueva posición/zoom
- ✅ Timestamp del frame
- ✅ Coloreado por altura

### Casos de uso comunes

**Caso 1: Validar interpolación**
```
1. Abre pestaña LiDAR con /velodyne_points
2. Nota el recuento (ej: 65,536 puntos)
3. Cambia a /velodyne_points_interpolated
4. Nota el nuevo recuento (ej: 128,512 puntos)
5. Compara visualmente las dos versiones
```

**Caso 2: Investigar diferencias de calidad**
```
1. Vista 3D: Selecciona /velodyne_points
2. Rota y examina la nube
3. Pestaña LiDAR: Selecciona /velodyne_points_interpolated
4. Compara rangos y distribución de puntos
```

**Caso 3: Debugging de sensor**
```
1. Si solo aparece 1 tópico en el combo: El otro no está en este frame
2. Si no aparece ninguno: Verificar que el rosbag tiene PointCloud2
3. Cambiar de frame para ver si los tópicos aparecen en otros frames
```

### Implementación técnica

#### Backend (message_loader.py)
```python
# Retorna TODOS los pointclouds disponibles:
data['pointclouds'] = {
    '/velodyne_points': array_1,
    '/velodyne_points_interpolated': array_2,
}

# Mantiene backward compatibility:
data['pointcloud'] = array_1  # Primer tópico encontrado
```

#### Frontend (gui_main.py)
**SensorTabLiDAR y SensorTab3D:**
```python
# Detectan tópicos automáticamente
available_topics = list(data['pointclouds'].keys())

# Permite selección independiente
self.selected_lidar_topic = combo.currentText()

# Re-renderiza al cambiar tópico
pc = data['pointclouds'][self.selected_lidar_topic]
```

### Notas y límites

- ✅ Cada pestaña selecciona independientemente su tópico
- ✅ El cambio de tópico no afecta la rotación 3D existente (preserva posición)
- ⚠️ Si un tópico tiene 0 puntos, se muestra "No disponible"
- ⚠️ Solo se muestran tópicos que estén disponibles en el frame actual
- ℹ️ Si cambias de frame, se conserva tu selección de tópico (si aún existe)

### Troubleshooting

**Pregunta: ¿Por qué solo veo 1 tópico?**
→ El rosbag solo contiene un tópico de PointCloud2. Los otros no existen o están vacíos en este frame.

**Pregunta: ¿Puedo grabar con ambos tópicos en la GUI?**
→ La GUI solo permite visualizar y seleccionar. Para grabar, necesitarías usar herramientas de ROS (rosbag record).

**Pregunta: ¿Se sincronizan las dos pestañas?**
→ No. Cada pestaña es independiente. Puedes ver diferentes tópicos en 2D y 3D simultáneamente.

**Pregunta: ¿Puedo exportar coordenadas de ambos tópicos?**
→ Actualmente exportas según el tópico visible. Para futuras versiones se puede implementar exportación múltiple.

---

**Versión**: 1.0  
**Agregado en**: Abril 2026  
**Relacionado con**: Selector de Tópicos de LiDAR para mejor análisis comparativo
