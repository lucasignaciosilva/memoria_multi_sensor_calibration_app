#!/usr/bin/env python3
"""
Guía: Cómo usar el Modo ROS En Vivo para detectar /velodyne_points_interpolated
"""

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║           GUÍA: CONECTAR A ROS EN VIVO PARA VER AMBOS TÓPICOS              ║
╚════════════════════════════════════════════════════════════════════════════╝

🎯 OBJETIVO
───────────
Visualizar AMBOS tópicos de LiDAR simultáneamente:
• /velodyne_points (datos crudos del bag)
• /velodyne_points_interpolated (generado por el pipeline ROS)

📋 REQUISITOS
─────────────
✅ ROS instalado y funcionando
✅ roscore ejecutándose
✅ El launch file corriendo

🚀 PASOS PARA IMPLEMENTAR
─────────────────────────

1️⃣  TERMINAL 1: Lanza el pipeline de interpolación
   ─────────────────────────────────────────────────
   
   $ cd /home/lucassilva/workspace/src/rosbag_launcher
   $ roslaunch rosbag_launcher play_zed_lidar.launch

   Esperado:
   • Ver mensajes como "Playing bag file"
   • El pipeline ROS genera /velodyne_points_interpolated
   • Los tópicos están disponibles en el ROS master

2️⃣  TERMINAL 2: Ejecuta la GUI en modo ROS en vivo
   ───────────────────────────────────────────────
   
   $ cd /home/lucassilva/workspace/src/calibrator_gui
   $ python3 scripts/gui_main.py

   En la GUI:
   • Se abre un diálogo: "¿Cómo deseas cargar los datos?"
   • Haz clic en "🔴 Conectarse a ROS en vivo"
   • La GUI se conecta al ROS master
   • Automáticamente detecta:
     ✓ /velodyne_points (del bag)
     ✓ /velodyne_points_interpolated (generado por pipeline)

3️⃣  En la Pestaña LiDAR (2D)
   ───────────────────────────
   
   ┌─────────────────────────────────┐
   │ 📡 Información de LiDAR         │
   ├─────────────────────────────────┤
   │ Tópico: [/velodyne_points ▼]  │  ← SELECTOR
   │         • /velodyne_points        │
   │         • /velodyne_points_int... │  ← Ambos visibles
   ├─────────────────────────────────┤
   │ Timestamp: ...                  │
   │ Puntos: ...                     │
   └─────────────────────────────────┘

4️⃣  En la Pestaña Vista 3D
   ─────────────────────────
   
   ┌──────────────────────────────────┐
   │ 📡 Tópico LiDAR: [/velodyne_points_int... ▼]
   ├──────────────────────────────────┤
   │                                  │
   │  [Visualización 3D]              │
   │                                  │
   │  Puedes seleccionar diferente    │
   │  que la pestaña 2D               │
   └──────────────────────────────────┘

💡 VENTAJAS DEL MODO ROS EN VIVO
────────────────────────────────

✓ VE TÓPICOS GENERADOS DINÁMICAMENTE
  El pipeline genera /velodyne_points_interpolated en tiempo real
  
✓ ACTUALIZACIÓN CONTINUAEN VIVO
  No necesitas recargar frames
  Los datos se actualizan automáticamente

✓ COMPARACIÓN EN TIEMPO REAL
  La pestaña 2D puede mostrar: /velodyne_points
  La pestaña 3D puede mostrar: /velodyne_points_interpolated
  
✓ COMPATIBLE CON MÚLTIPLES TÓPICOS
  Si el bag tiene varios LiDAR, los verás todos

🎛️  CAMBIAR ENTRE TÓPICOS
──────────────────────────

Cuando estés en la GUI:

ANTES:  Mostraba solo /velodyne_points
        El selector estaba vacío porque el bag no tenía interpolated

AHORA:  La GUI detecta /velodyne_points_interpolated (generado por ROS)
        El selector muestra AMBOS tópicos
        Puedes cambiar en tiempo real

┌─ Pestaña 2D ─┐      ┌─ Pestaña 3D ─┐
│              │      │              │
│ Selector:    │      │ Selector:    │
│ /velodyne    │  VS  │ /velodyne_   │
│ _points      │      │ points_inter │
│              │      │ polated      │
└──────────────┘      └──────────────┘

👉 FLUJO RECOMENDADO
────────────────────

Terminal 1:  roslaunch ... (Esperar a que esté listo)
             ↓ (Esperar ~5 segundos para que el pipeline arranque)
Terminal 2:  python3 gui_main.py → "🔴 Conectarse a ROS en vivo"
             ↓
GUI:         Detecta automáticamente ambos tópicos
             ↓
Pestaña LiDAR: Selector muestra ambas opciones
              ↓
Pestaña 3D:   Puedes elegir independiente

⚙️  SI ALGO NO FUNCIONA
─────────────────────

❌ No aparecen tópicos en el selector
   → Verifica que el launch file está ejecutando
   → Abre otra terminal y ejecuta: rostopic list | grep velodyne
   → Deberías ver:
        /velodyne_points
        /velodyne_points_interpolated

❌ La GUI no se conecta a ROS
   → Verifica que roscore está corriendo
   → Intenta: rosnode list
   → Deberías ver nodos listados

❌ Solo aparece un tópico
   → Espera a que el pipeline arroje puntos interpolados
   → El pipeline necesita tiempo para procesar

🔄 INICIAR DE NUEVO
───────────────────

Si necesitas reiniciar:

1. Detén la GUI (Ctrl+C en Terminal 2)
2. Detén el launch (Ctrl+C en Terminal 1)
3. Si falla: killall -9 rosbag
4. Vuelve a empezar desde Terminal 1

📝 RESUMEN DE CAMBIOS EN LA GUI
──────────────────────────────

ANTES (Solo archivos .bag):
  1. Abrías un archivo .bag → Se cargaban datos
  2. Selector mostraba solo tópicos EN EL BAG
  3. /velodyne_points_interpolated no existía → No se mostraba

AHORA (Archivos .bag + ROS en vivo):
  1. Diálogo te pregunta: "¿Archivo o ROS?"
  2. Si eliges ROS: Se conecta al master
  3. Detecta tópicos que SE GENERAN DINÁMICAMENTE
  4. /velodyne_points_interpolated APARECE si el pipeline lo crea

""")

print("\n" + "="*80)
print("✅ IMPLEMENTACIÓN COMPLETADA")
print("="*80)

print("""

ARCHIVOS NUEVOS/MODIFICADOS:
───────────────────────────

Nuevo:
  ✨ scripts/rosbag_backend/ros_live_listener.py
     └─ Escucha tópicos ROS en vivo
     └─ Detecta automáticamente nuevos tópicos
     └─ Retorna datos en formato compatible

Modificado:
  ✏️  scripts/gui_main.py
      ├─ Agregó selector: "¿Archivo o ROS?"
      ├─ Agregó método _connect_ros_live()
      ├─ Agregó método update_display_ros()
      ├─ Agregó timer para actualización en vivo
      └─ Variables: is_ros_mode, ros_live_loader, ros_update_timer

  ✏️  scripts/rosbag_backend/message_loader.py
      └─ Retorna data['pointclouds'] con TODOS los tópicos

¿LISTO?
──────

Cuando ejecutes: python3 scripts/gui_main.py

La GUI te preguntará al inicio:

   [📂 Abrir archivo .bag    ]  ← Modo tradicional
   [🔴 Conectarse a ROS en vivo]  ← NUEVO: Para ver topics dinámicos

¡Elige la segunda opción para ver /velodyne_points_interpolated!

""")
