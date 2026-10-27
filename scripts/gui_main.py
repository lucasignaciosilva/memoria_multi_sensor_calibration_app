#!/usr/bin/env python3
"""
Fase 5: GUI Interactiva PyQt5 para Visor Rosbag 3D
Versión simplificada sin QThread para evitar conflictos con cv2
"""

# ============================================================================
# CONFIGURACIÓN DE QT PRIMERO - Antes de cualquier otro import
# ============================================================================
import os
import sys

# Disable cv2 GUI features completely to avoid Qt conflicts
os.environ['OPENCV_VIDEOIO_DEBUG'] = '0'
os.environ['OPENCV_LOG_LEVEL'] = 'OFF'

os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = "/home/lucassilva/.local/lib/python3.8/site-packages/PyQt5/Qt5/plugins"
os.environ['QT_API'] = 'pyqt5'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

# Evitar conflictos con cv2 Qt plugins - set BEFORE importing anything
os.environ['QT_QPA_PLATFORM'] = 'xcb'  # Force xcb instead of using cv2's plugins

if 'LD_LIBRARY_PATH' in os.environ:
    os.environ['LD_LIBRARY_PATH'] = "/home/lucassilva/.local/lib/python3.8/site-packages/PyQt5/Qt5/lib:" + os.environ['LD_LIBRARY_PATH']
else:
    os.environ['LD_LIBRARY_PATH'] = "/home/lucassilva/.local/lib/python3.8/site-packages/PyQt5/Qt5/lib"

# ============================================================================
# IMPORTS DESPUÉS DE CONFIGURAR ENTORNO
# ============================================================================
import time
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any

# Import PyQt5 FIRST, before anything else
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QSpinBox, QDoubleSpinBox,
    QLabel, QLineEdit, QFrame, QGroupBox, QGridLayout,
    QMessageBox, QFileDialog, QStatusBar, QProgressBar, QDialog,
    QScrollArea, QComboBox, QCheckBox, QSlider, QListWidget, QListWidgetItem, QTextEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QColor, QPixmap, QImage

import numpy as np

# Matplotlib for 3D visualization
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from mpl_toolkits.mplot3d import Axes3D

# ============================================================================
# CORRECCIÓN DE FRAME ÓPTICO (cámara ZED / stereo)
# ============================================================================
# Intercambio visual que se aplicaba para normalizar la convención óptica de
# cámara. Se desactiva por defecto para dejar la nube en la orientación que
# entrega el sensor/TF real, sin una remap visual adicional.
# Si en algún momento quieres reactivar la corrección, solo cambia este flag a True.
ENABLE_OPTICAL_FRAME_SWAP = False

# Frame óptico de cámara (REP-103): X→derecha, Y→abajo, Z→adelante.
# Swap empírico validado en la pestaña 3D principal:
#   X_plot = -Z_cam, Y_plot = X_cam, Z_plot = -Y_cam
# IMPORTANTE: usar esta única función en TODOS los lugares donde se dibuje
# una nube de puntos de una cámara óptica (stereo/zed/rgb), para que las
# pestañas nunca vuelvan a desincronizarse en orientación.
_OPTICAL_SENSOR_KEYWORDS = ('point_cloud', 'cloud_registered', 'depth/points',
                            'zed', 'realsense', 'rgbd', 'stereo', 'rgb')


def is_optical_camera_source(label: str) -> bool:
    """label puede ser un topic ROS o un nombre de sensor ('stereo', 'lidar', ...)."""
    label = (label or '').lower()
    return any(kw in label for kw in _OPTICAL_SENSOR_KEYWORDS)


def apply_optical_frame_swap(pts_xyz: np.ndarray) -> np.ndarray:
    """Convierte puntos crudos en frame óptico de cámara a la convención
    usada para graficar. Si el swap visual está deshabilitado, devuelve los
    puntos tal cual llegan del sensor."""
    pts_xyz = np.asarray(pts_xyz, dtype=float)
    if not ENABLE_OPTICAL_FRAME_SWAP or pts_xyz.size == 0:
        return pts_xyz.copy()

    x = -pts_xyz[:, 2]   # -Z_cam → X_plot
    y = pts_xyz[:, 0]    #  X_cam → Y_plot
    z = -pts_xyz[:, 1]   # -Y_cam → Z_plot
    return np.column_stack([x, y, z])

sys.path.insert(0, str(Path(__file__).parent))


def numpy_to_qpixmap(img_array: np.ndarray, max_width: int = 640, max_height: int = 480) -> QPixmap:
    """
    Convierte un array numpy a QPixmap con escalado automático.
    
    Args:
        img_array: Array numpy con shape (H, W) o (H, W, C)
        max_width: Ancho máximo
        max_height: Altura máxima
    
    Returns:
        QPixmap escalado
    """
    if img_array is None or len(img_array) == 0:
        return QPixmap()
    
    h, w = img_array.shape[:2]
    
    # Limpiar NaN e Inf antes de procesar
    img_array = np.nan_to_num(img_array, nan=0.0, posinf=255.0, neginf=0.0)
    
    # Normalizar datos si es necesario
    if img_array.dtype == np.float32 or img_array.dtype == np.float64:
        # Para imágenes térmicas o en rango [0, 1]
        if img_array.max() <= 1.0:
            img_display = (img_array * 255).astype(np.uint8)
        else:
            # Normalizar al rango [0, 255]
            img_min = img_array.min()
            img_max = img_array.max()
            if img_max > img_min:
                img_display = ((img_array - img_min) / (img_max - img_min) * 255).astype(np.uint8)
            else:
                img_display = np.zeros_like(img_array, dtype=np.uint8)
    else:
        img_display = img_array
    
    # Escalar si es necesario
    scale = min(max_width / w, max_height / h, 1.0)
    if scale < 1.0:
        new_w, new_h = int(w * scale), int(h * scale)
        import cv2
        img_display = cv2.resize(img_display, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Manejar diferentes formatos de imagen
    if len(img_display.shape) == 2:
        # Imagen en escala de grises
        h, w = img_display.shape
        bytes_per_line = w
        q_img = QImage(img_display.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
    elif len(img_display.shape) == 3:
        h, w, c = img_display.shape
        if c == 3:
            # RGB
            bytes_per_line = 3 * w
            q_img = QImage(img_display.data, w, h, bytes_per_line, QImage.Format_RGB888)
        elif c == 4:
            # RGBA
            bytes_per_line = 4 * w
            q_img = QImage(img_display.data, w, h, bytes_per_line, QImage.Format_RGBA8888)
        else:
            return QPixmap()
    else:
        return QPixmap()
    
    return QPixmap.fromImage(q_img)


# DON'T import rosbag_backend at module level - it imports cv2 which causes Qt conflicts
# Instead, import it lazily in main() after QApplication is created
BagIndexer = None
FrameNavigator = None
MessageLoader = None
ROSLiveListener = None


def _ensure_backend_imported():
    """Import backend modules after QApplication is created."""
    global BagIndexer, FrameNavigator, MessageLoader, ROSLiveListener
    
    if BagIndexer is not None:
        return  # Already imported
    
    try:
        from rosbag_backend import BagIndexer as BI, FrameNavigator as FN, MessageLoader as ML
        from rosbag_backend.ros_live_listener import ROSLiveListener as RL
        BagIndexer = BI
        FrameNavigator = FN
        MessageLoader = ML
        ROSLiveListener = RL
    except ImportError as e:
        print(f"Warning: No se puede importar ROSLiveListener: {e}")
        backend_path = Path(__file__).parent / 'rosbag_backend' / '__init__.py'
        if backend_path.exists():
            spec = importlib.util.spec_from_file_location("rosbag_backend", backend_path)
            rosbag_backend = importlib.util.module_from_spec(spec)
            sys.modules['rosbag_backend'] = rosbag_backend
            spec.loader.exec_module(rosbag_backend)
            BagIndexer = rosbag_backend.BagIndexer
            FrameNavigator = rosbag_backend.FrameNavigator
            MessageLoader = rosbag_backend.MessageLoader
            # Intentar importar ROSLiveListener también
            try:
                from rosbag_backend.ros_live_listener import ROSLiveListener as RL
                ROSLiveListener = RL
            except:
                ROSLiveListener = None
        else:
            raise ImportError("No se puede encontrar rosbag_backend")


# ============================================================================
# DIÁLOGO DE SELECCIÓN DE SENSORES
# ============================================================================

class SensorSelectionDialog(QDialog):
    """Diálogo para seleccionar qué sensores habilitar/deshabilitar."""
    
    def __init__(self, parent=None, available_sensors=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Sensores Activos")
        self.setGeometry(300, 300, 400, 300)
        self.setModal(True)
        
        self.sensor_checks = {}
        self.available_sensors = available_sensors or {}
        
        self.init_ui()
    
    def init_ui(self):
        """Inicializa la interfaz."""
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Selecciona los sensores a procesar:"))
        layout.addWidget(QLabel("(Desactivar sensores mejora el rendimiento)"))
        layout.addSpacing(10)
        
        # Checkboxes para cada sensor
        sensors_config = [
            ("stereo", "📷 Cámara Estéreo (RGB)"),
            ("thermal", "🔥 Cámara Térmica"),
            ("lidar", "📡 LiDAR / PointCloud"),
        ]
        
        for sensor_id, sensor_label in sensors_config:
            # Verificar si el sensor está disponible
            is_available = sensor_id in self.available_sensors
            
            check = QCheckBox(sensor_label)
            check.setChecked(is_available)  # Habilitar por defecto si existe
            check.setEnabled(is_available)  # Deshabilitado si no existe
            
            if not is_available:
                check.setText(sensor_label + " (no disponible)")
            
            self.sensor_checks[sensor_id] = check
            layout.addWidget(check)
        
        layout.addSpacing(20)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_all = QPushButton("Todos")
        btn_all.clicked.connect(lambda: self.set_all_checked(True))
        btn_layout.addWidget(btn_all)
        
        btn_none = QPushButton("Ninguno")
        btn_none.clicked.connect(lambda: self.set_all_checked(False))
        btn_layout.addWidget(btn_none)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addSpacing(10)
        
        # OK/Cancel
        dialog_btn_layout = QHBoxLayout()
        btn_ok = QPushButton("✓ Aceptar")
        btn_ok.clicked.connect(self.accept)
        dialog_btn_layout.addWidget(btn_ok)
        
        btn_cancel = QPushButton("✗ Cancelar")
        btn_cancel.clicked.connect(self.reject)
        dialog_btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(dialog_btn_layout)
        self.setLayout(layout)
    
    def set_all_checked(self, checked: bool):
        """Marca/desmarca todos los sensores disponibles."""
        for sensor_id, check in self.sensor_checks.items():
            if check.isEnabled():
                check.setChecked(checked)
    
    def get_selected_sensors(self) -> dict:
        """Retorna diccionario con sensores habilitados."""
        return {sensor_id: check.isChecked() 
                for sensor_id, check in self.sensor_checks.items()}


# ============================================================================
# WIDGETS DE SENSORES
# ============================================================================

class SensorTabStereoCamera(QWidget):
    """Pestaña para visualización de cámara estéreo RGB."""
    
    def __init__(self):
        super().__init__()
        self.last_image_topic = None
        self.last_image_data = None
        self.available_rgb_topics = []
        self.selected_rgb_topic = None
        self._user_override = False
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        group = QGroupBox("📷 Información de Cámara Estéreo (RGB)")
        grid = QGridLayout()
        
        self.timestamp_label = QLabel("Timestamp: --")
        self.resolution_label = QLabel("Resolución: --")
        self.frequency_label = QLabel("Frecuencia: --")
        
        # Selector de tópico
        grid.addWidget(QLabel("Tópico:"), 0, 0)
        self.topic_combo = QComboBox()
        self.topic_combo.currentTextChanged.connect(self.on_topic_changed)
        grid.addWidget(self.topic_combo, 0, 1)
        
        grid.addWidget(self.timestamp_label, 1, 0, 1, 2)
        grid.addWidget(self.resolution_label, 2, 0, 1, 2)
        grid.addWidget(self.frequency_label, 3, 0, 1, 2)
        
        group.setLayout(grid)
        layout.addWidget(group)
        
        # Scroll area para la imagen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.image_label = QLabel()
        self.image_label.setMinimumHeight(300)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background: #000;")
        self.image_label.setAlignment(Qt.AlignCenter)
        scroll.setWidget(self.image_label)
        layout.addWidget(scroll, 1)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def on_topic_changed(self):
        """Manejador cuando cambia el tópico seleccionado."""
        self.selected_rgb_topic = self.topic_combo.currentText()
        self._user_override = True

    def update_available_topics(self, available_topics: list):
        """Actualiza la lista de tópicos disponibles."""
        self.available_rgb_topics = available_topics

        if self._user_override and self.selected_rgb_topic:
            current_topic = self.selected_rgb_topic
            self.topic_combo.blockSignals(True)
            self.topic_combo.clear()
            self.topic_combo.addItems(available_topics)
            if self.topic_combo.findText(current_topic) < 0:
                self.topic_combo.addItem(current_topic)
            self.topic_combo.setCurrentText(current_topic)
            self.topic_combo.blockSignals(False)
            return

        current_topic = self.topic_combo.currentText()
        self.topic_combo.blockSignals(True)
        self.topic_combo.clear()
        self.topic_combo.addItems(available_topics)

        if current_topic in available_topics:
            self.topic_combo.setCurrentText(current_topic)
        elif available_topics:
            self.selected_rgb_topic = available_topics[0]

        self.topic_combo.blockSignals(False)

    def set_all_topics(self, all_topics: list):
        """Repuebla el combo con TODOS los tópicos del bag/ROS.
        Los tópicos RGB recomendados aparecen primero; el resto al final."""
        recommended = [t for t in all_topics
                       if 'thermal' not in t.lower() and 'flir' not in t.lower()
                       and 'velodyne' not in t.lower() and 'lidar' not in t.lower()
                       and 'pointcloud' not in t.lower()]
        others = [t for t in all_topics if t not in recommended]

        current_topic = self.selected_rgb_topic if self._user_override else self.topic_combo.currentText()

        self.topic_combo.blockSignals(True)
        self.topic_combo.clear()

        if recommended:
            for t in recommended:
                self.topic_combo.addItem(t)
        if others:
            self.topic_combo.insertSeparator(self.topic_combo.count())
            for t in others:
                self.topic_combo.addItem(t)

        if current_topic and self.topic_combo.findText(current_topic) >= 0:
            self.topic_combo.setCurrentText(current_topic)
        elif current_topic and self._user_override:
            self.topic_combo.addItem(current_topic)
            self.topic_combo.setCurrentText(current_topic)
        elif recommended and not self._user_override:
            self.selected_rgb_topic = recommended[0]
            self.topic_combo.setCurrentText(recommended[0])

        self.topic_combo.blockSignals(False)

    def update_data(self, data: Dict[str, Any]):
        """Actualiza datos de cámara estéreo."""
        if 'timestamp' in data and data['timestamp']:
            self.timestamp_label.setText(f"Timestamp: {data['timestamp']:.6f}")
        
        if 'images' in data and data['images']:
            # Si no hay tópico seleccionado, seleccionar el primero disponible
            if not self.selected_rgb_topic:
                for topic in data['images'].keys():
                    if 'thermal' not in topic.lower() and 'flir' not in topic.lower():
                        self.selected_rgb_topic = topic
                        break
            
            # Mostrar imagen del tópico seleccionado
            if self.selected_rgb_topic in data['images']:
                img_array = data['images'][self.selected_rgb_topic]
                if img_array is not None and len(img_array) > 0:
                    h, w = img_array.shape[:2]
                    self.resolution_label.setText(f"Resolución: {w}x{h}")
                    self.frequency_label.setText("Frecuencia: 30 Hz")
                    
                    # Renderizar imagen
                    try:
                        pixmap = numpy_to_qpixmap(img_array, max_width=640, max_height=480)
                        if not pixmap.isNull():
                            self.image_label.setPixmap(pixmap)
                            self.last_image_topic = self.selected_rgb_topic
                            self.last_image_data = img_array
                        else:
                            self.image_label.setText("Error: No se pudo renderizar imagen")
                    except Exception as e:
                        self.image_label.setText(f"Error renderizando: {str(e)[:50]}")
                    return
            
            self.image_label.setText("No hay datos RGB disponibles")
    
    def get_selected_topic(self) -> str:
        """Retorna el tópico seleccionado actualmente."""
        return self.selected_rgb_topic or ""


class SensorTabLiDAR(QWidget):
    """Pestaña para visualización de LiDAR."""
    
    def __init__(self):
        super().__init__()
        self.last_pointcloud = None
        self.available_lidar_topics = []
        self.selected_lidar_topic = None
        self.last_data = None
        self._user_override = False
        self.init_ui()

    
    def init_ui(self):
        layout = QVBoxLayout()
        group = QGroupBox("📡 Información de LiDAR")
        grid = QGridLayout()
        
        self.timestamp_label = QLabel("Timestamp: --")
        self.points_label = QLabel("Puntos: --")
        self.range_label = QLabel("Rango: --")
        
        # Selector de tópico
        grid.addWidget(QLabel("Tópico:"), 0, 0)
        self.topic_combo = QComboBox()
        self.topic_combo.currentTextChanged.connect(self.on_topic_changed)
        grid.addWidget(self.topic_combo, 0, 1)
        
        grid.addWidget(self.timestamp_label, 1, 0, 1, 2)
        grid.addWidget(self.points_label, 2, 0, 1, 2)
        grid.addWidget(self.range_label, 3, 0, 1, 2)
        
        group.setLayout(grid)
        layout.addWidget(group)
        
        # Visualización 2D de la nube de puntos (vista XY)
        self.canvas_label = QLabel()
        self.canvas_label.setMinimumHeight(400)
        self.canvas_label.setStyleSheet("border: 1px solid #ccc; background: #1a1a1a;")
        self.canvas_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.canvas_label, 1)
        
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("background: #f5f5f5; padding: 8px; border-radius: 4px;")
        layout.addWidget(self.stats_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def draw_pointcloud_2d(self, pc: np.ndarray) -> QPixmap:
        """Dibuja una proyección 2D de la nube de puntos (vista XY)."""
        try:
            if pc is None or len(pc) == 0:
                return QPixmap()
            
            # Limpiar NaN e Inf en los datos
            pc = np.nan_to_num(pc, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Dimensiones del canvas
            canvas_w, canvas_h = 640, 400
            
            # Crear imagen blanca
            img = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8) * 26  # Fondo oscuro (#1a1a1a)
            
            # Extraer X, Y, Z
            x = pc[:, 0]
            y = pc[:, 1]
            z = pc[:, 2]
            
            # Calcular rango
            x_min, x_max = x.min(), x.max()
            y_min, y_max = y.min(), y.max()
            
            # Evitar división por cero
            x_range = x_max - x_min if x_max != x_min else 1
            y_range = y_max - y_min if y_max != y_min else 1
            
            # Normalizar y escalar a coordenadas de pixel
            margin = 20
            px_x = np.clip(((x - x_min) / x_range * (canvas_w - 2*margin) + margin).astype(np.int32), 0, canvas_w - 1)
            px_y = np.clip((canvas_h - (y - y_min) / y_range * (canvas_h - 2*margin) - margin).astype(np.int32), 0, canvas_h - 1)
            
            # Colorear por altura (Z)
            z_min, z_max = z.min(), z.max()
            z_range = z_max - z_min if z_max != z_min else 1
            z_normalized = (z - z_min) / z_range
            
            # Dibujar puntos
            for i in range(0, len(pc), max(1, len(pc) // 1000)):  # Subsample si hay muchos puntos
                px, py = px_x[i], px_y[i]
                if 0 <= px < canvas_w and 0 <= py < canvas_h:
                    # Color por altura: azul (bajo) -> rojo (alto)
                    color_val = int(np.clip(z_normalized[i] * 255, 0, 255))
                    img[py, px] = [color_val, 0, 255 - color_val]
            
            # Convertir a QPixmap
            return numpy_to_qpixmap(img)
        except Exception as e:
            print(f"Error dibujando nube de puntos: {e}")
            return QPixmap()
    
    def update_data(self, data: Dict[str, Any]):
        """Actualiza datos de LiDAR."""
        self.last_data = data  # Guardar para re-renderizar cuando cambie tópico
        
        if 'timestamp' in data and data['timestamp']:
            self.timestamp_label.setText(f"Timestamp: {data['timestamp']:.6f}")
        
        # Actualizar lista de tópicos de pointcloud disponibles
        available_pointcloud_topics = []
        if 'pointclouds' in data and data['pointclouds']:
            available_pointcloud_topics = list(data['pointclouds'].keys())

        # Añadir también tópicos de imagen (p.ej. disparity) para permitir convertir a pointcloud
        imgs = data.get('images', {}) if isinstance(data, dict) else {}
        if imgs:
            for t in imgs.keys():
                if t not in available_pointcloud_topics:
                    available_pointcloud_topics.append(t)
        
        if available_pointcloud_topics != self.available_lidar_topics:
            self.available_lidar_topics = available_pointcloud_topics
            self._update_topic_combo()
        
        # Seleccionar el pointcloud según el tópico actual
        pc = None
        if self.selected_lidar_topic and 'pointclouds' in data and self.selected_lidar_topic in data['pointclouds']:
            pc = data['pointclouds'][self.selected_lidar_topic]
        elif 'pointcloud' in data and data['pointcloud'] is not None:
            # Fallback a backward compatibility
            pc = data['pointcloud']
        
        if pc is not None:
            n_points = len(pc)
            self.points_label.setText(f"Puntos: {n_points:,}")
            self.last_pointcloud = pc
            
            if n_points > 0:
                ranges = np.sqrt(np.sum(pc ** 2, axis=1))
                max_range = ranges.max()
                mean_range = ranges.mean()
                self.range_label.setText(f"Rango máx: {max_range:.2f}m")
                
                stats = (f"X: [{pc[:, 0].min():.2f}, {pc[:, 0].max():.2f}]\n"
                        f"Y: [{pc[:, 1].min():.2f}, {pc[:, 1].max():.2f}]\n"
                        f"Z: [{pc[:, 2].min():.2f}, {pc[:, 2].max():.2f}]\n"
                        f"Rango promedio: {mean_range:.2f}m")
                self.stats_label.setText(stats)
                
                # Dibujar nube de puntos
                try:
                    pixmap = self.draw_pointcloud_2d(pc)
                    if not pixmap.isNull():
                        self.canvas_label.setPixmap(pixmap)
                    else:
                        self.canvas_label.setText("Error: No se pudo renderizar")
                except Exception as e:
                    self.canvas_label.setText(f"Error: {str(e)[:50]}")
    
    def _update_topic_combo(self):
        """Actualiza el combo de tópicos."""
        current_topic = self.topic_combo.currentText()
        self.topic_combo.blockSignals(True)
        self.topic_combo.clear()
        self.topic_combo.addItems(self.available_lidar_topics)
        
        # Restaurar selección anterior si existe
        if current_topic in self.available_lidar_topics:
            self.topic_combo.setCurrentText(current_topic)
        elif self.available_lidar_topics:
            self.selected_lidar_topic = self.available_lidar_topics[0]
        
        self.topic_combo.blockSignals(False)
    
    def on_topic_changed(self):
        """Manejador cuando cambia el tópico seleccionado."""
        self.selected_lidar_topic = self.topic_combo.currentText()
        self._user_override = True
        if self.last_data:
            self.update_data(self.last_data)

    def update_available_topics(self, available_topics: list):
        """Actualiza la lista de tópicos disponibles."""
        self.available_lidar_topics = available_topics

        if self._user_override and self.selected_lidar_topic:
            current_topic = self.selected_lidar_topic
            self.topic_combo.blockSignals(True)
            self.topic_combo.clear()
            self.topic_combo.addItems(available_topics)
            if self.topic_combo.findText(current_topic) < 0:
                self.topic_combo.addItem(current_topic)
            self.topic_combo.setCurrentText(current_topic)
            self.topic_combo.blockSignals(False)
            return

        current_topic = self.topic_combo.currentText()
        self.topic_combo.blockSignals(True)
        self.topic_combo.clear()
        self.topic_combo.addItems(available_topics)

        if current_topic in available_topics:
            self.topic_combo.setCurrentText(current_topic)
        elif available_topics:
            self.selected_lidar_topic = available_topics[0]

        self.topic_combo.blockSignals(False)

    def set_all_topics(self, all_topics: list):
        """Repuebla el combo con TODOS los tópicos del bag/ROS.
        Los tópicos LiDAR/pointcloud recomendados aparecen primero; el resto al final."""
        recommended = [t for t in all_topics
                       if 'velodyne' in t.lower() or 'lidar' in t.lower()
                       or 'pointcloud' in t.lower() or 'points' in t.lower()]
        others = [t for t in all_topics if t not in recommended]

        current_topic = self.selected_lidar_topic if self._user_override else self.topic_combo.currentText()

        self.topic_combo.blockSignals(True)
        self.topic_combo.clear()

        if recommended:
            for t in recommended:
                self.topic_combo.addItem(t)
        if others:
            self.topic_combo.insertSeparator(self.topic_combo.count())
            for t in others:
                self.topic_combo.addItem(t)

        if current_topic and self.topic_combo.findText(current_topic) >= 0:
            self.topic_combo.setCurrentText(current_topic)
        elif current_topic and self._user_override:
            self.topic_combo.addItem(current_topic)
            self.topic_combo.setCurrentText(current_topic)
        elif recommended and not self._user_override:
            self.selected_lidar_topic = recommended[0]
            self.topic_combo.setCurrentText(recommended[0])

        self.topic_combo.blockSignals(False)

    def get_selected_topic(self) -> str:
        """Retorna el tópico seleccionado actualmente."""
        return self.selected_lidar_topic or ""



class SensorTabThermalCamera(QWidget):
    """Pestaña para visualización de cámara térmica."""
    
    def __init__(self):
        super().__init__()
        self.last_image_topic = None
        self.last_image_data = None
        self.available_thermal_topics = []
        self.selected_thermal_topic = None
        self._user_override = False  # True cuando el usuario eligió manualmente un tópico
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        group = QGroupBox("🔥 Información de Cámara Térmica")
        grid = QGridLayout()
        
        self.timestamp_label = QLabel("Timestamp: --")
        self.resolution_label = QLabel("Resolución: --")
        self.frequency_label = QLabel("Frecuencia: --")
        self.temp_range_label = QLabel("Rango T°: --")
        
        # Selector de tópico
        grid.addWidget(QLabel("Tópico:"), 0, 0)
        self.topic_combo = QComboBox()
        self.topic_combo.currentTextChanged.connect(self.on_topic_changed)
        grid.addWidget(self.topic_combo, 0, 1)
        
        grid.addWidget(self.timestamp_label, 1, 0, 1, 2)
        grid.addWidget(self.resolution_label, 2, 0, 1, 2)
        grid.addWidget(self.frequency_label, 3, 0, 1, 2)
        grid.addWidget(self.temp_range_label, 4, 0, 1, 2)
        
        group.setLayout(grid)
        layout.addWidget(group)
        
        # Scroll area para la imagen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.image_label = QLabel()
        self.image_label.setMinimumHeight(300)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background: #000;")
        self.image_label.setAlignment(Qt.AlignCenter)
        scroll.setWidget(self.image_label)
        layout.addWidget(scroll, 1)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def on_topic_changed(self):
        """Manejador cuando cambia el tópico seleccionado."""
        self.selected_thermal_topic = self.topic_combo.currentText()
        self._user_override = True  # El usuario eligió manualmente; respetar esta selección

    def update_available_topics(self, available_topics: list):
        """Actualiza la lista de tópicos disponibles (solo si no hay override manual)."""
        self.available_thermal_topics = available_topics

        # Si el usuario eligió manualmente un tópico, no pisar su selección
        if self._user_override and self.selected_thermal_topic:
            # Solo repoblamos el combo sin cambiar la selección
            current_topic = self.selected_thermal_topic
            self.topic_combo.blockSignals(True)
            self.topic_combo.clear()
            self.topic_combo.addItems(available_topics)
            if self.topic_combo.findText(current_topic) < 0:
                self.topic_combo.addItem(current_topic)  # Mantener aunque no esté en la lista
            self.topic_combo.setCurrentText(current_topic)
            self.topic_combo.blockSignals(False)
            return

        current_topic = self.topic_combo.currentText()
        self.topic_combo.blockSignals(True)
        self.topic_combo.clear()
        self.topic_combo.addItems(available_topics)

        if current_topic in available_topics:
            self.topic_combo.setCurrentText(current_topic)
        elif available_topics:
            self.selected_thermal_topic = available_topics[0]

        self.topic_combo.blockSignals(False)

    def set_all_topics(self, all_topics: list):
        """Repuebla el combo con TODOS los tópicos del bag/ROS.
        Los tópicos térmicos recomendados aparecen primero; el resto al final."""
        recommended = [t for t in all_topics
                       if 'thermal' in t.lower() or 'flir' in t.lower()
                       or 'infrared' in t.lower() or 'ir_' in t.lower()]
        others = [t for t in all_topics if t not in recommended]

        # Preservar selección manual del usuario
        current_topic = self.selected_thermal_topic if self._user_override else self.topic_combo.currentText()

        self.topic_combo.blockSignals(True)
        self.topic_combo.clear()

        if recommended:
            for t in recommended:
                self.topic_combo.addItem(t)
        if others:
            self.topic_combo.insertSeparator(self.topic_combo.count())
            for t in others:
                self.topic_combo.addItem(t)

        if current_topic and self.topic_combo.findText(current_topic) >= 0:
            self.topic_combo.setCurrentText(current_topic)
        elif current_topic and self._user_override:
            # El tópico elegido por el usuario no está en la lista nueva; agregarlo igual
            self.topic_combo.addItem(current_topic)
            self.topic_combo.setCurrentText(current_topic)
        elif recommended and not self._user_override:
            self.selected_thermal_topic = recommended[0]
            self.topic_combo.setCurrentText(recommended[0])

        self.topic_combo.blockSignals(False)

    def update_data(self, data: Dict[str, Any]):
        """Actualiza datos de cámara térmica."""
        if 'timestamp' in data and data['timestamp']:
            self.timestamp_label.setText(f"Timestamp: {data['timestamp']:.6f}")
        
        if 'images' in data and data['images']:
            # Auto-seleccionar solo si no hay override manual del usuario
            if not self.selected_thermal_topic and not self._user_override:
                for topic in data['images'].keys():
                    if 'thermal' in topic.lower() or 'flir' in topic.lower():
                        self.selected_thermal_topic = topic
                        break

            # Buscar la imagen: primero en 'images', luego en sub-claves si el tópico es override
            img_array = None
            if self.selected_thermal_topic:
                # Buscar en todas las imágenes disponibles (no solo las térmicas pre-filtradas)
                all_images = data.get('images', {})
                if self.selected_thermal_topic in all_images:
                    img_array = all_images[self.selected_thermal_topic]

            if img_array is not None and len(img_array) > 0:
                h, w = img_array.shape[:2]
                self.resolution_label.setText(f"Resolución: {w}x{h}")
                self.frequency_label.setText("Frecuencia: 30 Hz")

                if len(img_array) > 0:
                    min_val = img_array.min()
                    max_val = img_array.max()
                    self.temp_range_label.setText(f"Rango: {min_val:.1f} - {max_val:.1f}")

                try:
                    pixmap = numpy_to_qpixmap(img_array, max_width=640, max_height=480)
                    if not pixmap.isNull():
                        self.image_label.setPixmap(pixmap)
                        self.last_image_topic = self.selected_thermal_topic
                        self.last_image_data = img_array
                    else:
                        self.image_label.setText("Error: No se pudo renderizar imagen térmica")
                except Exception as e:
                    self.image_label.setText(f"Error renderizando: {str(e)[:50]}")
                return

            self.image_label.setText("No hay datos térmicos disponibles")
    
    def get_selected_topic(self) -> str:
        """Retorna el tópico seleccionado actualmente."""
        return self.selected_thermal_topic or ""





class SensorTab3D(QWidget):
    """Pestaña para visualización 3D del LiDAR con patrón de calibración."""
    
    def __init__(self, parent_gui=None):
        super().__init__()
        self.parent_gui = parent_gui
        self.last_pointcloud = None
        self.last_data = None
        self.available_lidar_topics = []
        self.selected_lidar_topic = None
        self._user_override = False
        self.zoom_level = 1.0
        self.point_size = 2.0
        self.current_elev = None
        self.current_azim = None
        
        # Patrón de calibración
        self.calibration_pattern = CalibrationPattern()
        self.pattern_mode = True  # Usar patrón de calibración
        
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Selector de tópico
        topic_layout = QHBoxLayout()
        topic_layout.addWidget(QLabel("📡 Tópico LiDAR:"))
        self.topic_combo = QComboBox()
        self.topic_combo.currentTextChanged.connect(self.on_topic_changed)
        topic_layout.addWidget(self.topic_combo)
        topic_layout.addStretch()
        main_layout.addLayout(topic_layout)

        # Controles para convertir disparity -> pointcloud
        disp_layout = QHBoxLayout()
        self.disparity_checkbox = QPushButton("Usar Disparity como PointCloud")
        self.disparity_checkbox.setCheckable(True)
        self.disparity_checkbox.setChecked(False)
        self.disparity_checkbox.toggled.connect(self.on_disparity_toggled)
        disp_layout.addWidget(self.disparity_checkbox)

        disp_layout.addWidget(QLabel("fx:"))
        self.fx_spin = QDoubleSpinBox(); self.fx_spin.setRange(1,5000); self.fx_spin.setValue(700); self.fx_spin.setDecimals(1)
        disp_layout.addWidget(self.fx_spin)
        disp_layout.addWidget(QLabel("fy:"))
        self.fy_spin = QDoubleSpinBox(); self.fy_spin.setRange(1,5000); self.fy_spin.setValue(700); self.fy_spin.setDecimals(1)
        disp_layout.addWidget(self.fy_spin)

        disp_layout.addWidget(QLabel("cx:"))
        self.cx_spin = QDoubleSpinBox(); self.cx_spin.setRange(0,5000); self.cx_spin.setValue(320); self.cx_spin.setDecimals(1)
        disp_layout.addWidget(self.cx_spin)
        disp_layout.addWidget(QLabel("cy:"))
        self.cy_spin = QDoubleSpinBox(); self.cy_spin.setRange(0,5000); self.cy_spin.setValue(240); self.cy_spin.setDecimals(1)
        disp_layout.addWidget(self.cy_spin)

        disp_layout.addWidget(QLabel("baseline (m):"))
        self.baseline_spin = QDoubleSpinBox(); self.baseline_spin.setRange(0.001,1.0); self.baseline_spin.setValue(0.12); self.baseline_spin.setDecimals(3)
        disp_layout.addWidget(self.baseline_spin)

        disp_layout.addStretch()
        main_layout.addLayout(disp_layout)
        
        # Crear figura de matplotlib para visualización 3D
        self.fig = Figure(figsize=(8, 6), dpi=100, facecolor='#2a2a2a')
        self.canvas = FigureCanvas(self.fig)
        
        # Conectar evento de scroll del mouse para zoom
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        # Conectar evento de click para detección manual de puntos
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)
        
        main_layout.addWidget(self.canvas, stretch=1)
        
        # Panel de información
        info_layout = QHBoxLayout()
        
        self.pointcloud_label = QLabel("LiDAR: Esperando datos...")
        self.frame_points = QLabel("Puntos: --")
        self.frame_timestamp = QLabel("Timestamp: --")
        
        info_layout.addWidget(QLabel("📊"))
        info_layout.addWidget(self.pointcloud_label)
        info_layout.addSpacing(20)
        info_layout.addWidget(self.frame_points)
        info_layout.addSpacing(20)
        info_layout.addWidget(self.frame_timestamp)
        info_layout.addStretch()
        
        main_layout.addLayout(info_layout)
        
        # Panel de controles (Zoom y tamaño de puntos)
        controls_layout = QHBoxLayout()
        
        # Control de Zoom
        controls_layout.addWidget(QLabel("🔍 Zoom:"))
        self.zoom_slider = QDoubleSpinBox()
        self.zoom_slider.setMinimum(0.1)
        self.zoom_slider.setMaximum(5.0)
        self.zoom_slider.setSingleStep(0.1)
        self.zoom_slider.setValue(1.0)
        self.zoom_slider.setMaximumWidth(100)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        controls_layout.addWidget(self.zoom_slider)
        
        controls_layout.addSpacing(30)
        
        # Control de tamaño de puntos
        controls_layout.addWidget(QLabel("● Tamaño puntos:"))
        self.size_slider = QDoubleSpinBox()
        self.size_slider.setMinimum(0.5)
        self.size_slider.setMaximum(10.0)
        self.size_slider.setSingleStep(0.5)
        self.size_slider.setValue(2.0)
        self.size_slider.setMaximumWidth(100)
        self.size_slider.valueChanged.connect(self.on_size_changed)
        controls_layout.addWidget(self.size_slider)
        
        controls_layout.addSpacing(30)
        
        # Patrón de calibración
        self.pattern_label = QLabel("📐 Patrón: Listo (24cm x 4 círculos)")
        controls_layout.addWidget(self.pattern_label)
        
        btn_reset_pattern = QPushButton("🔄 Resetear")
        btn_reset_pattern.setMaximumWidth(80)
        btn_reset_pattern.clicked.connect(self.reset_pattern)
        controls_layout.addWidget(btn_reset_pattern)
        
        btn_confirm_pattern = QPushButton("✅ Confirmar")
        btn_confirm_pattern.setMaximumWidth(80)
        btn_confirm_pattern.clicked.connect(self.confirm_pattern)
        controls_layout.addWidget(btn_confirm_pattern)
        
        controls_layout.addStretch()
        
        main_layout.addLayout(controls_layout)
        self.setLayout(main_layout)
    
    def draw_3d_pointcloud(self, pc):
        """Dibuja la nube de puntos en 3D."""
        try:
            if pc is None or len(pc) == 0:
                return
            
            # Limpiar NaN e Inf
            pc = np.nan_to_num(pc, nan=0.0, posinf=0.0, neginf=0.0)
            
            # ── Corrección de frame para cámaras en convención óptica ──────────
            # Ver apply_optical_frame_swap() / is_optical_camera_source() arriba.
            topic = getattr(self, 'selected_lidar_topic', '') or ''
            is_camera_optical = is_optical_camera_source(topic)

            if is_camera_optical:
                pc_plot_xyz = apply_optical_frame_swap(pc[:, :3])
                x, y, z = pc_plot_xyz[:, 0], pc_plot_xyz[:, 1], pc_plot_xyz[:, 2]
            else:
                x = pc[:, 0]
                y = pc[:, 1]
                z = pc[:, 2]

            # Colorear por altura (Z)
            z_min, z_max = z.min(), z.max()
            z_range = z_max - z_min if z_max != z_min else 1.0
            z_normalized = (z - z_min) / z_range
            
            # Usar RGB real si el array tiene 6 columnas (XYZRGB del backend)
            if pc.shape[1] >= 6:
                colors = np.clip(pc[:, 3:6], 0, 1)
            else:
                # Fallback: colorear por altura
                colors = plt.cm.cool(z_normalized)
            
            # Limpiar figura anterior
            self.fig.clear()
            ax = self.fig.add_subplot(111, projection='3d')
            
            # Subsample si hay muchos puntos (máximo 10000 para performance)
            if len(pc) > 10000:
                indices = np.random.choice(len(pc), 10000, replace=False)
                x_plot = x[indices]
                y_plot = y[indices]
                z_plot = z[indices]
                colors_plot = colors[indices]
            else:
                x_plot = x
                y_plot = y
                z_plot = z
                colors_plot = colors
            
            # Graficar puntos con tamaño configurable
            ax.scatter(x_plot, y_plot, z_plot, c=colors_plot, s=self.point_size, alpha=0.6)
            
            # Dibujar patrón de calibración (4 círculos)
            if self.pattern_mode:
                centers = self.calibration_pattern.get_display_circle_centers()
                radius = self.calibration_pattern.circle_radius
                
                # Dibujar cada círculo como wireframe
                for i, center in enumerate(centers):
                    # Crear puntos del círculo en 3D (proyección XY con Z fijo)
                    u = np.linspace(0, 2 * np.pi, 20)
                    circle_x = center[0] + radius * np.cos(u)
                    circle_y = center[1] + radius * np.sin(u)
                    circle_z = np.ones_like(u) * center[2]
                    
                    # Dibujar círculo
                    ax.plot(circle_x, circle_y, circle_z, 'g-', linewidth=2, label='Patrón' if i == 0 else '')
                    
                    # Marcar centro con punto rojo grande
                    ax.scatter([center[0]], [center[1]], [center[2]], c='red', s=100, marker='*')
            
            # Configurar ejes
            if is_camera_optical:
                ax.set_xlabel('-Z_cam (m)', color='black')
                ax.set_ylabel('X_cam (m)', color='black')
                ax.set_zlabel('-Y_cam / altura (m)', color='black')
                short = topic.split('/')[-1]
                ax.set_title(f'Point Cloud [{short}] — frame óptico corregido', color='black', fontsize=11)
            else:
                ax.set_xlabel('X (m)', color='black')
                ax.set_ylabel('Y (m)', color='black')
                ax.set_zlabel('Z (m)', color='black')
                ax.set_title('LiDAR Point Cloud', color='black', fontsize=12)
            
            # Aplicar zoom: reducir rango de ejes para "acercarse"
            x_range = x.max() - x.min()
            y_range = y.max() - y.min()
            z_range = z.max() - z.min()
            
            x_center = (x.min() + x.max()) / 2
            y_center = (y.min() + y.max()) / 2
            z_center = (z.min() + z.max()) / 2
            
            # Aplicar zoom (reduce el rango visible)
            zoom_factor = 1.0 / self.zoom_level
            ax.set_xlim([x_center - x_range * zoom_factor / 2, x_center + x_range * zoom_factor / 2])
            ax.set_ylim([y_center - y_range * zoom_factor / 2, y_center + y_range * zoom_factor / 2])
            ax.set_zlim([z_center - z_range * zoom_factor / 2, z_center + z_range * zoom_factor / 2])
            
            # Restaurar posición de visualización si existe (mantener rotación al hacer zoom)
            if self.current_elev is not None and self.current_azim is not None:
                ax.view_init(elev=self.current_elev, azim=self.current_azim)
            
            # Estilo oscuro
            ax.xaxis.pane.fill = False
            ax.yaxis.pane.fill = False
            ax.zaxis.pane.fill = False
            ax.xaxis.pane.set_edgecolor('gray')
            ax.yaxis.pane.set_edgecolor('gray')
            ax.zaxis.pane.set_edgecolor('gray')
            ax.tick_params(colors='black', labelsize=8)
            
            self.fig.patch.set_facecolor('#2a2a2a')
            
            # Dibujar
            self.canvas.draw_idle()
            
            # Guardar posición de visualización actual para futuros redraws
            # (cuando solo se cambia zoom/tamaño, no al cargar frame nuevo)
            try:
                self.current_elev = ax.elev
                self.current_azim = ax.azim
            except:
                # Si no están disponibles, ignorar
                pass
        
        except Exception as e:
            print(f"Error dibujando nube 3D: {e}")
    
    def on_canvas_click(self, event):
        """Maneja clics del mouse para mover el patrón de calibración."""
        if event.inaxes is None or self.last_pointcloud is None or event.button != 1:
            return
        
        try:
            # Obtener coordenadas del click
            x_click, y_click = event.xdata, event.ydata
            
            if x_click is None or y_click is None:
                return
            
            # Mover el patrón hacia el punto clicado
            self.calibration_pattern.center_x = x_click
            self.calibration_pattern.center_y = y_click
            
            print(f"📐 Patrón movido a: ({x_click:.2f}, {y_click:.2f})")
            
            # Redibujar
            self.draw_3d_pointcloud(self.last_pointcloud)
        
        except Exception as e:
            print(f"Error moviendo patrón: {e}")
    
    def reset_pattern(self):
        """Reinicia el patrón de calibración."""
        self.calibration_pattern.reset()
        print("🔄 Patrón reiniciado")
        if self.last_pointcloud is not None:
            self.draw_3d_pointcloud(self.last_pointcloud)
    
    def confirm_pattern(self):
        """Confirma la posición del patrón y guarda los 4 centros."""
        try:
            # Usar centros de visualización para que lo guardado coincida con lo que el usuario ve
            centers = self.calibration_pattern.get_display_circle_centers(self.pattern_scale)
            
            print(f"✅ Patrón confirmado con 4 centros:")
            for i, center in enumerate(centers):
                print(f"   #{i+1}: ({center[0]:.4f}, {center[1]:.4f}, {center[2]:.4f})")
            
            # Agregar al frame confirmado actual si existe
            if self.parent_gui and hasattr(self.parent_gui, 'current_confirmed_frame_idx'):
                if self.parent_gui.current_confirmed_frame_idx is not None:
                    frame_idx = self.parent_gui.current_confirmed_frame_idx
                    if 0 <= frame_idx < len(self.parent_gui.confirmed_frames):
                        # Limpiar puntos anteriores y agregar los 4 nuevos
                        self.parent_gui.confirmed_frames[frame_idx]['points'] = centers.tolist()
                        self.parent_gui._update_confirmed_frames_list()
                        print(f"  → 4 puntos agregados a frame #{frame_idx+1}")
                        
                        # Mostrar diálogo de confirmación
                        QMessageBox.information(
                            self, "Patrón Confirmado",
                            f"✅ 4 centros de calibración guardados en frame #{frame_idx+1}"
                        )
                else:
                    print("⚠️  Debe confirmar un frame primero")
                    QMessageBox.warning(
                        self, "Advertencia",
                        "Debe confirmar un frame en el panel lateral primero"
                    )
        
        except Exception as e:
            print(f"Error confirmando patrón: {e}")
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")
    
    def get_selected_points(self):
        """Retorna los 4 centros del patrón de calibración."""
        return self.calibration_pattern.get_display_circle_centers(self.pattern_scale).tolist()
    
    def clear_selection(self):
        """Limpia la selección actual (reinicia patrón)."""
        self.calibration_pattern.reset()
    
    def update_data(self, data: Dict[str, Any]):
        """Actualiza datos 3D y estado de sensores."""
        # Guardar datos para re-renderizar cuando cambie tópico
        self.last_data = data
        
        # Resetear posición de visualización cuando se carga un frame nuevo
        self.current_elev = None
        self.current_azim = None
        
        # Actualizar lista de tópicos de pointcloud disponibles
        available_pointcloud_topics = []
        if 'pointclouds' in data and data['pointclouds']:
            available_pointcloud_topics = list(data['pointclouds'].keys())
        
        if available_pointcloud_topics != self.available_lidar_topics:
            self.available_lidar_topics = available_pointcloud_topics
            self._update_topic_combo()
        
        # Actualizar timestamp
        if 'timestamp' in data and data['timestamp']:
            self.frame_timestamp.setText(f"Timestamp: {data['timestamp']:.6f}")
        
        # Seleccionar el pointcloud según el tópico actual
        pc = None
        imgs = data.get('images', {}) if isinstance(data, dict) else {}

        # Si el tópico seleccionado es una imagen (disparity) y el usuario pidió usar disparity,
        # intentar convertir primero — esto evita usar el fallback al primer pointcloud (velodyne).
        if self.selected_lidar_topic and self.disparity_checkbox.isChecked() and self.selected_lidar_topic in imgs:
            disp = imgs[self.selected_lidar_topic]
            try:
                fx = float(self.fx_spin.value())
                fy = float(self.fy_spin.value())
                cx = float(self.cx_spin.value())
                cy = float(self.cy_spin.value())
                baseline = float(self.baseline_spin.value())
                pc_conv = self.disparity_to_pointcloud(disp, fx, fy, cx, cy, baseline)
                if pc_conv is not None and len(pc_conv) > 0:
                    pc = pc_conv
                    self.pointcloud_label.setText(f"LiDAR(disparity): ✅ Generado")
                    self.frame_points.setText(f"Puntos: {len(pc_conv)}")
                    self.draw_3d_pointcloud(pc_conv)
                    self.last_pointcloud = pc_conv
            except Exception as e:
                print(f"Error convirtiendo disparity->PC: {e}")

        # Si no se obtuvo pointcloud por disparity, buscar un pointcloud real seleccionado
        if pc is None:
            if self.selected_lidar_topic and 'pointclouds' in data and self.selected_lidar_topic in data['pointclouds']:
                pc = data['pointclouds'][self.selected_lidar_topic]
            elif 'pointcloud' in data and data['pointcloud'] is not None:
                # Fallback a backward compatibility (usar sólo si no hay selección explícita de imagen)
                pc = data['pointcloud']

        # Actualizar LiDAR/PointCloud (si no se dibujó ya con disparity conversion arriba)
        if pc is not None and (self.last_pointcloud is None or not np.array_equal(pc, self.last_pointcloud)):
            try:
                n_points = len(pc)
                self.pointcloud_label.setText(f"LiDAR: ✅ Detectado")
                self.frame_points.setText(f"Puntos: {n_points}")
                # Dibujar en 3D
                self.draw_3d_pointcloud(pc)
                self.last_pointcloud = pc
            except Exception:
                # Si falló dibujar (p.ej. pc es None-like), mostrar no disponible
                self.pointcloud_label.setText("LiDAR: ❌ No disponible")
                self.frame_points.setText("Puntos: --")
        elif pc is None:
            self.pointcloud_label.setText("LiDAR: ❌ No disponible")
            self.frame_points.setText("Puntos: --")

        # Actualizar la visualización de los círculos de calibración
        self.calibration_pattern.update_display()
    
    def _update_topic_combo(self):
        """Actualiza el combo de tópicos."""
        current_topic = self.topic_combo.currentText()
        self.topic_combo.blockSignals(True)
        self.topic_combo.clear()
        self.topic_combo.addItems(self.available_lidar_topics)
        
        # Restaurar selección anterior si existe
        if current_topic in self.available_lidar_topics:
            self.topic_combo.setCurrentText(current_topic)
        elif self.available_lidar_topics:
            self.selected_lidar_topic = self.available_lidar_topics[0]
        
        self.topic_combo.blockSignals(False)
    
    def on_topic_changed(self):
        """Manejador cuando cambia el tópico seleccionado."""
        self.selected_lidar_topic = self.topic_combo.currentText()
        self._user_override = True
        if self.last_data:
            self.current_elev = None
            self.current_azim = None
            self.update_data(self.last_data)

    def on_disparity_toggled(self, enabled: bool):
        """Handler when disparity-as-pointcloud toggle changes."""
        self.disparity_checkbox.setChecked(enabled)
        if self.last_data:
            self.update_data(self.last_data)

    def disparity_to_pointcloud(self, disp_img, fx, fy, cx, cy, baseline):
        """Converts disparity image (numpy) to Nx3 point cloud (meters).

        Expects disparity in pixels (float). Filters non-positive disparities.
        """
        try:
            disp = np.array(disp_img, dtype=np.float32)
            if disp.size == 0:
                return None
            h, w = disp.shape[:2]
            # Avoid division by zero
            mask = disp > 0
            if mask.sum() == 0:
                return None
            depth = (fx * baseline) / (disp + 1e-6)
            u, v = np.meshgrid(np.arange(w), np.arange(h))
            X = (u - cx) * depth / fx
            Y = (v - cy) * depth / fy
            Z = depth
            pts = np.stack([X[mask], Y[mask], Z[mask]], axis=1)
            return pts
        except Exception as e:
            print(f"Error in disparity_to_pointcloud: {e}")
            return None

    def set_all_topics(self, all_topics: list):
        """Repuebla el combo con TODOS los tópicos del bag/ROS.
        Los tópicos LiDAR/pointcloud recomendados aparecen primero; el resto al final."""
        recommended = [t for t in all_topics
                       if 'velodyne' in t.lower() or 'lidar' in t.lower()
                       or 'pointcloud' in t.lower() or 'points' in t.lower()]
        others = [t for t in all_topics if t not in recommended]

        current_topic = self.selected_lidar_topic if self._user_override else self.topic_combo.currentText()

        self.topic_combo.blockSignals(True)
        self.topic_combo.clear()

        if recommended:
            for t in recommended:
                self.topic_combo.addItem(t)
        if others:
            self.topic_combo.insertSeparator(self.topic_combo.count())
            for t in others:
                self.topic_combo.addItem(t)

        if current_topic and self.topic_combo.findText(current_topic) >= 0:
            self.topic_combo.setCurrentText(current_topic)
        elif current_topic and self._user_override:
            self.topic_combo.addItem(current_topic)
            self.topic_combo.setCurrentText(current_topic)
        elif recommended and not self._user_override:
            self.selected_lidar_topic = recommended[0]
            self.topic_combo.setCurrentText(recommended[0])

        self.topic_combo.blockSignals(False)

    def on_zoom_changed(self, value):
        """Actualiza el zoom de la visualización 3D."""
        self.zoom_level = value
        if self.last_pointcloud is not None:
            self.draw_3d_pointcloud(self.last_pointcloud)
    
    def on_size_changed(self, value):
        """Actualiza el tamaño de los puntos de la nube."""
        self.point_size = value
        if self.last_pointcloud is not None:
            self.draw_3d_pointcloud(self.last_pointcloud)
    
    def on_scroll(self, event):
        """Maneja el zoom con la rueda del mouse."""
        if event.inaxes is None or self.last_pointcloud is None:
            return
        
        # Incremento/decremento de zoom: 10% por scroll
        zoom_factor = 1.1
        
        if event.button == 'up':
            # Scroll arriba: acercar (aumentar zoom)
            new_zoom = self.zoom_level * zoom_factor
        elif event.button == 'down':
            # Scroll abajo: alejar (disminuir zoom)
            new_zoom = self.zoom_level / zoom_factor
        else:
            return
        
        # Limitar al rango válido
        new_zoom = np.clip(new_zoom, 0.1, 5.0)
        
        # Actualizar slider y zoom_level
        # Desconectar señal temporalmente para evitar bucles
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(new_zoom)
        self.zoom_slider.blockSignals(False)
        
        # Actualizar y redibujar
        self.zoom_level = new_zoom
        self.draw_3d_pointcloud(self.last_pointcloud)


# ============================================================================
# VENTANA DE DIÁLOGO: MOSTRAR COORDENADAS GUARDADAS
# ============================================================================

class CoordinatesDisplayDialog(QDialog):
    """Ventana para mostrar y guardar coordenadas de un frame."""
    
    def __init__(self, frame_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.frame_info = frame_info
        self.setWindowTitle(f"📍 Coordenadas - Frame {frame_info.get('frame_idx', '?')}")
        self.setGeometry(100, 100, 600, 600)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # ========== INFORMACIÓN DEL FRAME ==========
        info_group = QGroupBox("📊 Información del Frame")
        info_layout = QGridLayout()
        
        frame_idx = self.frame_info.get('frame_idx', 'N/A')
        sensor = self.frame_info.get('sensor', 'N/A')
        topic = self.frame_info.get('topic', 'N/A')
        timestamp = self.frame_info.get('timestamp', 0.0)
        
        info_layout.addWidget(QLabel("Frame:"), 0, 0)
        info_layout.addWidget(QLabel(f"#{frame_idx}"), 0, 1)
        
        info_layout.addWidget(QLabel("Sensor:"), 1, 0)
        info_layout.addWidget(QLabel(f"<b>{sensor.upper()}</b>"), 1, 1)
        
        info_layout.addWidget(QLabel("Tópico:"), 2, 0)
        topic_label = QLabel(topic)
        topic_label.setWordWrap(True)
        info_layout.addWidget(topic_label, 2, 1)
        
        info_layout.addWidget(QLabel("Timestamp:"), 3, 0)
        info_layout.addWidget(QLabel(f"{timestamp:.6f}"), 3, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # ========== COORDENADAS DE LOS 4 CÍRCULOS ==========
        coords_group = QGroupBox("🎯 Coordenadas de los 4 Círculos del Patrón")
        coords_layout = QGridLayout()
        coords_layout.setSpacing(8)
        
        # Encabezados
        header_style = "font-weight: bold; background-color: #f0f0f0; padding: 4px;"
        header_nro = QLabel("Nº")
        header_nro.setStyleSheet(header_style)
        header_x = QLabel("X (m)")
        header_x.setStyleSheet(header_style)
        header_y = QLabel("Y (m)")
        header_y.setStyleSheet(header_style)
        header_z = QLabel("Z (m)")
        header_z.setStyleSheet(header_style)
        
        coords_layout.addWidget(header_nro, 0, 0)
        coords_layout.addWidget(header_x, 0, 1)
        coords_layout.addWidget(header_y, 0, 2)
        coords_layout.addWidget(header_z, 0, 3)
        
        # Datos
        points = self.frame_info.get('points', [])
        
        if points and len(points) > 0:
            for i in range(4):  # Siempre mostrar 4 filas
                nro_label = QLabel(str(i+1))
                nro_label.setAlignment(Qt.AlignCenter)
                coords_layout.addWidget(nro_label, i+1, 0)
                
                if i < len(points):
                    point = points[i]
                    x_val = f"{point.get('x', 0):.6f}"
                    y_val = f"{point.get('y', 0):.6f}"
                    z_val = f"{point.get('z', 0):.6f}"
                else:
                    x_val = y_val = z_val = "--"
                
                x_label = QLabel(x_val)
                x_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                y_label = QLabel(y_val)
                y_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                z_label = QLabel(z_val)
                z_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                coords_layout.addWidget(x_label, i+1, 1)
                coords_layout.addWidget(y_label, i+1, 2)
                coords_layout.addWidget(z_label, i+1, 3)
            
            num_puntos = len(points)
            info_text = f"✅ {num_puntos} punto{'s' if num_puntos != 1 else ''} capturado{'s' if num_puntos != 1 else ''}"
        else:
            # Sin datos
            coords_layout.addWidget(QLabel("⚠️ No hay coordenadas guardadas"), 1, 0, 1, 4)
            info_text = "❌ Sin coordenadas"
        
        coords_group.setLayout(coords_layout)
        layout.addWidget(coords_group)
        
        # ========== METADATA DE LA MÁSCARA ==========
        mask_metadata = self.frame_info.get('mask_metadata', {})
        if mask_metadata:
            meta_group = QGroupBox("📐 Metadata de la Máscara")
            meta_layout = QGridLayout()
            
            # Posición
            pos = mask_metadata.get('position', {})
            meta_layout.addWidget(QLabel("Posición (m):"), 0, 0)
            meta_layout.addWidget(QLabel(f"X: {pos.get('x', 0):.4f}"), 0, 1)
            meta_layout.addWidget(QLabel(f"Y: {pos.get('y', 0):.4f}"), 0, 2)
            meta_layout.addWidget(QLabel(f"Z: {pos.get('z', 0):.4f}"), 0, 3)
            
            # Rotación
            rot = mask_metadata.get('rotation', {})
            meta_layout.addWidget(QLabel("Rotación (°):"), 1, 0)
            meta_layout.addWidget(QLabel(f"X: {rot.get('x', 0):.2f}"), 1, 1)
            meta_layout.addWidget(QLabel(f"Y: {rot.get('y', 0):.2f}"), 1, 2)
            meta_layout.addWidget(QLabel(f"Z: {rot.get('z', 0):.2f}"), 1, 3)
            
            # Escala
            scale = mask_metadata.get('scale', 1.0)
            meta_layout.addWidget(QLabel("Escala:"), 2, 0)
            meta_layout.addWidget(QLabel(f"{scale:.4f}x"), 2, 1)
            
            meta_group.setLayout(meta_layout)
            layout.addWidget(meta_group)
        
        # ========== INFORMACIÓN ADICIONAL ==========
        info_label = QLabel(f"<b>{info_text}</b>")
        info_label.setStyleSheet("color: #0066cc; padding: 8px;")
        layout.addWidget(info_label)
        
        # ========== BOTONES ==========
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        btn_copy = QPushButton("📋 Copiar al Portapapeles")
        btn_copy.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(btn_copy)
        
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def copy_to_clipboard(self):
        """Copia las coordenadas al portapapeles."""
        import subprocess
        
        # Construir texto detallado
        text = "=" * 60 + "\n"
        text += f"📍 COORDENADAS - Frame {self.frame_info.get('frame_idx')}\n"
        text += "=" * 60 + "\n\n"
        
        # Información del frame
        text += "📊 INFORMACIÓN DEL FRAME:\n"
        text += f"  Frame: {self.frame_info.get('frame_idx')}\n"
        text += f"  Sensor: {self.frame_info.get('sensor').upper()}\n"
        text += f"  Tópico: {self.frame_info.get('topic')}\n"
        text += f"  Timestamp: {self.frame_info.get('timestamp'):.6f}\n\n"
        
        # Coordenadas
        points = self.frame_info.get('points', [])
        text += "🎯 COORDENADAS DE LOS 4 CÍRCULOS:\n"
        text += "  Nº   X (m)         Y (m)         Z (m)\n"
        text += "  " + "-" * 50 + "\n"
        
        for i in range(4):
            if i < len(points):
                point = points[i]
                text += f"  {i+1}.   {point.get('x', 0):12.6f}  {point.get('y', 0):12.6f}  {point.get('z', 0):12.6f}\n"
            else:
                text += f"  {i+1}.   {'--':>12}  {'--':>12}  {'--':>12}\n"
        
        # Metadata de la máscara
        mask_metadata = self.frame_info.get('mask_metadata', {})
        if mask_metadata:
            text += "\n📐 METADATA DE LA MÁSCARA:\n"
            
            pos = mask_metadata.get('position', {})
            text += f"  Posición: X={pos.get('x', 0):.4f}, Y={pos.get('y', 0):.4f}, Z={pos.get('z', 0):.4f}\n"
            
            rot = mask_metadata.get('rotation', {})
            text += f"  Rotación: X={rot.get('x', 0):.2f}°, Y={rot.get('y', 0):.2f}°, Z={rot.get('z', 0):.2f}°\n"
            
            scale = mask_metadata.get('scale', 1.0)
            text += f"  Escala: {scale:.4f}x\n"
        
        text += "\n" + "=" * 60 + "\n"
        
        # Copiar al portapapeles
        try:
            process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
            process.communicate(text.encode('utf-8'))
            QMessageBox.information(self, "✅ Copiado", "Coordenadas copiadas al portapapeles")
        except:
            # Fallback: mostrar en diálogo si xclip no está disponible
            QMessageBox.information(self, "Coordenadas", text)
        
        try:
            process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
            process.communicate(text.encode('utf-8'))
            QMessageBox.information(self, "✅ Copiado", "Coordenadas copiadas al portapapeles")
        except:
            QMessageBox.warning(self, "⚠️ Aviso", "No se pudo copiar. Asegúrate de tener xclip instalado.")


# ============================================================================
# PESTAÑA DE DETECCIÓN (VISUALIZACIÓN DE PUNTOS GUARDADOS)
# ============================================================================

class DetectionTab(QWidget):
    """Pestaña para editar detecciones guardadas - Mover y redimensionar puntos."""
    
    def __init__(self):
        super().__init__()
        self.current_detection_points = []
        self.original_detection_points = []  # Guardar puntos originales
        self.frame_info = {}
        self.parent_gui = None
        self.fig = None
        self.canvas = None
        self.current_elev = 30
        self.current_azim = -60
        self.selected_point_idx = None  # Índice del punto seleccionado
        self.last_pointcloud = None
        self.scale_factor = 1.0  # Factor de escala para redimensionar
        self.current_view_mode = "3D"  # "2D" o "3D"
        self.current_sensor = None  # Tipo de sensor actual
        self.calibration_pattern = CalibrationPattern()  # Patrón de 4 círculos
        self.pattern_visible = False  # Si la máscara está visible
        self.is_2d_mode = False  # Si se muestra en 2D o 3D
        self.pattern_scale = 1.0  # Escala de la máscara (tamaño de círculos)
        self.movement_step = 0.01  # Paso de movimiento en metros
        self.lidar_zoom = 1.0  # Factor de zoom para vista 3D LiDAR
        self.lidar_point_size = 2.0  # Tamaño de puntos de la nube de puntos (1-50)
        self.current_points_unit = "m"  # Unidad principal del panel de coordenadas
        self.current_image_shape = None  # (alto, ancho) de la imagen activa si existe
        
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Panel superior: Información del frame + Opciones de vista
        info_layout = QHBoxLayout()
        self.frame_label = QLabel("📋 Frame: -")
        self.sensor_label = QLabel("🔌 Sensor: -")
        self.points_label = QLabel("📍 Puntos: 0")
        self.timestamp_label = QLabel("⏱️ Timestamp: -")
        
        info_layout.addWidget(self.frame_label)
        info_layout.addWidget(self.sensor_label)
        info_layout.addWidget(self.points_label)
        info_layout.addWidget(self.timestamp_label)
        info_layout.addStretch()
        
        # Opciones de vista (solo visible para Stereo)
        info_layout.addWidget(QLabel("Vista:"))
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["3D (Profundidad)", "2D (Imagen)"])
        self.view_mode_combo.currentTextChanged.connect(self.on_view_mode_changed)
        self.view_mode_combo.setVisible(False)  # Inicialmente oculto
        info_layout.addWidget(self.view_mode_combo)
        
        main_layout.addLayout(info_layout)
        
        # Canvas de visualización 3D/2D con interacción
        self.fig = Figure(figsize=(8, 6), dpi=100, facecolor='#2a2a2a')
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet("background-color: #2a2a2a;")
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)
        self.canvas.mpl_connect('scroll_event', self.on_canvas_scroll)
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_motion)
        self.canvas.mpl_connect('button_release_event', self._on_mouse_release)
        main_layout.addWidget(self.canvas, 1)
        
        # Panel de controles: Mover y redimensionar
        controls_layout = QHBoxLayout()
        
        self.selected_label = QLabel("Seleccionado: Ninguno")
        controls_layout.addWidget(self.selected_label)
        controls_layout.addStretch()
        
        # Control de escala/tamaño
        controls_layout.addWidget(QLabel("Escala:"))
        self.scale_slider = QDoubleSpinBox()
        self.scale_slider.setMinimum(0.5)
        self.scale_slider.setMaximum(2.0)
        self.scale_slider.setValue(1.0)
        self.scale_slider.setSingleStep(0.1)
        self.scale_slider.valueChanged.connect(self.on_scale_changed)
        controls_layout.addWidget(self.scale_slider)
        
        # Botones de acción
        btn_reset = QPushButton("🔄 Resetear")
        btn_reset.clicked.connect(self.reset_points)
        controls_layout.addWidget(btn_reset)
        
        btn_save = QPushButton("💾 Guardar Cambios")
        btn_save.clicked.connect(self.save_changes)
        controls_layout.addWidget(btn_save)
        
        main_layout.addLayout(controls_layout)
        
        # Panel de movimiento de máscara (solo visible cuando patrón activo)
        movement_layout = QVBoxLayout()
        
        # Fila 1: Botones de movimiento
        movement_buttons_layout = QHBoxLayout()
        movement_buttons_layout.addWidget(QLabel("🎯 Mover Máscara:"))
        
        btn_up = QPushButton("⬆")
        btn_up.clicked.connect(lambda: self.move_pattern(dy=-self.movement_step))
        movement_buttons_layout.addWidget(btn_up)
        
        btn_down = QPushButton("⬇")
        btn_down.clicked.connect(lambda: self.move_pattern(dy=self.movement_step))
        movement_buttons_layout.addWidget(btn_down)
        
        btn_left = QPushButton("⬅")
        btn_left.clicked.connect(lambda: self.move_pattern(dx=-self.movement_step))
        movement_buttons_layout.addWidget(btn_left)
        
        btn_right = QPushButton("➡")
        btn_right.clicked.connect(lambda: self.move_pattern(dx=self.movement_step))
        movement_buttons_layout.addWidget(btn_right)
        
        movement_buttons_layout.addStretch()
        movement_layout.addLayout(movement_buttons_layout)

        # Fila extra: movimiento en el eje Z para LiDAR / vista 3D
        movement_z_layout = QHBoxLayout()
        movement_z_layout.addWidget(QLabel("🎚 Eje Z:"))

        btn_z_up = QPushButton("⬆ Z+")
        btn_z_up.clicked.connect(lambda: self.move_pattern(dz=self.movement_step))
        movement_z_layout.addWidget(btn_z_up)

        btn_z_down = QPushButton("⬇ Z-")
        btn_z_down.clicked.connect(lambda: self.move_pattern(dz=-self.movement_step))
        movement_z_layout.addWidget(btn_z_down)

        movement_z_layout.addStretch()
        movement_layout.addLayout(movement_z_layout)
        
        # Fila 2: Control de escala de máscara
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("📏 Escala Máscara:"))
        
        self.pattern_scale_spinbox = QDoubleSpinBox()
        self.pattern_scale_spinbox.setMinimum(0.01)
        self.pattern_scale_spinbox.setMaximum(100.0)
        self.pattern_scale_spinbox.setSingleStep(0.1)
        self.pattern_scale_spinbox.setValue(1.0)
        self.pattern_scale_spinbox.setDecimals(2)
        self.pattern_scale_spinbox.valueChanged.connect(self.on_pattern_scale_changed)
        scale_layout.addWidget(self.pattern_scale_spinbox)
        
        scale_layout.addWidget(QLabel("(Rueda ratón para ajustar)"))
        scale_layout.addStretch()
        movement_layout.addLayout(scale_layout)
        
        # Fila 3: Control de paso de movimiento
        step_layout = QHBoxLayout()
        step_layout.addWidget(QLabel("📍 Paso Movimiento:"))
        
        self.movement_step_spinbox = QDoubleSpinBox()
        self.movement_step_spinbox.setMinimum(0.001)
        self.movement_step_spinbox.setMaximum(0.1)
        self.movement_step_spinbox.setSingleStep(0.001)
        self.movement_step_spinbox.setValue(0.01)
        self.movement_step_spinbox.setDecimals(4)
        self.movement_step_spinbox.valueChanged.connect(self.on_movement_step_changed)
        step_layout.addWidget(self.movement_step_spinbox)
        
        step_layout.addWidget(QLabel("m (0.001=1mm, 0.01=1cm, 0.1=10cm)"))
        step_layout.addStretch()
        movement_layout.addLayout(step_layout)
        
        # Fila 4: Control de rotación de máscara - con selector de eje (X, Y, Z)
        rotation_layout = QHBoxLayout()
        rotation_layout.addWidget(QLabel("🔄 Rotar Máscara:"))
        
        btn_rotate_left = QPushButton("↶ -5°")
        btn_rotate_left.clicked.connect(self.on_rotate_button_left)
        rotation_layout.addWidget(btn_rotate_left)
        
        btn_rotate_right = QPushButton("↷ +5°")
        btn_rotate_right.clicked.connect(self.on_rotate_button_right)
        rotation_layout.addWidget(btn_rotate_right)
        
        self.rotation_angle_spinbox = QDoubleSpinBox()
        self.rotation_angle_spinbox.setMinimum(-360.0)
        self.rotation_angle_spinbox.setMaximum(360.0)
        self.rotation_angle_spinbox.setSingleStep(1.0)
        self.rotation_angle_spinbox.setValue(0.0)
        self.rotation_angle_spinbox.setDecimals(1)
        self.rotation_angle_spinbox.setSuffix("°")
        self.rotation_angle_spinbox.valueChanged.connect(self.on_rotation_spinbox_changed)
        rotation_layout.addWidget(self.rotation_angle_spinbox)
        
        # ComboBox para seleccionar el eje (X, Y, Z)
        self.rotation_axis_combo = QComboBox()
        self.rotation_axis_combo.addItems(["X", "Y", "Z"])
        self.rotation_axis_combo.setCurrentIndex(2)  # Por defecto Z
        self.rotation_axis_combo.currentTextChanged.connect(self.on_rotation_axis_changed)
        rotation_layout.addWidget(self.rotation_axis_combo)
        
        rotation_layout.addWidget(QLabel("(Grados)"))
        rotation_layout.addStretch()
        movement_layout.addLayout(rotation_layout)
        
        self.movement_group = QGroupBox("Controles de Máscara")
        self.movement_group.setLayout(movement_layout)
        self.movement_group.setVisible(False)  # Oculto por defecto
        main_layout.addWidget(self.movement_group)
        
        # Panel de zoom para vista 3D de LiDAR
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("🔍 Zoom 3D:"))
        
        btn_zoom_out = QPushButton("🔍−")
        btn_zoom_out.clicked.connect(lambda: self.set_lidar_zoom(self.lidar_zoom / 1.2))
        zoom_layout.addWidget(btn_zoom_out)
        
        btn_zoom_in = QPushButton("🔍+")
        btn_zoom_in.clicked.connect(lambda: self.set_lidar_zoom(self.lidar_zoom * 1.2))
        zoom_layout.addWidget(btn_zoom_in)
        
        self.zoom_spinbox = QDoubleSpinBox()
        self.zoom_spinbox.setMinimum(0.1)
        self.zoom_spinbox.setMaximum(10.0)
        self.zoom_spinbox.setSingleStep(0.1)
        self.zoom_spinbox.setValue(1.0)
        self.zoom_spinbox.setDecimals(1)
        self.zoom_spinbox.setSuffix("x")
        self.zoom_spinbox.valueChanged.connect(self.on_zoom_changed)
        zoom_layout.addWidget(self.zoom_spinbox)
        
        zoom_layout.addWidget(QLabel("(Scroll rueda para zoom)"))
        zoom_layout.addStretch()
        
        # Agregar control de tamaño de puntos de la nube
        points_size_layout = QHBoxLayout()
        points_size_layout.addWidget(QLabel("📍 Tamaño Puntos Nube:"))
        
        self.point_size_spinbox = QDoubleSpinBox()
        self.point_size_spinbox.setMinimum(0.5)
        self.point_size_spinbox.setMaximum(50.0)
        self.point_size_spinbox.setSingleStep(0.5)
        self.point_size_spinbox.setValue(2.0)
        self.point_size_spinbox.setDecimals(1)
        self.point_size_spinbox.valueChanged.connect(self.on_point_size_changed)
        points_size_layout.addWidget(self.point_size_spinbox)
        
        points_size_layout.addWidget(QLabel("(Pequeño: 0.5 → Grande: 50)"))
        points_size_layout.addStretch()
        zoom_layout.addLayout(points_size_layout)
        
        self.zoom_group = QGroupBox("Controles Vista 3D")
        self.zoom_group.setLayout(zoom_layout)
        self.zoom_group.setVisible(False)  # Oculto por defecto, solo visible en LiDAR 3D
        main_layout.addWidget(self.zoom_group)
        
        # Panel inferior: Coordenadas detalladas
        coords_layout = QVBoxLayout()
        self.coords_text = QTextEdit()
        self.coords_text.setReadOnly(True)
        self.coords_text.setMaximumHeight(100)
        self.coords_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ff00;
                font-family: 'Courier New';
                font-size: 10px;
                border: 1px solid #444;
            }
        """)
        coords_layout.addWidget(QLabel("📊 Coordenadas de puntos (Click para seleccionar, Flechas para mover):"))
        coords_layout.addWidget(self.coords_text)
        main_layout.addLayout(coords_layout)
        
        self.setLayout(main_layout)
        self.setFocus()
    
    def set_parent_gui(self, parent_gui):
        """Establece referencia al GUI principal."""
        self.parent_gui = parent_gui
    
    def on_view_mode_changed(self):
        """Maneja cambios entre vista 2D e 3D."""
        view_text = self.view_mode_combo.currentText()
        if "2D" in view_text:
            self.current_view_mode = "2D"
        else:
            self.current_view_mode = "3D"
        
        # Redibujar con la nueva vista
        self._draw_detection_display()
    
    def display_detection(self, detection_data: Dict[str, Any]):
        """Carga una detección para edición - Soporta LiDAR y Stereo."""
        self.current_detection_points = []
        self.original_detection_points = []
        
        # Verificar el sensor
        sensor = detection_data.get('sensor', 'unknown')
        self.current_sensor = sensor
        self.frame_info = {k: v for k, v in detection_data.items() if k != 'points'}
        
        # Actualizar etiquetas
        frame_idx = detection_data.get('frame_idx', '-')
        self.frame_label.setText(f"📋 Frame: {frame_idx}")
        self.sensor_label.setText(f"🔌 Sensor: {sensor.upper()}")
        timestamp = detection_data.get('timestamp', '-')
        if timestamp != '-':
            self.timestamp_label.setText(f"⏱️ Timestamp: {timestamp:.6f}")
        
        # Detectar modo 2D
        self.is_2d_mode = detection_data.get('is_2d', False)
        
        # Mostrar/ocultar controles de zoom 3D (solo para LiDAR 3D)
        is_lidar_3d = (sensor.lower() == 'lidar' and not self.is_2d_mode)
        self.zoom_group.setVisible(is_lidar_3d)
        
        # Configurar opciones de vista según sensor
        if sensor.lower() in ['stereo', 'rgb'] and not self.is_2d_mode:
            # Para Stereo en 3D: mostrar opciones de vista 2D/3D
            self.view_mode_combo.setVisible(True)
            self.view_mode_combo.blockSignals(True)
            self.view_mode_combo.setCurrentIndex(0)  # Por defecto mostrar 3D
            self.view_mode_combo.blockSignals(False)
            self.current_view_mode = "3D"
        else:
            # Para LiDAR o Stereo 2D: solo 3D o solo 2D, ocultar opciones
            self.view_mode_combo.setVisible(False)
            self.current_view_mode = "3D" if not self.is_2d_mode else "2D"
        
        # 📌 IMPORTANTE: Procesar puntos SOLO si NO hay mask_metadata
        # Si hay metadata, los puntos se recalcularán después de restaurar la máscara
        has_mask_metadata = 'mask_metadata' in detection_data and bool(detection_data.get('mask_metadata'))
        
        if not has_mask_metadata:
            # Procesar puntos según sensor (cuando no hay metadata de máscara)
            if sensor.lower() == 'lidar':
                # Para LiDAR: convertir puntos a lista de listas
                points_raw = detection_data.get('points', [])
                for p in points_raw:
                    if isinstance(p, (list, tuple)):
                        self.current_detection_points.append(list(p)[:3])
                        self.original_detection_points.append(list(p)[:3])
                    elif isinstance(p, np.ndarray):
                        self.current_detection_points.append(p[:3].tolist())
                        self.original_detection_points.append(p[:3].tolist())
                    elif isinstance(p, dict):
                        point_list = [p.get('x', 0), p.get('y', 0), p.get('z', 0)]
                        self.current_detection_points.append(point_list)
                        self.original_detection_points.append(point_list)
            elif sensor.lower() in ['stereo', 'rgb', 'thermal']:
                # Para Stereo/Thermal: puntos pueden ser 2D (imagen) o 3D (profundidad)
                points_raw = detection_data.get('points', [])
                for p in points_raw:
                    if isinstance(p, (list, tuple)):
                        self.current_detection_points.append(list(p))
                        self.original_detection_points.append(list(p))
                    elif isinstance(p, np.ndarray):
                        self.current_detection_points.append(p.tolist())
                        self.original_detection_points.append(p.tolist())
                    elif isinstance(p, dict):
                        point_list = [p.get('x', 0), p.get('y', 0), p.get('z', 0) if 'z' in p else 0]
                        self.current_detection_points.append(point_list)
                        self.original_detection_points.append(point_list)
        
        self.scale_factor = 1.0
        self.selected_point_idx = None
        
        # Bloquear señales del slider para no activar el cambio
        self.scale_slider.blockSignals(True)
        self.scale_slider.setValue(1.0)
        self.scale_slider.blockSignals(False)
        
        self.points_label.setText(f"📍 Puntos: {len(self.current_detection_points)}")

        if sensor.lower() in ['stereo', 'rgb', 'thermal'] and self.current_view_mode == "2D":
            self.current_points_unit = "m"
        elif sensor.lower() == 'lidar':
            self.current_points_unit = "m"
        else:
            self.current_points_unit = "m"
        
        # Mostrar máscara de calibración automáticamente
        self.calibration_pattern.reset()  # Resetear a origen
        
        # 🆕 Restaurar posición y rotación guardadas si existen
        mask_metadata = detection_data.get('mask_metadata', {})
        if mask_metadata:
            # Restaurar posición
            pos = mask_metadata.get('position', {})
            self.calibration_pattern.center_x = float(pos.get('x', 0))
            self.calibration_pattern.center_y = float(pos.get('y', 0))
            self.calibration_pattern.center_z = float(pos.get('z', 0))
            
            # Restaurar rotación
            rot = mask_metadata.get('rotation', {})
            self.calibration_pattern.rotation_x = float(rot.get('x', 0))
            self.calibration_pattern.rotation_y = float(rot.get('y', 0))
            self.calibration_pattern.rotation_z = float(rot.get('z', 0))
            
            # Restaurar escala
            scale = mask_metadata.get('scale', 1.0)
            self.pattern_scale = scale
            print(f"[DISPLAY] ✅ Restaurada posición: ({self.calibration_pattern.center_x:.4f}, {self.calibration_pattern.center_y:.4f}, {self.calibration_pattern.center_z:.4f})")
            print(f"[DISPLAY] ✅ Restaurada rotación: X={self.calibration_pattern.rotation_x:.2f}°, Y={self.calibration_pattern.rotation_y:.2f}°, Z={self.calibration_pattern.rotation_z:.2f}°")
            print(f"[DISPLAY] ✅ Restaurada escala: {scale:.4f}")
            if self.calibration_pattern.detect_double_rotation():
                print("[DISPLAY] ⚠️  Posible doble rotación detectada: rotación lógica cercana al offset visual de 90° en X")
        else:
            # Sin metadata: resetear completamente
            self.calibration_pattern.rotation_x = 0.0
            self.calibration_pattern.rotation_y = 0.0
            self.calibration_pattern.rotation_z = 0.0
            self.pattern_scale = 1.0
            print(f"[DISPLAY] ⚠️  Sin metadata de máscara - reseteando a valores por defecto")
        
        # Actualizar spinbox de rotación
        self.rotation_angle_spinbox.blockSignals(True)
        self.rotation_angle_spinbox.setValue(self.calibration_pattern.rotation_z)
        self.rotation_angle_spinbox.blockSignals(False)
        
        # Actualizar spinbox del selector de eje
        if hasattr(self, 'rotation_axis_combo'):
            self.rotation_axis_combo.blockSignals(True)
            self.rotation_axis_combo.setCurrentIndex(0)  # X por defecto para la orientación vertical inicial
            self.rotation_axis_combo.blockSignals(False)
        
        self.pattern_visible = True
        self.movement_group.setVisible(True)  # Mostrar controles de movimiento
        
        # 🔄 CRÍTICO: Recalcular los centros de círculos con la posición/rotación/escala restauradas
        # Esto asegura que las coordenadas mostradas reflejen la VERDADERA posición de la máscara
        if mask_metadata and sensor.lower() in ['lidar', 'stereo', 'rgb', 'thermal']:
            print(f"[DISPLAY] 🔄 RECALCULANDO centros de círculos con posición/rotación/escala restauradas...")
            print(f"[DISPLAY]    Centro: ({self.calibration_pattern.center_x:.4f}, {self.calibration_pattern.center_y:.4f}, {self.calibration_pattern.center_z:.4f})")
            print(f"[DISPLAY]    Rotación: X={self.calibration_pattern.rotation_x:.2f}°, Y={self.calibration_pattern.rotation_y:.2f}°, Z={self.calibration_pattern.rotation_z:.2f}°")
            print(f"[DISPLAY]    Escala: {self.pattern_scale:.4f}")

            logical_centers = self.calibration_pattern.get_logical_circle_centers(self.pattern_scale)
            display_centers = self.calibration_pattern.get_display_circle_centers(self.pattern_scale)
            print(f"[DISPLAY]    Centros lógicos (sin offset visual):")
            for i, center in enumerate(logical_centers, start=1):
                print(f"[DISPLAY]      L{i}: X={center[0]:9.6f}, Y={center[1]:9.6f}, Z={center[2]:9.6f}")
            print(f"[DISPLAY]    Centros visuales (con offset visual):")
            for i, center in enumerate(display_centers, start=1):
                print(f"[DISPLAY]      V{i}: X={center[0]:9.6f}, Y={center[1]:9.6f}, Z={center[2]:9.6f}")

            if self.calibration_pattern.detect_double_rotation():
                print("[DISPLAY] ⚠️  Posible doble rotación detectada en el renderizado de la máscara")
            
            # Obtener los centros recalculados lógicos (los que se guardan/editarán)
            centers_world = logical_centers
            
            if centers_world is not None and len(centers_world) > 0:
                print(f"[DISPLAY] ✅ Centros recalculados:")
                self.current_detection_points = []
                self.original_detection_points = []
                
                for i, center in enumerate(centers_world):
                    x_m = float(center[0])
                    y_m = float(center[1])
                    z_m = float(center[2])
                    self.current_detection_points.append([x_m, y_m, z_m])
                    self.original_detection_points.append([x_m, y_m, z_m])
                    print(f"[DISPLAY]   Punto Lógico #{i+1}: X={x_m:9.6f}, Y={y_m:9.6f}, Z={z_m:9.6f}")
                
                # Actualizar scale_factor
                self.scale_factor = 1.0
                self.scale_slider.blockSignals(True)
                self.scale_slider.setValue(1.0)
                self.scale_slider.blockSignals(False)
                print(f"[DISPLAY] ✅ Coordenadas actualizadas con la posición restaurada")
            else:
                print(f"[DISPLAY] ⚠️ No se pudieron recalcular centros - usando puntos guardados")
        
        # Mostrar información o visualización según sensor/vista
        if sensor.lower() not in ['lidar', 'stereo', 'rgb', 'thermal']:
            # Sensor no soportado
            self.coords_text.setText(
                f"⚠️  Sensor {sensor.upper()} no soportado\n\n"
                f"Sensores soportados:\n"
                f"  • LiDAR → Vista 3D\n"
                f"  • Stereo → Vista 2D/3D\n"
                f"  • Thermal → Vista 2D"
            )
        else:
            self._update_coordinates_text()
            self._draw_detection_display()
    
    def on_canvas_click(self, event):
        """Selecciona un punto al hacer click."""
        if event.inaxes is None or len(self.current_detection_points) == 0:
            return
        
        try:
            x_click, y_click = event.xdata, event.ydata
            if x_click is None or y_click is None:
                return
            
            # Encontrar el punto más cercano al click
            min_dist = float('inf')
            closest_idx = -1
            
            for i, point in enumerate(self.current_detection_points):
                dist = np.sqrt((point[0] - x_click)**2 + (point[1] - y_click)**2)
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i
            
            # Seleccionar si está cerca (dentro de 0.1 unidades)
            if min_dist < 0.1:
                self.selected_point_idx = closest_idx
                self.selected_label.setText(f"Seleccionado: Punto #{closest_idx+1}")
                print(f"✅ Punto #{closest_idx+1} seleccionado")
                self._draw_detection_3d()
            else:
                self.selected_point_idx = None
                self.selected_label.setText("Seleccionado: Ninguno")
                self._draw_detection_3d()
        
        except Exception as e:
            print(f"Error al seleccionar punto: {e}")
    
    def keyPressEvent(self, event):
        """Maneja teclas para escalar máscara o mover puntos."""
        step = 0.01  # Unidades a mover (para puntos)
        key = event.key()
        
        # Si la máscara está visible y no hay punto seleccionado, ESCALAR máscara con flechas
        if self.pattern_visible and self.selected_point_idx is None:
            scale_step = 0.1  # Incremento de escala por tecla (10%)
            if key == Qt.Key_Up:
                new_scale = self.pattern_scale * (1 + scale_step)  # Aumentar 10%
                self.pattern_scale_spinbox.blockSignals(True)
                self.pattern_scale_spinbox.setValue(new_scale)
                self.pattern_scale_spinbox.blockSignals(False)
                self.on_pattern_scale_changed(new_scale)
            elif key == Qt.Key_Down:
                new_scale = max(0.01, self.pattern_scale / (1 + scale_step))  # Disminuir 10%
                self.pattern_scale_spinbox.blockSignals(True)
                self.pattern_scale_spinbox.setValue(new_scale)
                self.pattern_scale_spinbox.blockSignals(False)
                self.on_pattern_scale_changed(new_scale)
            elif key == Qt.Key_Left or key == Qt.Key_Right:
                super().keyPressEvent(event)
            else:
                super().keyPressEvent(event)
            return
        
        # Si hay punto seleccionado, mover punto
        if self.selected_point_idx is None or len(self.current_detection_points) == 0:
            return
        
        if key == Qt.Key_Left:
            self.current_detection_points[self.selected_point_idx][0] -= step
        elif key == Qt.Key_Right:
            self.current_detection_points[self.selected_point_idx][0] += step
        elif key == Qt.Key_Up:
            self.current_detection_points[self.selected_point_idx][1] += step
        elif key == Qt.Key_Down:
            self.current_detection_points[self.selected_point_idx][1] -= step
        elif key == Qt.Key_Plus or event.text() == '+':
            self.current_detection_points[self.selected_point_idx][2] += step
        elif key == Qt.Key_Minus or event.text() == '-':
            self.current_detection_points[self.selected_point_idx][2] -= step
        else:
            super().keyPressEvent(event)
            return
        
        self._update_coordinates_text()
        self._draw_detection_display()
    
    def on_scale_changed(self, value):
        """Redimensiona todos los puntos."""
        self.scale_factor = value
        self._apply_scale()
        self._update_coordinates_text()
        self._draw_detection_display()
    
    def _update_current_points_from_pattern(self):
        """Recalcula current_detection_points desde la posición/rotación/escala actual del patrón."""
        if not self.calibration_pattern or not self.pattern_visible:
            return
        centers = self.calibration_pattern.get_display_circle_centers(self.pattern_scale)
        if centers is not None and len(centers) > 0:
            self.current_detection_points = [
                [float(c[0]), float(c[1]), float(c[2])] for c in centers
            ]

    def move_pattern(self, dx=0, dy=0, dz=0):
        """Mueve la máscara de calibración."""
        if self.pattern_visible:
            self.calibration_pattern.move(dx, dy, dz)
            self._update_current_points_from_pattern()
            self._draw_detection_display()
            self._update_coordinates_text()
    
    def on_pattern_scale_changed(self, value):
        """Maneja cambios en la escala de la máscara."""
        self.pattern_scale = value
        if self.pattern_visible:
            self._update_current_points_from_pattern()
            self._draw_detection_display()
            self._update_coordinates_text()
    
    def on_movement_step_changed(self, value):
        """Maneja cambios en el paso de movimiento."""
        self.movement_step = value
    
    def on_rotate_button_left(self):
        """Rota -5° en el eje seleccionado."""
        axis = self.rotation_axis_combo.currentText()
        if axis == "X":
            self.rotate_pattern(dx=-5)
        elif axis == "Y":
            self.rotate_pattern(dy=-5)
        else:  # Z
            self.rotate_pattern(dz=-5)
    
    def on_rotate_button_right(self):
        """Rota +5° en el eje seleccionado."""
        axis = self.rotation_axis_combo.currentText()
        if axis == "X":
            self.rotate_pattern(dx=5)
        elif axis == "Y":
            self.rotate_pattern(dy=5)
        else:  # Z
            self.rotate_pattern(dz=5)
    
    def on_rotation_spinbox_changed(self, value):
        """Maneja cambios en el ángulo de rotación (desde spinbox)."""
        if not self.pattern_visible or not self.calibration_pattern:
            return
        
        axis = self.rotation_axis_combo.currentText()
        if axis == "X":
            self.calibration_pattern.rotation_x = value
        elif axis == "Y":
            self.calibration_pattern.rotation_y = value
        else:  # Z
            self.calibration_pattern.rotation_z = value
        
        self._draw_detection_display()
    
    def on_rotation_axis_changed(self, axis_name):
        """Maneja cambios en el eje seleccionado - actualiza el spinbox."""
        if not self.pattern_visible or not self.calibration_pattern:
            return
        
        # Actualizar spinbox para mostrar el valor del eje seleccionado
        self.rotation_angle_spinbox.blockSignals(True)
        if axis_name == "X":
            self.rotation_angle_spinbox.setValue(self.calibration_pattern.rotation_x)
        elif axis_name == "Y":
            self.rotation_angle_spinbox.setValue(self.calibration_pattern.rotation_y)
        else:  # Z
            self.rotation_angle_spinbox.setValue(self.calibration_pattern.rotation_z)
        self.rotation_angle_spinbox.blockSignals(False)
    
    def rotate_pattern(self, dx=0, dy=0, dz=0):
        """Rota la máscara de calibración alrededor de los ejes X, Y, Z."""
        if self.pattern_visible and self.calibration_pattern:
            # Aplicar rotaciones incrementales
            if dx != 0:
                self.calibration_pattern.rotation_x += dx
            if dy != 0:
                self.calibration_pattern.rotation_y += dy
            if dz != 0:
                self.calibration_pattern.rotation_z += dz
            
            # Actualizar spinbox sin disparar cambios
            self.rotation_angle_spinbox.blockSignals(True)
            axis = self.rotation_axis_combo.currentText()
            if axis == "X":
                self.rotation_angle_spinbox.setValue(self.calibration_pattern.rotation_x)
            elif axis == "Y":
                self.rotation_angle_spinbox.setValue(self.calibration_pattern.rotation_y)
            else:  # Z
                self.rotation_angle_spinbox.setValue(self.calibration_pattern.rotation_z)
            self.rotation_angle_spinbox.blockSignals(False)
            
            # Renderizar y actualizar coordenadas
            self._update_current_points_from_pattern()
            self._draw_detection_display()
            self._update_coordinates_text()
    
    def set_lidar_zoom(self, zoom_value):
        """Establece el zoom de la vista 3D de LiDAR."""
        # Limitar a rango válido
        self.lidar_zoom = np.clip(zoom_value, 0.1, 10.0)
        # Actualizar spinbox sin disparar eventos
        self.zoom_spinbox.blockSignals(True)
        self.zoom_spinbox.setValue(self.lidar_zoom)
        self.zoom_spinbox.blockSignals(False)
        # Renderizar con nuevo zoom
        self._draw_detection_display()
    
    def on_zoom_changed(self, value):
        """Maneja cambios en el zoom desde el spinbox."""
        self.lidar_zoom = value
        self._draw_detection_display()
    
    def on_point_size_changed(self, value):
        """Maneja cambios en el tamaño de los puntos de la nube de puntos."""
        self.lidar_point_size = value
        self._draw_detection_display()
    
    def _on_mouse_motion(self, event):
        """Captura la posición de la cámara mientras el usuario arrastra para rotar."""
        if event.inaxes is None:
            return
        try:
            ax = self.fig.axes[0] if self.fig.axes else None
            if ax is not None and hasattr(ax, 'elev'):
                self.current_elev = ax.elev
                self.current_azim = ax.azim
        except Exception:
            pass

    def _on_mouse_release(self, event):
        """Captura la posición final de la cámara al soltar el mouse."""
        try:
            ax = self.fig.axes[0] if self.fig.axes else None
            if ax is not None and hasattr(ax, 'elev'):
                self.current_elev = ax.elev
                self.current_azim = ax.azim
        except Exception:
            pass

    def on_canvas_scroll(self, event):
        """Captura eventos de scroll del ratón en el canvas para ajustar escala o zoom."""
        if not self.pattern_visible or self.selected_point_idx is not None:
            # Solo ajustar si no hay punto seleccionado
            return
        
        if event.inaxes is None:
            return
        
        zoom_factor = 1.15
        
        # En vista 3D (LiDAR o ZED/estéreo), la rueda debe hacer zoom de la nube,
        # no redimensionar la máscara. La escala de la máscara solo debe cambiar en 2D.
        if not self.is_2d_mode and self.current_sensor and self.current_sensor.lower() in {'lidar', 'stereo', 'rgb', 'thermal'}:
            if event.button == 'up':
                new_zoom = self.lidar_zoom * zoom_factor
            elif event.button == 'down':
                new_zoom = self.lidar_zoom / zoom_factor
            else:
                return
            self.set_lidar_zoom(new_zoom)
            return

        # En vista 2D, usar scroll para escala de máscara
        if event.button == 'up':
            # Rueda arriba: aumentar escala
            new_scale = self.pattern_scale * zoom_factor
        elif event.button == 'down':
            # Rueda abajo: disminuir escala
            new_scale = self.pattern_scale / zoom_factor
        else:
            return

        # Sin límites (permite escalar desde 0.01 hasta 100.0)
        new_scale = np.clip(new_scale, 0.01, 100.0)

        # Actualizar spinbox y pattern_scale
        self.pattern_scale_spinbox.blockSignals(True)
        self.pattern_scale_spinbox.setValue(new_scale)
        self.pattern_scale_spinbox.blockSignals(False)

        self.pattern_scale = new_scale
        self._draw_detection_display()
    
    def _apply_scale(self):
        """Aplica factor de escala a los puntos respecto al centroide original."""
        if len(self.original_detection_points) < 2:
            return
        
        # Calcular centroide desde puntos originales
        centroid = np.mean(self.original_detection_points, axis=0)
        
        # Reescalar respecto al centroide ORIGINAL
        for i, original_point in enumerate(self.original_detection_points):
            scaled = centroid + (np.array(original_point) - centroid) * self.scale_factor
            self.current_detection_points[i] = scaled.tolist()
    
    def reset_points(self):
        """Resetea los puntos a su estado original."""
        self.current_detection_points = [p[:] for p in self.original_detection_points]
        self.scale_factor = 1.0
        self.scale_slider.blockSignals(True)
        self.scale_slider.setValue(1.0)
        self.scale_slider.blockSignals(False)
        self.selected_point_idx = None
        self._update_coordinates_text()
        self._draw_detection_display()
    
    def save_changes(self):
        """Guarda los cambios en el frame confirmado."""
        if self.parent_gui and hasattr(self.parent_gui, 'current_confirmed_frame_idx'):
            current_idx = self.parent_gui.current_confirmed_frame_idx
            if current_idx is not None and 0 <= current_idx < len(self.parent_gui.confirmed_frames):
                self.parent_gui.confirmed_frames[current_idx]['points'] = self.current_detection_points

                # Actualizar lista bloqueando señales para no disparar on_confirmed_frame_selected
                self.parent_gui.confirmed_frames_list.blockSignals(True)
                self.parent_gui._update_confirmed_frames_list()
                self.parent_gui.confirmed_frames_list.setCurrentRow(current_idx)
                self.parent_gui.confirmed_frames_list.blockSignals(False)

                # Refrescar panel de coordenadas y visualización
                self._update_coordinates_text()
                self._draw_detection_display()

                QMessageBox.information(
                    self, "Cambios Guardados",
                    f"✅ {len(self.current_detection_points)} puntos actualizados"
                )
                print(f"💾 Cambios guardados en frame #{current_idx+1}")
    
    def _update_coordinates_text(self):
        """Actualiza el panel de texto con coordenadas."""
        if not self.current_detection_points:
            self.coords_text.setText("Sin puntos de detección")
            return

        text = f"Sistema principal: {self.current_points_unit}"
        if self.current_view_mode == "2D" and self.current_image_shape is not None:
            text += f" | Imagen: {self.current_image_shape[1]}x{self.current_image_shape[0]} px"
        text += "\n"
        text += "=" * max(20, len(text.strip())) + "\n"

        for i, point in enumerate(self.current_detection_points):
            marker = "👉 " if i == self.selected_point_idx else "   "
            x, y, z = point[0], point[1], point[2]

            if self.current_view_mode == "2D" and self.current_image_shape is not None and self.current_points_unit == "m":
                px_coords = self._meters_to_pixels(x, y)
                if px_coords is not None:
                    px_x, px_y = px_coords
                    text += (
                        f"{marker}Punto #{i+1}: X={x:8.4f} m  Y={y:8.4f} m  Z={z:8.4f} m"
                        f"  |  Xpx={px_x:8.1f}  Ypx={px_y:8.1f}\n"
                    )
                else:
                    text += f"{marker}Punto #{i+1}: X={x:8.4f} m  Y={y:8.4f} m  Z={z:8.4f} m\n"
            else:
                text += f"{marker}Punto #{i+1}: X={x:8.4f} {self.current_points_unit}  Y={y:8.4f} {self.current_points_unit}  Z={z:8.4f} {self.current_points_unit}\n"
        
        self.coords_text.setText(text)

    def _meters_to_pixels(self, x_m: float, y_m: float):
        """Convierte coordenadas métricas de la máscara a píxeles usando la misma
        referencia visual del panel 2D."""
        if self.current_image_shape is None:
            return None

        try:
            img_h, img_w = self.current_image_shape[:2]
            min_dim = min(img_w, img_h)
            scale_px_per_m = min_dim / 0.24
            offset_x = (img_w - min_dim) / 2
            offset_y = (img_h - min_dim) / 2

            px_x = offset_x + (x_m + 0.12 * self.pattern_scale) * scale_px_per_m
            px_y = offset_y + (y_m + 0.12 * self.pattern_scale) * scale_px_per_m
            return px_x, px_y
        except Exception:
            return None
    
    def _draw_detection_display(self):
        """Dibuja los datos del sensor + máscara de calibración + puntos de detección."""
        try:
            self.fig.clear()
            
            sensor = self.current_sensor or self.frame_info.get('sensor', 'unknown')
            sensor_data = self.frame_info.get('sensor_data', None)
            is_2d = self.frame_info.get('is_2d', False) or (sensor.lower() == 'thermal')
            
            # Determinar qué vista mostrar
            if sensor.lower() in ['stereo', 'rgb', 'thermal'] and (self.current_view_mode == "2D" or is_2d):
                # Vista 2D: Mostrar imagen con máscara superpuesta
                ax = self.fig.add_subplot(111)
                ax.set_facecolor('#000000')
                ax.set_title(f'Detección en Imagen 2D - {sensor.upper()}', color='white', fontsize=11)
                self.current_image_shape = None
                
                # Mostrar imagen del sensor si está disponible
                # Preferir imagen de visualización guardada (p.ej. para disparity)
                img_display = None
                if isinstance(self.frame_info, dict) and self.frame_info.get('sensor_display') is not None:
                    img_display = self.frame_info.get('sensor_display')

                if img_display is None and sensor_data is not None and isinstance(sensor_data, np.ndarray):
                    try:
                        # Si es imagen uint8 o RGB, mostrar directamente
                        if sensor_data.dtype == np.uint8:
                            img_display = sensor_data
                        else:
                            # Si es disparity (float), en lugar de mostrar la matriz cruda,
                            # visualizamos un scatter X vs Z (altura=Z, ancho=X) para que el
                            # usuario vea profundidad como altura.
                            if sensor_data.dtype.kind == 'f' and sensor_data.ndim == 2:
                                disp = sensor_data.astype(np.float32)
                                # Obtener intrínsecos desde tab_3d si están disponibles
                                fx = 700.0; fy = 700.0; cx = sensor_data.shape[1]/2; cy = sensor_data.shape[0]/2; baseline = 0.12
                                try:
                                    if hasattr(self, 'parent_gui') and getattr(self.parent_gui, 'tab_3d', None):
                                        tab3 = self.parent_gui.tab_3d
                                        fx = float(tab3.fx_spin.value())
                                        fy = float(tab3.fy_spin.value())
                                        cx = float(tab3.cx_spin.value())
                                        cy = float(tab3.cy_spin.value())
                                        baseline = float(tab3.baseline_spin.value())
                                except Exception:
                                    pass

                                # Convertir disparity->depth, luego a X,Z para plot
                                with np.errstate(divide='ignore', invalid='ignore'):
                                    depth = (fx * baseline) / (disp + 1e-6)
                                mask = np.isfinite(depth) & (depth > 0)
                                if mask.any():
                                    h, w = disp.shape[:2]
                                    u, v = np.meshgrid(np.arange(w), np.arange(h))
                                    Z = depth
                                    X = (u - cx) * Z / fx
                                    # Mostrar scatter X vs Z
                                    xs = X[mask].ravel()
                                    zs = Z[mask].ravel()
                                    ax.scatter(xs, zs, c=zs, cmap='viridis', s=1)
                                    ax.set_xlabel('X (m)', color='white')
                                    ax.set_ylabel('Z (m)', color='white')
                                    self.fig.patch.set_facecolor('#000000')
                                    self.canvas.draw_idle()
                                    return
                                else:
                                    img_display = None
                            else:
                                # Otros tipos numéricos: normalizar a 0-255
                                arr = sensor_data
                                arr_min = np.nanmin(arr)
                                arr_max = np.nanmax(arr)
                                if arr_max - arr_min > 0:
                                    img_display = np.clip((arr - arr_min) / (arr_max - arr_min) * 255, 0, 255).astype(np.uint8)
                                else:
                                    img_display = np.zeros((arr.shape[0], arr.shape[1]), dtype=np.uint8)
                        
                        # Mostrar imagen si hemos generado una visualización
                        if img_display is not None:
                            if img_display.ndim == 3 and img_display.shape[2] in [3, 4]:
                                ax.imshow(img_display, cmap=None)
                            elif img_display.ndim == 2:
                                ax.imshow(img_display, cmap='gray')
                            else:
                                ax.text(0.5, 0.5, "Formato de imagen\nno soportado", 
                                       color='white', fontsize=12, ha='center', va='center',
                                       transform=ax.transAxes)
                    except Exception as e:
                        ax.text(0.5, 0.5, f"Error: {str(e)[:60]}", 
                               color='white', fontsize=10, ha='center', va='center',
                               transform=ax.transAxes)
                else:
                    ax.text(0.5, 0.5, "Sin imagen del sensor", 
                           color='white', fontsize=12, ha='center', va='center',
                           transform=ax.transAxes)

                if sensor_data is not None and isinstance(sensor_data, np.ndarray):
                    self.current_image_shape = sensor_data.shape[:2]
                
                # Superponer máscara de calibración (si está visible)
                if self.pattern_visible:
                    centers = self.calibration_pattern.get_display_circle_centers(self.pattern_scale)
                    # Obtener dimensiones de la imagen para escalar correctamente
                    if sensor_data is not None and isinstance(sensor_data, np.ndarray):
                        img_h, img_w = sensor_data.shape[:2]
                    else:
                        img_h, img_w = 480, 640  # Valores por defecto

                    # Mantener proporción cuadrada: usar dimensión mínima como referencia
                    min_dim = min(img_w, img_h)
                    # scale_px_per_m: mapea 0.24m del patrón base a min_dim píxeles
                    # No dividir por escala para permitir verdadero zoom (puede salirse del canvas)
                    scale_px_per_m = min_dim / 0.24

                    # Calcular offset para centrar el patrón cuadrado en la imagen
                    offset_x = (img_w - min_dim) / 2
                    offset_y = (img_h - min_dim) / 2

                    # Escalar centros de calibración a píxeles de imagen
                    for i, center in enumerate(centers):
                        cx, cy = center[0], center[1]
                        # Los centros están en rango [-0.12*s, 0.12*s] (ya escalados por get_circle_centers)
                        # Mapear a píxeles: cx en [-0.12*s, 0.12*s] mapea a píxeles
                        px = int(offset_x + (cx + 0.12 * self.pattern_scale) * scale_px_per_m)
                        py = int(offset_y + (cy + 0.12 * self.pattern_scale) * scale_px_per_m)

                        # Radio del círculo en píxeles (aplicar escala para que se escale con el patrón)
                        radius_px = int(0.075 * self.pattern_scale * scale_px_per_m)

                        # Dibujar círculo
                        circle = Circle((px, py), radius_px, fill=False, color='green', linewidth=2, alpha=0.8)
                        ax.add_patch(circle)
                        ax.scatter([px], [py], c='lime', s=150, marker='*', edgecolors='white', linewidths=2)
                
                ax.set_xlabel('X (px)', color='white')
                ax.set_ylabel('Y (px)', color='white')
                ax.set_title(f'Detección en Imagen 2D - {sensor.upper()} | Ejes en píxeles', color='white', fontsize=11)
                ax.tick_params(colors='white', labelsize=8)
                
            else:
                # Vista 3D: Mostrar nube de puntos + máscara de calibración
                ax = self.fig.add_subplot(111, projection='3d')
                self.current_image_shape = None
                
                if sensor.lower() not in ['lidar', 'stereo', 'rgb', 'thermal']:
                    ax.text(0, 0, 0, 
                           f"Sensor {sensor.upper()}\nno soportado", 
                           color='black', fontsize=12, ha='center', va='center')
                    self.fig.patch.set_facecolor('#2a2a2a')
                    self.canvas.draw_idle()
                    return
                
                # Mostrar nube de puntos del sensor como fondo
                if sensor_data is not None and isinstance(sensor_data, np.ndarray):
                    try:
                        if len(sensor_data.shape) == 2 and sensor_data.shape[1] >= 3:
                            pts = sensor_data[:, :3]
                            has_rgb = sensor_data.shape[1] >= 6
                            rgb_cols = sensor_data[:, 3:6] if has_rgb else None
                            
                            if len(pts) > 5000:
                                idx = np.random.choice(len(pts), 5000, replace=False)
                                pts = pts[idx]
                                if has_rgb:
                                    rgb_cols = rgb_cols[idx]
                            
                            # ── Misma corrección de frame óptico que en SensorTab3D ──
                            # Antes esta pestaña dibujaba pts crudos sin remap, por eso
                            # LiDAR y ZED se veían distinto entre pestañas.
                            if is_optical_camera_source(sensor):
                                pts = apply_optical_frame_swap(pts)
                            
                            # Usar color RGB real si está disponible (igual que SensorTab3D);
                            # si no, fallback a color por altura.
                            if has_rgb:
                                point_colors = np.clip(rgb_cols, 0, 1)
                                point_alpha = 0.6
                            else:
                                z_vals = pts[:, 2]
                                z_norm = (z_vals - z_vals.min()) / (z_vals.max() - z_vals.min() + 1e-6)
                                point_colors = plt.cm.viridis(z_norm)
                                point_alpha = 0.3
                            
                            ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], 
                                     c=point_colors, s=self.lidar_point_size, alpha=point_alpha)
                    except Exception as e:
                        print(f"Error mostrando nube: {e}")
                
                # Superponer máscara de calibración (si está visible)
                if self.pattern_visible:
                    centers = self.calibration_pattern.get_display_circle_centers(self.pattern_scale)
                    # Tamaño del marcador escalado por pattern_scale
                    marker_size = int(150 * self.pattern_scale)
                    
                    # Dibujar círculos de calibración (radio 7.5 cm = 0.075 m)
                    for i, center in enumerate(centers):
                        # Círculo 3D en matplotlib: usar scatter con 'o' para círculos llenos
                        ax.scatter([center[0]], [center[1]], [center[2]], 
                                 c='lime', s=marker_size, marker='o', alpha=0.9,
                                 edgecolors='yellow', linewidths=2, label=f'Círculo {i+1}')
                    
                    # Conectar centros formando cuadrado
                    if len(centers) == 4:
                        connections = [(0, 1), (1, 3), (3, 2), (2, 0)]
                        for i, j in connections:
                            ax.plot(
                                [centers[i][0], centers[j][0]],
                                [centers[i][1], centers[j][1]],
                                [centers[i][2], centers[j][2]],
                                'g-', linewidth=2, alpha=0.8
                            )
                
                # Configurar límites con zoom
                if self.pattern_visible:
                    margin = 0.3 / self.lidar_zoom  # Aplicar zoom: menor margen = más zoom
                    centers_arr = np.array(self.calibration_pattern.get_display_circle_centers())
                    ax.set_xlim([centers_arr[:, 0].min() - margin, centers_arr[:, 0].max() + margin])
                    ax.set_ylim([centers_arr[:, 1].min() - margin, centers_arr[:, 1].max() + margin])
                    ax.set_zlim([centers_arr[:, 2].min() - margin, centers_arr[:, 2].max() + margin])
                
                # Configurar ejes
                ax.set_xlabel('X (m)', color='black')
                ax.set_ylabel('Y (m)', color='black')
                ax.set_zlabel('Z (m)', color='black')
                ax.set_title(f'Detección 3D - {sensor.upper()} | Máscara: Flechas/Botones', color='black', fontsize=10)
                
                # Estilo oscuro
                ax.xaxis.pane.fill = False
                ax.yaxis.pane.fill = False
                ax.zaxis.pane.fill = False
                ax.xaxis.pane.set_edgecolor('gray')
                ax.yaxis.pane.set_edgecolor('gray')
                ax.zaxis.pane.set_edgecolor('gray')
                ax.tick_params(colors='black', labelsize=8)
                
                ax.view_init(elev=self.current_elev, azim=self.current_azim)
                
                try:
                    self.current_elev = ax.elev
                    self.current_azim = ax.azim
                except:
                    pass
            
            self.fig.patch.set_facecolor('#2a2a2a')
            self.canvas.draw_idle()
        
        except Exception as e:
            print(f"Error dibujando detección: {e}")
            import traceback
            traceback.print_exc()
    
    # ============================================================================
    # FIN DE DETECTION TAB - INICIO DE SIGUIENTE SECCIÓN
    # ============================================================================


# ============================================================================
# PATRÓN DE CALIBRACIÓN (4 CÍRCULOS)
# ============================================================================

class CalibrationPattern:
    """
    Patrón de calibración con 4 círculos en configuración cuadrada.
    
    Especificaciones:
    - Cuadrado: 24 cm de lado (0.24 m)
    - Círculos: 15 cm de diámetro (0.075 m de radio)
    - Centros en las esquinas del cuadrado
    """
    
    def __init__(self):
        self.square_side = 0.24  # 24 cm en metros
        self.circle_radius = 0.075  # 15 cm / 2 en metros
        
        # Posición del centro del patrón en el espacio 3D
        self.center_x = 0.0
        self.center_y = 0.0
        self.center_z = 0.0
        
        # Rotación (ángulos en grados): rotaciones "reales" empiezan en 0
        self.rotation_x = 0.0  # Roll
        self.rotation_y = 0.0  # Pitch
        self.rotation_z = 0.0  # Yaw

        # Offset de visualización: muestra la máscara vertical (90° en X)
        # Este offset se aplica SOLO para renderizado/visualización y NO
        # modifica las coordenadas ni la metadata guardada.
        self.display_rotation_offset = np.array([90.0, 0.0, 0.0])

        # Actualizar puntos
        self._update_circle_centers()
    
    def _update_circle_centers(self):
        """Calcula las posiciones de los 4 centros de círculos con rotación."""
        half_side = self.square_side / 2
        
        # Coordenadas relativas (antes de rotación)
        local_centers = np.array([
            [-half_side, -half_side, 0],  # Inferior izquierda
            [ half_side, -half_side, 0],  # Inferior derecha
            [ half_side,  half_side, 0],  # Superior derecha
            [-half_side,  half_side, 0],  # Superior izquierda
        ])
        
        # Aplicar rotaciones (en radianes, desde grados)
        rx = np.radians(self.rotation_x)
        ry = np.radians(self.rotation_y)
        rz = np.radians(self.rotation_z)
        
        # Matrices de rotación
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(rx), -np.sin(rx)],
            [0, np.sin(rx), np.cos(rx)]
        ])
        
        Ry = np.array([
            [np.cos(ry), 0, np.sin(ry)],
            [0, 1, 0],
            [-np.sin(ry), 0, np.cos(ry)]
        ])
        
        Rz = np.array([
            [np.cos(rz), -np.sin(rz), 0],
            [np.sin(rz), np.cos(rz), 0],
            [0, 0, 1]
        ])
        
        # Combinar rotaciones: Rz * Ry * Rx (ZYX order)
        R = Rz @ Ry @ Rx
        
        # Aplicar rotación a cada punto local
        rotated_centers = np.array([R @ point for point in local_centers])
        
        # Aplicar translación
        self.local_centers = local_centers  # Guardar sin rotación
        self.world_centers = rotated_centers + np.array([
            self.center_x, self.center_y, self.center_z
        ])
    
    def get_circle_centers(self, scale=1.0):
        """Retorna los 4 centros de círculos en coordenadas mundiales.
        
        Args:
            scale: Factor de escala del patrón (1.0 = tamaño normal, 2.0 = doble tamaño)
        
        La escala se aplica respecto al centro del patrón, manteniendo la separación
        entre círculos proporcional al tamaño. ✅ Incluye rotación completa.
        """
        self._update_circle_centers()
        
        # Aplicar escala: los centros locales (sin rotar) se multiplican por la escala
        scaled_local_centers = self.local_centers * scale
        
        # Aplicar rotaciones a los centros escalados
        rx = np.radians(self.rotation_x)
        ry = np.radians(self.rotation_y)
        rz = np.radians(self.rotation_z)
        
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(rx), -np.sin(rx)],
            [0, np.sin(rx), np.cos(rx)]
        ])
        
        Ry = np.array([
            [np.cos(ry), 0, np.sin(ry)],
            [0, 1, 0],
            [-np.sin(ry), 0, np.cos(ry)]
        ])
        
        Rz = np.array([
            [np.cos(rz), -np.sin(rz), 0],
            [np.sin(rz), np.cos(rz), 0],
            [0, 0, 1]
        ])
        
        R = Rz @ Ry @ Rx
        
        # Rotar los centros escalados
        rotated_scaled_centers = np.array([R @ point for point in scaled_local_centers])
        
        # Aplicar translación al centro del patrón
        center_offset = np.array([self.center_x, self.center_y, self.center_z])
        scaled_world_centers = rotated_scaled_centers + center_offset
        
        return scaled_world_centers.copy()

    def get_logical_circle_centers(self, scale=1.0):
        """Alias explícito para los centros lógicos (rotación real, sin offset visual)."""
        return self.get_circle_centers(scale)

    def get_display_circle_centers(self, scale=1.0):
        """Centros para visualización aplicando el offset visual.

        Devuelve los centros transformados por el offset pero NO altera
        las rotaciones reales almacenadas en el objeto.
        """
        # Guardar estado
        rx0, ry0, rz0 = self.rotation_x, self.rotation_y, self.rotation_z
        try:
            # Aplicar offset temporal
            self.rotation_x = rx0 + float(self.display_rotation_offset[0])
            self.rotation_y = ry0 + float(self.display_rotation_offset[1])
            self.rotation_z = rz0 + float(self.display_rotation_offset[2])
            centers = self.get_circle_centers(scale)
        finally:
            # Restaurar rotaciones reales
            self.rotation_x, self.rotation_y, self.rotation_z = rx0, ry0, rz0

        return centers

    def detect_double_rotation(self) -> bool:
        """Detecta si hay una posible doble rotación entre la lógica y el offset visual.

        La GUI usa un offset visual de 90° en X para mostrar la máscara vertical.
        Si además la rotación lógica también está cerca de 90° en X, hay riesgo de
        aplicar dos veces la misma orientación.
        """
        rx_mod = abs(float(self.rotation_x)) % 360.0
        offset_x = abs(float(self.display_rotation_offset[0])) % 360.0
        return np.isclose(rx_mod, offset_x, atol=1e-3)

    def debug_state(self, scale=1.0) -> None:
        """Imprime el estado matemático del patrón para depuración."""
        logical = self.get_logical_circle_centers(scale)
        display = self.get_display_circle_centers(scale)

        print("[PATTERN] ===== ESTADO DEL PATRÓN =====")
        print(f"[PATTERN] Centro: ({self.center_x:.4f}, {self.center_y:.4f}, {self.center_z:.4f})")
        print(f"[PATTERN] Rotación lógica: X={self.rotation_x:.2f}°, Y={self.rotation_y:.2f}°, Z={self.rotation_z:.2f}°")
        print(f"[PATTERN] Offset visual: X={float(self.display_rotation_offset[0]):.2f}°, Y={float(self.display_rotation_offset[1]):.2f}°, Z={float(self.display_rotation_offset[2]):.2f}°")
        print(f"[PATTERN] Escala: {scale:.4f}")
        print(f"[PATTERN] Doble rotación sospechosa: {'SI' if self.detect_double_rotation() else 'NO'}")

        for name, pts in [("LOGICAL", logical), ("DISPLAY", display)]:
            print(f"[PATTERN] {name} centers:")
            for i, p in enumerate(pts, start=1):
                print(f"[PATTERN]   #{i}: X={p[0]: .6f}  Y={p[1]: .6f}  Z={p[2]: .6f}")
    
    def move(self, dx, dy, dz):
        """Mueve el patrón completo."""
        self.center_x += dx
        self.center_y += dy
        self.center_z += dz
    
    def rotate(self, rx=0, ry=0, rz=0):
        """Rota el patrón (en grados)."""
        self.rotation_x += rx
        self.rotation_y += ry
        self.rotation_z += rz
    
    def reset(self):
        """Reinicia el patrón a posición y orientación inicial vertical."""
        self.center_x = 0.0
        self.center_y = 0.0
        self.center_z = 0.0
        # Mantener rotaciones lógicas en 0; la orientación vertical es solo visual
        self.rotation_x = 0.0
        self.rotation_y = 0.0
        self.rotation_z = 0.0


# ============================================================================
# VISTA 3D CON PATRÓN DE CALIBRACIÓN
# ============================================================================


class CalibratorGUI(QMainWindow):
    """Aplicación principal del Visor Rosbag 3D."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visor Interactivo de Rosbag 3D")
        self.setGeometry(100, 100, 1400, 900)
        
        # Backend
        self.bag_path = None
        self.indexer = None
        self.navigator = None
        self.loader = None
        self.ros_live_loader = None
        self.is_ros_mode = False
        
        # Sensores habilitados (por defecto todos)
        self.sensors_enabled = {
            "stereo": True,
            "thermal": True,
            "lidar": True,
        }
        
        # Caché y optimización
        self.last_frame_index = None
        self.last_update_time = 0
        self.update_interval = 0.1  # Máximo 10 FPS
        
        # Timer para actualización en vivo ROS
        from PyQt5.QtCore import QTimer
        self.ros_update_timer = QTimer()
        self.ros_update_timer.timeout.connect(self.on_load_frame)
        self.ros_update_timer.setInterval(100)  # Actualizar cada 100ms (10 FPS)
        
        # Sistema de frames confirmados para detección manual
        self.confirmed_frames = []  # Lista de {frame_idx, sensor, topic, timestamp, points}
        self.current_confirmed_frame_idx = None  # Índice del frame confirmado seleccionado
        
        # UI
        self.init_ui()
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Listo. Cargue un archivo rosbag o conéctese a ROS en vivo.")
    
    def init_ui(self):
        """Inicializa la interfaz de usuario."""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        
        # Panel superior: Control de archivo
        file_panel = self.create_file_panel()
        main_layout.addLayout(file_panel)
        
        # Panel de frame selector
        range_panel = self.create_range_panel()
        main_layout.addLayout(range_panel)
        
        # Layout horizontal: Tabs a la derecha + Panel lateral a la izquierda
        content_layout = QHBoxLayout()
        
        # Tabs de sensores (lado derecho, principal)
        self.tabs = QTabWidget()
        self.tab_stereo = SensorTabStereoCamera()
        self.tab_thermal = SensorTabThermalCamera()
        self.tab_lidar = SensorTabLiDAR()
        self.tab_3d = SensorTab3D(parent_gui=self)
        self.tab_detection = DetectionTab()
        self.tab_detection.set_parent_gui(self)
        
        self.tabs.addTab(self.tab_stereo, "📷 Estéreo (RGB)")
        self.tabs.addTab(self.tab_thermal, "🔥 Térmal")
        self.tabs.addTab(self.tab_lidar, "📡 LiDAR")
        self.tabs.addTab(self.tab_3d, "🎲 Vista 3D")
        self.tabs.addTab(self.tab_detection, "🎯 Detección")
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        content_layout.addWidget(self.tabs, 1)
        
        # Panel lateral (lado izquierdo): Frames confirmados
        sidebar_layout = self.create_sidebar_panel()
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)
        sidebar_widget.setMaximumWidth(250)
        content_layout.addWidget(sidebar_widget)
        
        main_layout.addLayout(content_layout, 1)
        
        # Panel inferior
        control_panel = self.create_control_panel()
        main_layout.addLayout(control_panel)
        
        main_widget.setLayout(main_layout)
    
    def create_file_panel(self) -> QHBoxLayout:
        """Panel para cargar archivo."""
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Archivo:"))
        self.file_label = QLabel("Ninguno cargado")
        layout.addWidget(self.file_label)
        
        btn_open = QPushButton("📂 Abrir Bag")
        btn_open.clicked.connect(self.on_open_file)
        layout.addWidget(btn_open)
        
        btn_sensors = QPushButton("⚙️ Sensores")
        btn_sensors.clicked.connect(self.on_configure_sensors)
        layout.addWidget(btn_sensors)
        
        layout.addStretch()
        return layout
    
    def create_range_panel(self) -> QHBoxLayout:
        """Panel para seleccionar frame a visualizar con línea de tiempo visual."""
        layout = QHBoxLayout()
        
        # ========== MODO ARCHIVO .BAG ==========
        layout.addWidget(QLabel("Frame:"))
        self.spin_frame = QSpinBox()
        self.spin_frame.setMinimum(0)
        self.spin_frame.setValue(0)
        self.spin_frame.setMaximumWidth(80)
        layout.addWidget(self.spin_frame)
        
        btn_load = QPushButton("📂 Cargar")
        btn_load.clicked.connect(self.on_load_frame)
        btn_load.setMaximumWidth(80)
        layout.addWidget(btn_load)
        

        
        # Información de progreso
        self.label_total_frames = QLabel("Total: 0")
        self.label_total_frames.setMinimumWidth(120)
        self.label_total_frames.setStyleSheet(
            "background: #f0f0f0; padding: 4px; border-radius: 3px; font-weight: bold;"
        )
        layout.addWidget(self.label_total_frames)
        
        layout.addStretch()
        return layout
    

    
    
    def create_sidebar_panel(self) -> QVBoxLayout:
        """Panel lateral con lista de frames confirmados."""
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("📋 Frames Confirmados"))
        
        # Lista de frames confirmados
        self.confirmed_frames_list = QListWidget()
        self.confirmed_frames_list.itemClicked.connect(self.on_confirmed_frame_selected)
        layout.addWidget(self.confirmed_frames_list)
        
        # Botones para gestionar frames
        btn_layout = QVBoxLayout()
        
        btn_delete = QPushButton("🗑️ Borrar")
        btn_delete.clicked.connect(self.on_delete_confirmed_frame)
        btn_layout.addWidget(btn_delete)
        
        btn_clear_all = QPushButton("🧹 Limpiar Todo")
        btn_clear_all.clicked.connect(self.on_clear_all_frames)
        btn_layout.addWidget(btn_clear_all)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        return layout
    
    def create_control_panel(self) -> QHBoxLayout:
        """Panel de controles adicionales."""
        layout = QHBoxLayout()
        
        layout.addWidget(QLabel("Multiplicador:"))
        self.spin_multiplier = QDoubleSpinBox()
        self.spin_multiplier.setMinimum(0.1)
        self.spin_multiplier.setMaximum(100.0)
        self.spin_multiplier.setValue(10.0)
        self.spin_multiplier.setSingleStep(0.1)
        layout.addWidget(self.spin_multiplier)
        
        layout.addSpacing(20)
        
        btn_save_single = QPushButton("💾 Guardar Coordenadas")
        btn_save_single.clicked.connect(self.on_save_single_coordinate)
        layout.addWidget(btn_save_single)
        
        btn_save_all = QPushButton("💾 Guardar Todas las Coordenadas Salvadas")
        btn_save_all.clicked.connect(self.on_save_all_coordinates_yaml)
        layout.addWidget(btn_save_all)
        
        btn_confirm = QPushButton("✓ Confirmar Frame")
        btn_confirm.clicked.connect(self.on_confirm_frame)
        layout.addWidget(btn_confirm)
        
        layout.addStretch()
        return layout
    
    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================
    
    def on_open_file(self):
        """Abre un archivo rosbag o se conecta a ROS en vivo."""
        # Crear diálogo para elegir modo
        dialog = QDialog(self)
        dialog.setWindowTitle("Modo de Operación")
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("¿Cómo deseas cargar los datos?"))
        
        btn_bag = QPushButton("📂 Abrir archivo .bag")
        btn_live = QPushButton("🔴 Conectarse a ROS en vivo")
        btn_cancel = QPushButton("Cancelar")
        
        layout.addWidget(btn_bag)
        layout.addWidget(btn_live)
        layout.addWidget(btn_cancel)
        dialog.setLayout(layout)
        
        self.mode_selected = None
        btn_bag.clicked.connect(lambda: (setattr(self, 'mode_selected', 'bag'), dialog.accept()))
        btn_live.clicked.connect(lambda: (setattr(self, 'mode_selected', 'ros'), dialog.accept()))
        btn_cancel.clicked.connect(dialog.reject)
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        if self.mode_selected == 'bag':
            self._open_bag_file()
        elif self.mode_selected == 'ros':
            self._connect_ros_live()
    
    def _open_bag_file(self):
        """Abre un archivo rosbag (modo estático)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Abrir rosbag", "", "ROS Bag Files (*.bag)"
        )
        
        if not file_path:
            return
        
        try:
            self.statusBar.showMessage("Cargando bag... (esto puede tomar 1-2 minutos)")
            QApplication.processEvents()
            
            start = time.time()
            self.bag_path = file_path
            self.indexer = BagIndexer(file_path)
            self.navigator = FrameNavigator(self.indexer)
            self.loader = MessageLoader(self.indexer, self.navigator)
            self.ros_live_loader = None
            self.is_ros_mode = False
            
            elapsed = time.time() - start
            
            # Actualizar UI
            self.file_label.setText(Path(file_path).name)
            
            # Actualizar ranges
            max_frame = self.indexer.total_messages - 1
            self.spin_frame.setMaximum(max_frame)
            
            # Detectar sensores disponibles
            available_sensors = self.detect_available_sensors()
            
            # Mostrar diálogo de selección de sensores
            dialog = SensorSelectionDialog(self, available_sensors)
            if dialog.exec_() == QDialog.Accepted:
                self.sensors_enabled = dialog.get_selected_sensors()
                self.statusBar.showMessage(
                    f"Sensores: {self.get_enabled_sensors_str()} | "
                    f"Bag cargado: {self.indexer.total_messages} mensajes en {elapsed:.2f}s"
                )
            else:
                # Usuario canceló - descargar bag
                self.bag_path = None
                self.indexer = None
                self.navigator = None
                self.loader = None
                self.statusBar.showMessage("Carga de bag cancelada")
                return
            
            # Actualizar tópicos disponibles en las pestañas
            self.update_topic_selectors()
            
            # Actualizar indicador de total de frames
            max_frame = self.indexer.total_messages - 1
            self.label_total_frames.setText(
                f"Total: {max_frame + 1} frames"
            )
            
            # Cargar primer frame
            self.on_load_frame()
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando bag: {str(e)}")
            self.statusBar.showMessage(f"Error: {str(e)}")
    
    def _connect_ros_live(self):
        """Se conecta a ROS en vivo para detectar tópicos dinámicamente."""
        if ROSLiveListener is None:
            QMessageBox.warning(
                self,
                "No disponible",
                "ROSLiveListener no está disponible.\n"
                "Asegúrate de que ROS esté instalado y que el paquete esté correctamente configurado."
            )
            return
        
        try:
            # Importar rospy localmente (solo si usamos ROS en vivo)
            import rospy
            
            # Inicializar rospy si no está ya
            if not rospy.get_node_uri():
                rospy.init_node('calibrator_gui', anonymous=True, disable_signals=True)
            
            self.statusBar.showMessage("Conectando a ROS en vivo...")
            QApplication.processEvents()
            
            self.bag_path = None
            self.indexer = None
            self.navigator = None
            self.loader = None
            self.ros_live_loader = ROSLiveListener()
            self.is_ros_mode = True
            
            self.file_label.setText("🔴 ROS En Vivo")
            
            # Habilitar todos los sensores por defecto en modo ROS
            self.sensors_enabled = {
                'stereo': True,
                'thermal': True,
                'lidar': True,
            }
            
            self.statusBar.showMessage(
                f"Sensores: {self.get_enabled_sensors_str()} | "
                f"Conectado a ROS (detectando tópicos...)"
            )
            
            # Actualizar label con información inicial
            self.label_total_frames.setText("🔴 ROS En Vivo")
            
            # Escanear y detectar tópicos disponibles
            self.update_topic_selectors_ros()
            
            # Iniciar timer de actualización en vivo
            self.last_frame_index = -1
            self.ros_update_timer.start()
            self.on_load_frame()
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error conectando a ROS: {str(e)}")
            self.statusBar.showMessage(f"Error: {str(e)}")
    
    def on_configure_sensors(self):
        """Abre diálogo para configurar sensores activos."""
        if self.loader is None:
            QMessageBox.warning(self, "Advertencia", "Cargue un bag primero")
            return
        
        # Detectar sensores disponibles nuevamente
        available_sensors = self.detect_available_sensors()
        
        # Mostrar diálogo con selección actual
        dialog = SensorSelectionDialog(self, available_sensors)
        
        # Pre-seleccionar sensores actualmente habilitados
        for sensor_id, is_enabled in self.sensors_enabled.items():
            if sensor_id in dialog.sensor_checks:
                dialog.sensor_checks[sensor_id].setChecked(is_enabled)
        
        if dialog.exec_() == QDialog.Accepted:
            self.sensors_enabled = dialog.get_selected_sensors()
            self.statusBar.showMessage(
                f"Sensores: {self.get_enabled_sensors_str()}"
            )
            # Forzar actualización de display
            self.last_frame_index = None
            self.update_display()
    
    
    def on_load_frame(self):
        """Carga el frame especificado en el spinbox."""
        if self.is_ros_mode:
            self.update_display_ros()
        else:
            if self.navigator is None:
                return
            
            value = self.spin_frame.value()
            
            try:
                self.navigator.goto(value)
                self.update_display()
            except Exception as e:
                self.statusBar.showMessage(f"Error: {e}")
    

    

    
    def on_tab_changed(self, index):
        """Actualiza la pestaña cuando se cambia. Fuerza recarga de datos para Thermal."""
        # Forzar actualización de la pestaña actual
        self.last_frame_index = None
        
        # Si cambias a Thermal, asegúrate de que se cargan los datos térmicos
        if index == 1:  # Thermal
            # Forzar recarga de datos para garantizar que se captura imagen térmica
            self.update_display()
        else:
            self.update_display()
    
    def update_topic_selectors(self):
        """Actualiza los selectores de tópicos disponibles."""
        if self.loader is None:
            print("[DEBUG] Loader es None")
            return
        
        try:
            # Obtener tópicos identificados en TODO el bag (no solo frame actual)
            sensor_topics = self.loader.get_sensor_topics()
            print(f"[DEBUG] Sensor topics: {sensor_topics}")
            
            # Inicializar
            rgb_topics = []
            thermal_topics = []
            lidar_topics = []
            
            # Procesar imágenes
            if 'image' in sensor_topics:
                image_topics = sensor_topics['image']
                print(f"[DEBUG] Imágenes encontradas: {image_topics}")
                for topic in image_topics:
                    if 'thermal' in topic.lower() or 'flir' in topic.lower():
                        thermal_topics.append(topic)
                    else:
                        rgb_topics.append(topic)
            
            # Procesar LiDAR
            if 'pointcloud' in sensor_topics:
                lidar_topics = sensor_topics['pointcloud']
                print(f"[DEBUG] PointClouds encontrados: {lidar_topics}")

            # Recolectar TODOS los tópicos disponibles (para override manual)
            all_topics = []
            for key, topics in sensor_topics.items():
                if isinstance(topics, list):
                    all_topics.extend(topics)
                elif isinstance(topics, str):
                    all_topics.append(topics)
            all_topics = list(dict.fromkeys(all_topics))  # deduplicar preservando orden
            print(f"[DEBUG] Todos los tópicos disponibles: {all_topics}")

            # Actualizar selectores con tópicos filtrados por tipo (comportamiento original)
            print(f"[DEBUG] Actualizando: RGB={rgb_topics}, Thermal={thermal_topics}, LiDAR={lidar_topics}")
            self.tab_stereo.update_available_topics(rgb_topics if rgb_topics else ["(sin datos)"])
            self.tab_thermal.update_available_topics(thermal_topics if thermal_topics else ["(sin datos)"])
            if lidar_topics:
                self.tab_lidar.update_available_topics(lidar_topics)

            # Pasar todos los tópicos a cada pestaña para permitir override manual
            if all_topics:
                self.tab_stereo.set_all_topics(all_topics)
                self.tab_thermal.set_all_topics(all_topics)
                self.tab_lidar.set_all_topics(all_topics)
                self.tab_3d.set_all_topics(all_topics)
            
            # Mostrar resumen
            self.statusBar.showMessage(
                f"Tópicos detectados: {len(rgb_topics)} RGB, "
                f"{len(thermal_topics)} térmicos, {len(lidar_topics)} LiDAR"
                f" | {len(all_topics)} tópicos totales"
            )
            
        except Exception as e:
            print(f"[ERROR] update_topic_selectors: {e}")
            import traceback
            traceback.print_exc()

    
    def update_topic_selectors_ros(self):
        """Actualiza selectores de tópicos en modo ROS en vivo."""
        if self.ros_live_loader is None:
            print("[DEBUG] ROSLiveListener es None")
            return
        
        try:
            # Escanear nuevos tópicos disponibles
            self.ros_live_loader.scan_and_subscribe_topics()
            
            # Obtener tópicos detectados
            lidar_topics = self.ros_live_loader.get_available_lidar_topics()
            image_topics = self.ros_live_loader.get_available_image_topics()
            
            print(f"[DEBUG] Tópicos ROS detectados - LiDAR: {lidar_topics}, Imágenes: {image_topics}")
            
            # Categorizar imágenes en RGB y Térmicas
            rgb_topics = []
            thermal_topics = []
            for topic in image_topics:
                if 'thermal' in topic.lower() or 'flir' in topic.lower():
                    thermal_topics.append(topic)
                else:
                    rgb_topics.append(topic)
            
            # Recolectar TODOS los tópicos para override manual
            all_topics = list(dict.fromkeys(image_topics + lidar_topics))
            # Intentar obtener tópicos adicionales (IMU, GPS, etc.) si el loader los expone
            try:
                extra = self.ros_live_loader.get_available_topics()
                if isinstance(extra, list):
                    for t in extra:
                        if t not in all_topics:
                            all_topics.append(t)
            except AttributeError:
                pass
            print(f"[DEBUG] Todos los tópicos ROS: {all_topics}")

            # Actualizar selectores filtrados por tipo
            print(f"[DEBUG] Actualizando ROS: RGB={rgb_topics}, Thermal={thermal_topics}, LiDAR={lidar_topics}")
            self.tab_stereo.update_available_topics(rgb_topics if rgb_topics else ["(sin datos)"])
            self.tab_thermal.update_available_topics(thermal_topics if thermal_topics else ["(sin datos)"])
            if lidar_topics:
                self.tab_lidar.update_available_topics(lidar_topics)

            # Pasar todos los tópicos para override manual
            if all_topics:
                self.tab_stereo.set_all_topics(all_topics)
                self.tab_thermal.set_all_topics(all_topics)
                self.tab_lidar.set_all_topics(all_topics)
                self.tab_3d.set_all_topics(all_topics)
            
            # Mostrar resumen
            self.statusBar.showMessage(
                f"ROS - Tópicos: {len(rgb_topics)} RGB, "
                f"{len(thermal_topics)} térmicos, {len(lidar_topics)} LiDAR"
                f" | {len(all_topics)} tópicos totales"
            )
            
        except Exception as e:
            print(f"[ERROR] update_topic_selectors_ros: {e}")
            import traceback
            traceback.print_exc()

    
    def detect_available_sensors(self) -> dict:
        """Detecta qué sensores están disponibles en el bag."""
        available = {}
        try:
            data = self.loader.get_current_frame_data()
            
            # Detectar imágenes
            if 'images' in data and data['images']:
                for topic in data['images'].keys():
                    if 'thermal' in topic.lower() or 'flir' in topic.lower():
                        available['thermal'] = True
                    else:
                        available['stereo'] = True
            
            # Detectar LiDAR
            if 'pointcloud' in data and data['pointcloud'] is not None:
                available['lidar'] = True
        
        except Exception as e:
            print(f"Error detectando sensores: {e}")
        
        return available
    
    def get_enabled_sensors_str(self) -> str:
        """Retorna string con sensores habilitados."""
        enabled = []
        if self.sensors_enabled.get('stereo'):
            enabled.append("RGB")
        if self.sensors_enabled.get('thermal'):
            enabled.append("Térmica")
        if self.sensors_enabled.get('lidar'):
            enabled.append("LiDAR")
        return ", ".join(enabled) if enabled else "Ninguno"
    
    def update_display(self):
        """Actualiza la información mostrada (con limitador de tasa)."""
        if self.loader is None or self.navigator is None:
            return
        
        # Limitar actualizaciones a máximo 10 FPS
        current_time = time.time()
        if current_time - self.last_update_time < self.update_interval:
            return
        self.last_update_time = current_time
        
        try:
            pos = self.navigator.get_current_position()
            frame_idx = pos.global_index
            
            # Si es el mismo frame, no actualizar
            if self.last_frame_index == frame_idx:
                return
            
            self.last_frame_index = frame_idx
            
            # Cargar datos del frame
            data = self.loader.get_current_frame_data()
            
            # Solo actualizar la pestaña visible para optimizar
            current_tab = self.tabs.currentIndex()
            
            if current_tab == 0:
                # Tab Estéreo - verificar si está habilitado
                if self.sensors_enabled.get('stereo', True):
                    self.tab_stereo.update_data(data)
            elif current_tab == 1:
                # Tab Térmica - verificar si está habilitado
                if self.sensors_enabled.get('thermal', True):
                    self.tab_thermal.update_data(data)
            elif current_tab == 2:
                # Tab LiDAR - verificar si está habilitado
                if self.sensors_enabled.get('lidar', True):
                    self.tab_lidar.update_data(data)
            elif current_tab == 3:
                self.tab_3d.update_data(data)
            
        except Exception as e:
            self.statusBar.showMessage(f"Error actualizando display: {e}")
    
    def update_display_ros(self):
        """Actualiza la información desde ROS en vivo (sin frame navigator)."""
        if self.ros_live_loader is None:
            return
        
        # Limitar actualizaciones a máximo 10 FPS
        current_time = time.time()
        if current_time - self.last_update_time < self.update_interval:
            return
        self.last_update_time = current_time
        
        try:
            # Escanear nuevos tópicos cada 5 actualizaciones (aprox cada 0.5 seg)
            if not hasattr(self, '_ros_scan_counter'):
                self._ros_scan_counter = 0
            self._ros_scan_counter += 1
            if self._ros_scan_counter >= 5:
                self.update_topic_selectors_ros()
                self._ros_scan_counter = 0
            
            # Obtener datos del frame actual en el historial
            current_idx = self.ros_live_loader.get_current_frame_index()
            data = self.ros_live_loader.get_current_frame_data()
            
            # DEBUG
            print(f"[DISPLAY] Actualizando frame {current_idx}, timestamp={data['timestamp']}")
            
            # Si no hay timestamp, aún no hay datos
            if data['timestamp'] is None:
                print("[DISPLAY] Sin timestamp - sin datos aún")
                return
            
            # Actualizar label con frame actual/total
            total_frames = self.ros_live_loader.get_total_frames()
            frame_info = f"Frame: {current_idx + 1}/{total_frames}" if total_frames > 0 else "Sin datos"
            self.label_total_frames.setText(frame_info)
            
            # Actualizar todas las pestañas visibles
            current_tab = self.tabs.currentIndex()
            
            if current_tab == 0:
                if self.sensors_enabled.get('stereo', True):
                    self.tab_stereo.update_data(data)
            elif current_tab == 1:
                if self.sensors_enabled.get('thermal', True):
                    self.tab_thermal.update_data(data)
            elif current_tab == 2:
                if self.sensors_enabled.get('lidar', True):
                    self.tab_lidar.update_data(data)
            elif current_tab == 3:
                self.tab_3d.update_data(data)
            
        except Exception as e:
            print(f"[ERROR] Error en update_display_ros: {e}")
            import traceback
            traceback.print_exc()
    
    def on_save_single_coordinate(self):
        """Abre ventana para mostrar coordenadas del frame actual seleccionado."""
        if self.current_confirmed_frame_idx is None or len(self.confirmed_frames) == 0:
            QMessageBox.warning(
                self, "Advertencia", 
                "Selecciona un frame de la lista 'Frames Confirmados' primero.\n"
                "Las coordenadas aparecerán en la nueva ventana."
            )
            return
        
        # Obtener frame seleccionado
        frame_info = self.confirmed_frames[self.current_confirmed_frame_idx]
        
        # Abre el diálogo con las coordenadas
        dialog = CoordinatesDisplayDialog(frame_info, self)
        dialog.exec_()
    
    def on_save_all_coordinates_yaml(self):
        """Guarda TODAS las coordenadas en un archivo YAML."""
        print(f"\n[SAVE_YAML] Iniciando guardado de TODAS las coordenadas...")
        print(f"[SAVE_YAML] Total de frames confirmados: {len(self.confirmed_frames)}")
        
        if not self.confirmed_frames:
            QMessageBox.warning(self, "Advertencia", "No hay frames confirmados para guardar.")
            return
        
        try:
            import yaml
            from pathlib import Path

            # Mantener una clave YAML por detector/sensor para evitar mezclar
            # frames de diferentes sensores bajo la misma ruta.
            sensor_key_map = {
                'lidar': '/lidar_detector/lidar_pattern',
                'radar': '/radar_detector/radar_pattern',
                'mono': '/mono_detector/mono_pattern_flir',
                'thermal': '/mono_detector/mono_pattern_flir',
                'stereo': '/stereo_detector/stereo_pattern',
                'rgb': '/stereo_detector/stereo_pattern',
                'zed': '/stereo_detector/stereo_pattern',
                'camera': '/stereo_detector/stereo_pattern',
            }
            data_to_save = {}

            for i, frame_info in enumerate(self.confirmed_frames):
                sensor_name = str(frame_info.get('sensor', 'unknown')).lower()
                raw_topic = str(frame_info.get('topic') or frame_info.get('frame_id') or sensor_name)
                raw_topic_lower = raw_topic.lower()
                yaml_sensor_key = sensor_key_map.get(sensor_name, raw_topic)

                # Clasificación por topic real para no mezclar la nube ZED con LiDAR.
                if 'zed' in raw_topic_lower or 'cloud_registered' in raw_topic_lower or 'point_cloud' in raw_topic_lower:
                    yaml_sensor_key = '/stereo_detector/stereo_pattern'
                elif 'velodyne' in raw_topic_lower or 'lidar' in raw_topic_lower:
                    yaml_sensor_key = '/lidar_detector/lidar_pattern'
                elif 'flir' in raw_topic_lower or sensor_name in {'mono', 'thermal'}:
                    yaml_sensor_key = '/mono_detector/mono_pattern_flir'

                print(f"[SAVE_YAML] Frame {i+1}: sensor={sensor_name} -> yaml_key={yaml_sensor_key}")
                print(f"[SAVE_YAML]   Sensor: {frame_info.get('sensor', 'unknown')}")
                print(f"[SAVE_YAML]   Puntos: {len(frame_info.get('points', []))}")

                points_list = []
                for p in frame_info.get('points', []):
                    if isinstance(p, dict):
                        points_list.append({'x': float(p['x']), 'y': float(p['y']), 'z': float(p['z'])})
                    elif isinstance(p, (list, tuple)):
                        points_list.append({'x': float(p[0]), 'y': float(p[1]), 'z': float(p[2])})

                if yaml_sensor_key not in data_to_save:
                    data_to_save[yaml_sensor_key] = []

                data_to_save[yaml_sensor_key].append({
                    'frame_id': raw_topic,
                    'points': points_list,
                })
            
            # Elegir archivo de salida
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Guardar Todas las Coordenadas", "", "YAML Files (*.yaml);;All Files (*)"
            )
            
            if not file_path:
                print(f"[SAVE_YAML] Operación cancelada por el usuario")
                return
            
            # Guardar YAML
            with open(file_path, 'w') as f:
                            yaml.safe_dump(data_to_save, f, default_flow_style=False, sort_keys=False)
            
            print(f"[SAVE_YAML] ✅ Guardado exitosamente en: {file_path}")
            print(f"[SAVE_YAML] Total de frames guardados: {len(data_to_save)}")
            
            QMessageBox.information(
                self, "✅ Éxito", 
                f"Todas las coordenadas guardadas en:\n{file_path}\n"
                f"Total de frames: {len(self.confirmed_frames)}"
            )
            print(f"✅ Guardado completado\n")
            
        except ImportError:
            QMessageBox.critical(self, "Error", "PyYAML no está instalado.\nInstala con: pip install pyyaml")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error guardando coordenadas:\n{str(e)}")
    
    def on_confirm_frame(self):
        """Confirma el frame actual del sensor visualizado."""
        current_tab = self.tabs.currentIndex()
        current_frame_idx = self.spin_frame.value() if not self.is_ros_mode else self.ros_live_loader.get_current_frame_index()
        
# Determinar qué sensor está activo.
        # Importante: en la vista 3D hay dos fuentes distintas (LiDAR y ZED point cloud).
        # No todas las nubes 3D son LiDAR; si el topic contiene ZED/point_cloud/cloud_registered,
        # debemos tratarlo como sensor estéreo/zed, no como LiDAR.
        sensor_map = {
            0: 'stereo',
            1: 'thermal',
            2: 'lidar',
            3: 'lidar'  # Vista 3D es el punto de entrada; se re-evalúa por topic real abajo
        }
        sensor = sensor_map.get(current_tab, 'unknown')
        
        # Determinar si debe ser 2D o 3D
        is_2d_sensor = (current_tab == 0 or current_tab == 1)  # Stereo o Thermal en 2D
        
        # Obtener tópico seleccionado según el sensor
        topic = None
        sensor_data = None  # Datos del sensor para visualización
        
        if current_tab == 0:
            topic = self.tab_stereo.get_selected_topic()
            # Capturar imagen RGB
            if hasattr(self.tab_stereo, 'last_image_data') and self.tab_stereo.last_image_data is not None:
                sensor_data = self.tab_stereo.last_image_data.copy()
        elif current_tab == 1:
            topic = self.tab_thermal.get_selected_topic()
            # Capturar imagen térmica EXPLÍCITAMENTE desde tab_thermal
            if hasattr(self.tab_thermal, 'last_image_data') and self.tab_thermal.last_image_data is not None:
                sensor_data = self.tab_thermal.last_image_data.copy()
                print(f"✅ Frame confirmado: THERMAL - Shape: {sensor_data.shape}, Topic: {topic}")
            else:
                print(f"⚠️  Frame confirmado: THERMAL pero sin datos! Topic: {topic}, last_image_topic: {getattr(self.tab_thermal, 'last_image_topic', 'None')}")
        elif current_tab == 2:
            topic = self.tab_lidar.get_selected_topic()
            # Capturar nube de puntos LiDAR
            if hasattr(self.tab_lidar, 'last_pointcloud') and self.tab_lidar.last_pointcloud is not None:
                sensor_data = self.tab_lidar.last_pointcloud.copy() if isinstance(self.tab_lidar.last_pointcloud, np.ndarray) else self.tab_lidar.last_pointcloud
        elif current_tab == 3:
            topic = self.tab_3d.selected_lidar_topic
            # Capturar nube de puntos desde Vista 3D.
            # La fuente real puede ser LiDAR o la nube registrada de ZED, por eso hay que
            # clasificar por el topic, no solo por la pestaña.
            if hasattr(self.tab_3d, 'last_pointcloud') and self.tab_3d.last_pointcloud is not None:
                sensor_data = self.tab_3d.last_pointcloud.copy() if isinstance(self.tab_3d.last_pointcloud, np.ndarray) else self.tab_3d.last_pointcloud

            if topic is not None:
                topic_lower = topic.lower()
                if 'zed' in topic_lower or 'cloud_registered' in topic_lower or 'point_cloud' in topic_lower:
                    sensor = 'stereo'
                elif 'velodyne' in topic_lower or 'lidar' in topic_lower:
                    sensor = 'lidar'
                else:
                    sensor = 'lidar'

        # Obtener timestamp
        timestamp = 0.0
        if self.is_ros_mode and self.ros_live_loader:
            data = self.ros_live_loader.get_current_frame_data()
            timestamp = data.get('timestamp', 0.0)
        elif self.navigator:
            pos = self.navigator.get_current_position()
            timestamp = pos.timestamp
        
        # Crear entrada del frame confirmado
        frame_entry = {
            'frame_idx': current_frame_idx,
            'sensor': sensor,
            'topic': topic,
            'timestamp': timestamp,
            'points': [],  # Se llenará con los centros de la máscara
            'sensor_data': sensor_data,  # Imagen o nube de puntos del sensor
            'is_2d': is_2d_sensor  # Indica si debe renderizarse en 2D o 3D
        }

        # Si capturamos una imagen de disparidad (float32 2D), generar
        # una versión de visualización (uint8 RGB) y guardarla junto al frame
        try:
            if isinstance(sensor_data, np.ndarray) and sensor_data.dtype.kind == 'f' and sensor_data.ndim == 2:
                disp = sensor_data.astype(np.float32)
                finite = np.isfinite(disp)
                if finite.any():
                    vmin = float(np.nanpercentile(disp[finite], 2))
                    vmax = float(np.nanpercentile(disp[finite], 98))
                    norm = np.clip((disp - vmin) / (vmax - vmin + 1e-6), 0.0, 1.0)
                else:
                    norm = np.zeros_like(disp)

                # Map to colormap (viridis) and convert to uint8 RGB
                try:
                    import matplotlib.cm as cm
                    cmap = cm.get_cmap('viridis')
                    rgba = cmap(norm)
                    rgb = (rgba[:, :, :3] * 255).astype(np.uint8)
                    frame_entry['sensor_display'] = rgb
                except Exception:
                    # Fallback: grayscale
                    frame_entry['sensor_display'] = (norm * 255).astype(np.uint8)
        except Exception:
            pass
        
        # 🆕 SIEMPRE capturar los centros de la máscara desde tab_detection
        # (independientemente de qué pestaña esté activa)
        print(f"\n[CONFIRM] ===== CONFIRMANDO FRAME {current_frame_idx} (SENSOR: {sensor.upper()}) =====")
        print(f"[CONFIRM] Pattern visible: {self.tab_detection.pattern_visible}")
        print(f"[CONFIRM] Pattern scale: {self.tab_detection.pattern_scale}")
        print(f"[CONFIRM] Has calibration_pattern: {hasattr(self.tab_detection, 'calibration_pattern')}")
        
        if hasattr(self.tab_detection, 'calibration_pattern') and self.tab_detection.calibration_pattern is not None:
            try:
                pattern = self.tab_detection.calibration_pattern
                print(f"[CONFIRM] ✓ Patrón existe")
                print(f"[CONFIRM]   Centro: ({pattern.center_x:.4f}, {pattern.center_y:.4f}, {pattern.center_z:.4f})")
                print(f"[CONFIRM]   Rotación: X={pattern.rotation_x:.2f}°, Y={pattern.rotation_y:.2f}°, Z={pattern.rotation_z:.2f}°")
                print(f"[CONFIRM]   Square side: {pattern.square_side:.4f}")
                print(f"[CONFIRM]   Local centers shape: {pattern.local_centers.shape if hasattr(pattern, 'local_centers') else 'N/A'}")
                print(f"[CONFIRM]   Doble rotación sospechosa: {'SI' if pattern.detect_double_rotation() else 'NO'}")
                
                # ── Coordenadas LÓGICAS (sistema de referencia del sensor) ──────────
                # Las coordenadas visuales (get_display_circle_centers) sólo sirven
                # para el renderizado en pantalla.  Lo que se exporta al YAML son
                # siempre las coordenadas lógicas, expresadas en el sistema propio
                # del sensor:
                #   - LiDAR / nube de puntos : metros (X, Y, Z en frame del sensor)
                #   - Cámara 2D (stereo/thermal/rgb) : píxeles normalizados [0-1]
                #     relativo al ancho/alto de la imagen capturada.
                scale = self.tab_detection.pattern_scale
                is_2d_frame = frame_entry.get('is_2d', False)

                print(f"[CONFIRM]   Llamando get_logical_circle_centers(scale={scale})...")
                logical_centers = pattern.get_logical_circle_centers(scale)
                print(f"[CONFIRM] Resultado logical_centers: {logical_centers}")

                if logical_centers is not None and len(logical_centers) > 0:
                    print(f"[CONFIRM] ✅ Centros lógicos obtenidos: {len(logical_centers)} puntos")

                    points_out = []

                    if is_2d_frame:
                        # ── Caso 2D: convertir metros → píxeles normalizados ─────────
                        # Intentar obtener dimensiones reales de la imagen capturada.
                        img_shape = None
                        sensor_data_local = frame_entry.get('sensor_data')
                        if isinstance(sensor_data_local, np.ndarray):
                            img_shape = sensor_data_local.shape[:2]  # (H, W)

                        if img_shape is not None:
                            img_h, img_w = img_shape
                            min_dim = min(img_w, img_h)
                            scale_px_per_m = min_dim / 0.24
                            offset_x = (img_w - min_dim) / 2
                            offset_y = (img_h - min_dim) / 2

                            for i, center in enumerate(logical_centers):
                                # Los centros lógicos están en metros con el centro
                                # del patrón como origen.  Convertir a píxeles
                                # absolutos y luego normalizar a [0, 1].
                                px = offset_x + (float(center[0]) + 0.12 * scale) * scale_px_per_m
                                py = offset_y + (float(center[1]) + 0.12 * scale) * scale_px_per_m
                                x_norm = px / img_w
                                y_norm = py / img_h
                                points_out.append({'x': x_norm, 'y': y_norm, 'z': 0.0})
                                print(f"  ✓ Círculo {i+1} [2D px-norm]: X={x_norm:.6f}, Y={y_norm:.6f}")
                        else:
                            # Sin imagen de referencia: guardar metros directamente
                            print("[CONFIRM] ⚠️  Sin imagen de referencia para 2D; guardando metros")
                            for i, center in enumerate(logical_centers):
                                x_m = float(center[0])
                                y_m = float(center[1])
                                points_out.append({'x': x_m, 'y': y_m, 'z': 0.0})
                                print(f"  ✓ Círculo {i+1} [2D m]: X={x_m:.6f}, Y={y_m:.6f}")
                    else:
                        # ── Caso 3D: guardar metros en frame del sensor (LiDAR) ──────
                        for i, center in enumerate(logical_centers):
                            x_m = float(center[0])
                            y_m = float(center[1])
                            z_m = float(center[2])
                            points_out.append({'x': x_m, 'y': y_m, 'z': z_m})
                            print(f"  ✓ Círculo {i+1} [3D m]: X={x_m:.6f}, Y={y_m:.6f}, Z={z_m:.6f}")

                    frame_entry['points'] = points_out

                    # Metadata: posición/rotación/escala LÓGICAS (no visuales)
                    frame_entry['mask_metadata'] = {
                        'position': {
                            'x': float(pattern.center_x),
                            'y': float(pattern.center_y),
                            'z': float(pattern.center_z)
                        },
                        'rotation': {
                            'x': float(pattern.rotation_x),
                            'y': float(pattern.rotation_y),
                            'z': float(pattern.rotation_z)
                        },
                        'scale': float(scale),
                        'num_circles': len(points_out),
                        'coord_system': 'px_normalized' if is_2d_frame else 'meters_sensor_frame'
                    }

                    print(f"✅ Frame {current_frame_idx} guardado con {len(points_out)} centros "
                          f"({'px norm' if is_2d_frame else 'm sensor frame'})\n")
                else:
                    print(f"⚠️  ADVERTENCIA: get_logical_circle_centers() devolvió None o lista vacía")
                    # Fallback: local_centers escalados (siempre en metros)
                    points_out = []
                    if hasattr(pattern, 'local_centers') and pattern.local_centers is not None:
                        for i, center in enumerate(pattern.local_centers):
                            x_m = float(center[0]) * scale
                            y_m = float(center[1]) * scale
                            z_m = float(center[2]) * scale
                            points_out.append({'x': x_m, 'y': y_m, 'z': z_m})
                            print(f"  ✓ Círculo {i+1} (fallback): X={x_m:.6f}, Y={y_m:.6f}, Z={z_m:.6f}")
                    frame_entry['points'] = points_out
                    
            except Exception as e:
                print(f"❌ ERROR al capturar centros: {e}")
                import traceback
                traceback.print_exc()
                frame_entry['points'] = []
        else:
            print(f"⚠️  calibration_pattern no existe o es None")
            frame_entry['points'] = []
        
        self.confirmed_frames.append(frame_entry)
        
        # Actualizar lista visual
        self._update_confirmed_frames_list()
        
        # Seleccionar este frame en la lista
        self.confirmed_frames_list.setCurrentRow(len(self.confirmed_frames) - 1)
        
        # Mostrar estadísticas
        num_puntos = len(frame_entry['points'])
        QMessageBox.information(
            self, "Frame Confirmado",
            f"✅ Frame {current_frame_idx} confirmado\n"
            f"Sensor: {sensor}\n"
            f"Tópico: {topic}\n"
            f"Puntos guardados: {num_puntos}\n"
            f"Timestamp: {timestamp:.6f}"
        )
    
    def _update_confirmed_frames_list(self):
        """Actualiza la lista visual de frames confirmados."""
        self.confirmed_frames_list.clear()
        
        for i, frame_info in enumerate(self.confirmed_frames):
            item_text = (
                f"#{i+1} Frame {frame_info['frame_idx']}\n"
                f"  {frame_info['sensor']} | {frame_info.get('topic', 'N/A')}\n"
                f"  Puntos: {len(frame_info['points'])}"
            )
            self.confirmed_frames_list.addItem(item_text)
    
    def on_confirmed_frame_selected(self, item):
        """Maneja selección de frame confirmado desde la lista."""
        row = self.confirmed_frames_list.row(item)
        if 0 <= row < len(self.confirmed_frames):
            self.current_confirmed_frame_idx = row
            frame_info = self.confirmed_frames[row]
            
            print(f"\n{'='*60}")
            print(f"📍 Frame seleccionado: #{row+1} (frame_idx={frame_info['frame_idx']})")
            print(f"   Sensor: {frame_info.get('sensor', 'N/A')}")
            print(f"   Topic: {frame_info.get('topic', 'N/A')}")
            print(f"   Timestamp: {frame_info.get('timestamp', 'N/A')}")
            print(f"   Puntos: {len(frame_info.get('points', []))} / Tipo: {type(frame_info.get('points', []))}")
            if frame_info.get('points'):
                print(f"   Primer punto: {frame_info['points'][0]}")
            print(f"{'='*60}\n")
            
            # Limpiar selección de puntos en el tab 3D
            self.tab_3d.clear_selection()
            
            # Actualizar spin_frame para que muestre este frame
            if not self.is_ros_mode and self.navigator:
                self.spin_frame.blockSignals(True)
                self.spin_frame.setValue(frame_info['frame_idx'])
                self.spin_frame.blockSignals(False)
                self.on_load_frame()
            
            print(f"📍 Frame seleccionado: #{row+1} (frame_idx={frame_info['frame_idx']})")
            
            # Si el sensor es LiDAR/3D, seleccionar el tópico correcto
            if frame_info['sensor'] in ['lidar']:
                if frame_info.get('topic'):
                    self.tab_3d.topic_combo.setCurrentText(frame_info['topic'])
            
            # 🎯 NUEVO: Mostrar pestaña de Detección con los puntos guardados
            print(f"[DEBUG] Llamando display_detection() con {len(frame_info.get('points', []))} puntos")
            self.tab_detection.display_detection(frame_info)
            self.tabs.setCurrentWidget(self.tab_detection)
            print(f"🎯 Pestaña Detección abierta con {len(frame_info.get('points', []))} puntos")
    
    def on_delete_confirmed_frame(self):
        """Borra el frame confirmado seleccionado."""
        if self.current_confirmed_frame_idx is not None:
            row = self.current_confirmed_frame_idx
            if 0 <= row < len(self.confirmed_frames):
                removed = self.confirmed_frames.pop(row)
                print(f"❌ Frame eliminado: #{row+1}")
                self._update_confirmed_frames_list()
                self.current_confirmed_frame_idx = None
    
    def on_clear_all_frames(self):
        """Limpia todos los frames confirmados."""
        reply = QMessageBox.question(
            self, "Confirmar",
            "¿Borrar todos los frames confirmados?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.confirmed_frames = []
            self.confirmed_frames_list.clear()
            self.current_confirmed_frame_idx = None
            self.tab_3d.clear_selection()
            print("🧹 Todos los frames limpiados")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Punto de entrada principal."""
    app = QApplication(sys.argv)
    
    # Ensure backend is imported AFTER QApplication is created
    _ensure_backend_imported()
    
    # Aplicar estilo
    app.setStyle('Fusion')
    
    # Crear ventana
    gui = CalibratorGUI()
    gui.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()