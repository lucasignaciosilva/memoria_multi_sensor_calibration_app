# Controles de Zoom y Tamaño de Puntos - Guía de Uso

## 🎮 Nuevos Controles en la Vista 3D

### Panel de Control Inferior

En la parte inferior de la pestaña "🎲 Vista 3D" encontrarás dos controles principales:

```
🔍 Zoom: [════o════] | ● Tamaño puntos: [════o════]
0.1x                5.0x                0.5          10.0
```

### Métodos de Control

**Hay 3 formas de controlar el zoom:**

1. **Slider Zoom**: Arrastra el deslizador
2. **Rueda del mouse**: Scroll sobre el canvas 3D (✨ NUEVO)
3. **Mouse scroll**: Si lo prefieres directamente sin slider

## 🔍 Control de Zoom

### Descripción
Permite **acercar y alejar** la vista de la nube de puntos.

### Rango
- **Mínimo**: 0.1x (zoom out - ver todo desde lejos)
- **Máximo**: 5.0x (zoom in - mucho acercamiento)
- **Por defecto**: 1.0x (vista normal)

### Métodos de Control

#### Método 1: Slider de Zoom (Manual)
1. En la pestaña "🎲 Vista 3D", busca **"🔍 Zoom:"**
2. Arrastra el deslizador:
   - **Hacia la izquierda** → Alejar (ver más área)
   - **Hacia la derecha** → Acercar (detalle de zona específica)

#### Método 2: Rueda del Mouse (Recomendado) ✨
1. Coloca el mouse **sobre el canvas 3D** (la visualización)
2. **Scroll arriba** (rueda hacia ti):
   - Acerca la vista (+10% zoom)
   - Pulsa varias veces para acercar progresivamente
3. **Scroll abajo** (rueda hacia afuera):
   - Aleja la vista (-10% zoom)
   - Pulsa varias veces para alejar progresivamente

**Ventajas del scroll:**
- ✅ Más rápido que mover el slider
- ✅ Más intuitivo (como en Google Maps, Blender, etc)
- ✅ El slider se sincroniza automáticamente
- ✅ Incremenro suave (10% por scroll)

### Ejemplos Prácticos
```
Zoom = 0.1x  → Ves todos los puntos a distancia
             → Ideal para obtener vista general de toda la escena

Zoom = 1.0x  → Vista normal equilibrada
             → Recomendado para visualización general

Zoom = 5.0x  → Muy acercado
             → Ideal para inspeccionar detalle de puntos específicos
```

### Combinación con Mouse
- El control de zoom es **independiente** de los controles de mouse
- Puedes usar el **scroll del mouse** para zoom adicional
- O ajustar con el slider para cambios precisos

## ● Tamaño de Puntos

### Descripción
Ajusta el **tamaño de visualización de los puntos** de la nube.

### Rango
- **Mínimo**: 0.5 (puntos muy pequeños)
- **Máximo**: 10.0 (puntos grandes)
- **Por defecto**: 2.0 (tamaño normal)

### Cómo Usar
1. Con un frame cargado en la vista 3D
2. Usa el slider de Tamaño Puntos:
   - **Arrastra a la izquierda** → Puntos más pequeños
   - **Arrastra a la derecha** → Puntos más grandes

### Ejemplos de Uso
```
Tamaño = 0.5   → Puntos casi invisibles
              → Util cuando tienes muchos puntos (>50k)
              → Permite ver estructura general sin saturación visual

Tamaño = 2.0   → Tamaño normal (por defecto)
              → Buen balance entre detalle y claridad
              → Recomendado para la mayoría de casos

Tamaño = 10.0  → Puntos muy grandes
              → Util para nubes pequeñas (<1k puntos)
              → Facilita identificación individual de puntos
```

## 🎯 Casos de Uso Comunes

### Caso 1: Inspeccionar Objeto Específico
```
1. Usa rueda del mouse: scroll arriba 2-3 veces (zoom ~3.0x)
2. Tamaño = 5.0 (puntos más visibles)
3. Usa mouse para rotar y examinar desde diferentes ángulos
```

### Caso 2: Obtener Vista General
```
1. Usa rueda del mouse: scroll abajo 3-4 veces (zoom ~0.5x)
2. Tamaño = 1.0 (puntos pequeños para no saturar)
3. Analiza distribución espacial general de puntos
```

### Caso 3: Analizar Nube Pequeña (<2k puntos)
```
1. Zoom por defecto: 1.0x (o rueda para ajustar)
2. Tamaño = 5.0 (puntos grandes para claridad)
3. Rota con mouse para ver desde todos los ángulos
4. Usa scroll para zoom fino mientras inspeccionas
```

### Caso 4: Analizar Nube Grande (>50k puntos, subsampled a 10k)
```
1. Usa rueda: scroll arriba 1-2 veces (zoom moderado ~2.0x)
2. Tamaño = 0.5 (puntos pequeños)
3. Evita saturación visual de puntos superpuestos
4. Scroll suave (±10% por cada scroll) para control fino
```

## 🖱️ Interacción Completa

### Controles Mouse (en el canvas)
- **Arrastrar**: Rotar vista 3D (y mantiene la posición al hacer zoom)
- **Scroll arriba**: Zoom +10% (acerca manteniendo rotación)
- **Scroll abajo**: Zoom -10% (aleja manteniendo rotación)
- **Click derecho + Arrastrar**: Trasladar (pan)

### Características Especiales

#### Mantener Posición al Hacer Zoom ✨
- Cuando rotates el gráfico y luego haces zoom, **la rotación se mantiene**
- Cambiar tamaño de puntos **también preserva la posición**
- Solo cuando cargas un **frame nuevo**, la vista se resetea a la posición inicial

**Cómo funciona:**
```
1. Usuario carga frame → Vista inicial (elev=30°, azim=-60°)
2. Usuario rota con mouse → Posición se actualiza (elev=20°, azim=45°)
3. Usuario hace zoom (scroll) → Posición se mantiene (elev=20°, azim=45°)
4. Usuario carga nuevo frame → Vista se resetea a inicial
```

### Controles Sliders (en panel inferior)
- **Slider Zoom**: Acerca/aleja la vista (alternativa al scroll)
- **Slider Tamaño**: Aumenta/reduce tamaño de puntos

### Controles Combinados Recomendados
```
Exploración Rápida:
  1. Scroll del mouse para zoom dinámico
  2. Arrastrar mouse para rotar
  3. Slider de tamaño para ajustar visibilidad

Inspección Detallada:
  1. Scroll para zoom fino
  2. Mantén el mouse sobre area de interés
  3. Rota con arrastrar para ver desde ángulos
```

### Resultado Combinado
```
Mouse Scroll + Arrastrar = Control natural e intuitivo
  • Scroll = zoom dinámico (±10% por scroll)
  • Arrastrar = rotación libre
  • Ambos en tiempo real

Slider Zoom (alternativa) = Control preciso
  • Para valores exactos (0.5x, 2.0x, etc)
  • Si prefieres interfaz tradicional
  • Se sincroniza con scroll automáticamente
```

## 🔧 Ajustes Técnicos

### Cómo Funciona el Zoom
- **Zoom < 1.0**: Expande el rango visible (aleja la vista)
- **Zoom = 1.0**: Rango estándar basado en datos
- **Zoom > 1.0**: Reduce el rango visible (acerca la vista)

### Cómo Funciona el Scroll
- **Scroll arriba**: `nuevo_zoom = zoom_actual × 1.1` (+10%)
- **Scroll abajo**: `nuevo_zoom = zoom_actual ÷ 1.1` (-10%)
- **Límites**: Se asegura que el zoom esté siempre en [0.1, 5.0]
- **Sincronización**: El slider se actualiza automáticamente
- **Redibujado**: Instantáneo al cambiar zoom (no requiere recargar frame)

### Cómo Funciona el Tamaño
- El parámetro `s` del scatter plot de matplotlib
- Rango: 0.5 (mínimo) a 10.0 (máximo)
- Cambios se aplican inmediatamente sin recargar el frame

## 💡 Consejos Pro

1. **Performance**: Si la visualización es lenta con zoom alto:
   - Reduce el tamaño de puntos
   - El sistema subsamplea a 10,000 si hay más puntos

2. **Precisión**: Para mediciones visuales:
   - Zoom cercano + tamaño mediano
   - Verifica los ejes (etiquetados en metros)

3. **Análisis Rápido**: Para exploración general:
   - Zoom fuera + tamaño pequeño
   - Todos los puntos en pantalla
   - Rota con mouse para cambiar perspectiva

4. **Documentación**: Los valores de zoom y tamaño NO se guardan:
   - Se reinician al cargar un nuevo frame
   - Vuelven a valores por defecto (1.0x, 2.0)

## 📊 Resumen de Controles

| Control | Min | Defecto | Max | Unidad | Efecto |
|---------|-----|---------|-----|--------|--------|
| Zoom | 0.1 | 1.0 | 5.0 | Factor | Acerca/aleja la vista |
| Tamaño | 0.5 | 2.0 | 10.0 | Escala | Aumenta/reduce puntos |

## 🚀 Próximas Extensiones (Futuro)

- [ ] Recordar últimos valores de zoom/tamaño
- [ ] Presets de zoom (Home, Fit All, etc)
- [ ] Filtrado de puntos por rango Z
- [ ] Herramientas de medición en 3D
- [ ] Exportar vista como imagen PNG
