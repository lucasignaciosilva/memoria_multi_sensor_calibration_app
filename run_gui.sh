#!/bin/bash
# Script wrapper para ejecutar GUI con configuración correcta de Qt

# Configurar variables de entorno ANTES de ejecutar python
export QT_QPA_PLATFORM_PLUGIN_PATH="/home/lucassilva/.local/lib/python3.8/site-packages/PyQt5/Qt5/plugins"
export QT_API="pyqt5"

# Force use of system xcb instead of cv2's bundled Qt
export QT_QPA_PLATFORM="xcb"
export LD_LIBRARY_PATH="/home/lucassilva/.local/lib/python3.8/site-packages/PyQt5/Qt5/lib:$LD_LIBRARY_PATH"

# Disable cv2 GUI warnings
export OPENCV_VIDEOIO_DEBUG=0
export OPENCV_LOG_LEVEL=OFF

# Ejecutar GUI
cd "$(dirname "$0")"
python3 scripts/gui_main.py "$@"
