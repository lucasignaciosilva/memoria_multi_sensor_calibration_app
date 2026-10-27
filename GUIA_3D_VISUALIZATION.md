# Visualización 3D del LiDAR - Guía de Uso

## ¿Qué cambió?

La pestaña **"🎲 Vista 3D"** ahora muestra una **visualización interactiva 3D de la nube de puntos del LiDAR** en lugar de solo información de texto.

## Características Principales

### 1. Visualización 3D Interactiva
- **Canvas Matplotlib 3D** embebido en PyQt5
- Muestra la nube de puntos capturada por el LiDAR
- **Coloreado por altura (Z)**: azul (puntos bajos) → rojo (puntos altos)
- Fondo oscuro para mejor contraste

### 2. Ejes Cartesianos
- **Eje X**: Rojo (horizontal)
- **Eje Y**: Verde (profundidad)
- **Eje Z**: Azul (altura)
- Todos etiquetados en metros

### 3. Controles Interactivos del Mouse
- **Arrastrar**: Rota la vista 3D
- **Scroll**: Zoom in/out
- **Click derecho + Arrastrar**: Traslada la vista

### 4. Información en Tiempo Real
```
📊 LiDAR: ✅ Detectado | Puntos: 5432 | Timestamp: 1234567890.123456
```

## Rendimiento

### Optimizaciones Implementadas
- **Subsampling automático**: Si hay más de 10,000 puntos, se reduce automáticamente a 10,000 para mantener interactividad
- **Limpiar datos inválidos**: Se eliminan valores NaN e Inf automáticamente
- **Renderizado eficiente**: Usa matplotlib con backend Qt5Agg

### Ejemplo
```
Bag con 230,000 puntos por frame → Se muestran 10,000 puntos subsampled
Bag con 5,000 puntos por frame → Se muestran todos los 5,000 puntos
```

## Flujo de Trabajo

1. **Abrir un bag**: Detecta automáticamente si hay LiDAR disponible
2. **Seleccionar frame**: Usa el selector "Frame: [número]" con botón "📂 Cargar"
3. **Visualizar en 3D**: La pestaña "🎲 Vista 3D" mostrará la nube automáticamente
4. **Interactuar**: Rota, zoom, traslada con el mouse según sea necesario

## Configuración de Sensores

Si necesitas habilitar/deshabilitar el LiDAR:
1. Presiona botón **"⚙️ Sensores"** en la barra superior
2. Marca/desmarca **"LiDAR"** en el diálogo
3. El cambio se refleja inmediatamente

## Solución de Problemas

### "LiDAR: ❌ No disponible"
- El bag no tiene datos de PointCloud
- O el LiDAR está deshabilitado en configuración de sensores

### Visualización lenta
- Si el bag tiene muchos puntos (>50,000), está normal
- El sistema subsamplea automáticamente pero toma tiempo
- Espera a que termine la renderización

### Canvas gris sin puntos
- Es posible que la nube esté fuera de la vista
- Prueba presionando "Home" en la barra de herramientas matplotlib
- O usa el scroll para hacer zoom out

## Ejemplos de Uso

### Calibración de sensores
```
1. Carga frame del bag
2. Visualiza nube 3D
3. Rota la vista para inspeccionar desde diferentes ángulos
4. Verifica alineación con otras cámaras
```

### Análisis de obstáculos
```
1. Selecciona un frame específico
2. Rota la vista 3D
3. Identifica objetos por altura (color)
4. Analiza distribución espacial
```

### Validación de datos
```
1. Carga varios frames secuencialmente
2. Compara nubes de puntos en 3D
3. Verifica que los puntos se mueven suavemente
4. Detecta anomalías o artefactos
```

## Referencia Técnica

### Imports Agregados
```python
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
```

### Clase Principal
```python
class SensorTab3D(QWidget):
    def draw_3d_pointcloud(pc):
        """Dibuja nube de puntos en 3D"""
        # Limpia NaN/Inf
        # Colorea por altura (Z)
        # Subsamplea si > 10,000 puntos
        # Renderiza scatter 3D interactivo
```

### Formato de Datos
```python
data = {
    'timestamp': float,        # Segundos desde epoch
    'pointcloud': np.array,    # Shape (N, 3) o (N, 4) - X, Y, Z, [intensity]
    'images': dict,            # Imágenes de cámaras
}
```

## Mejoras Futuras

- [ ] Exportar visualización 3D a archivos (PNG, PDF)
- [ ] Cargar múltiples frames en paralelo
- [ ] Herramientas de medición de distancias en 3D
- [ ] Filtrado de puntos por rango Z
- [ ] OpenGL backend para mejor performance
- [ ] Anotaciones 3D sobre puntos
