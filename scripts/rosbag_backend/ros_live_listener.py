#!/usr/bin/env python3
"""
Módulo de escucha en vivo de ROS
Detecta y se suscribe a tópicos de sensores mientras corren en el ROS master
"""

import rospy
import numpy as np
from typing import Dict, Optional, Any, List, Callable
from collections import OrderedDict
import threading
import time

try:
    import sensor_msgs.point_cloud2 as pc2
    HAS_PC2 = True
except ImportError:
    HAS_PC2 = False

try:
    from cv_bridge import CvBridge
    HAS_CV_BRIDGE = True
except ImportError:
    HAS_CV_BRIDGE = False

from sensor_msgs.msg import PointCloud2, Image, Imu


class ROSLiveListener:
    """
    Escucha tópicos ROS en vivo y detecta sensores disponibles.
    
    Similar a MessageLoader pero se conecta al ROS master en tiempo real,
    detectando tópicos que se generan dinámicamente (como /velodyne_points_interpolated).
    
    Características:
    - Detección automática de PointCloud2, Image, Imu
    - Caché de últimos mensajes
    - Thread-safe
    - Compatible con topics que se crean/destruyen dinámicamente
    """
    
    def __init__(self, cache_size: int = 500):
        """
        Inicializa el escucha de ROS en vivo.
        
        Args:
            cache_size: Cantidad de últimos frames a mantener en caché para navegación
        """
        self.cache_size = cache_size
        self.frame_history = OrderedDict()  # Historial de frames para navegación
        self.current_frame_index = -1  # Índice actual en el historial
        self.lock = threading.Lock()
        
        # Datos actuales
        self.current_data = {
            'timestamp': None,
            'pointclouds': {},
            'images': {},
            'imu': None,
            'available_sensors': set(),
        }
        
        # Información de tópicos
        self.pointcloud_topics = {}  # {topic: subscriber}
        self.image_topics = {}
        self.imu_topics = {}
        
        self.last_scan_time = 0
        self.scan_interval = 2.0  # Escanear cada 2 segundos
        
        # Bridge para imágenes
        if HAS_CV_BRIDGE:
            self.bridge = CvBridge()
        
        print("✅ ROSLiveListener inicializado (buffer de navegación: {} frames)".format(cache_size))
    
    def scan_and_subscribe_topics(self):
        """Escanea tópicos disponibles y se suscribe a nuevos."""
        current_time = time.time()
        if current_time - self.last_scan_time < self.scan_interval:
            return
        
        self.last_scan_time = current_time
        
        try:
            # Obtener lista de tópicos y tipos
            master = rospy.get_master()
            _, _, topic_types = master.getPublishedTopics('/')

            # Construir sets de tópicos actuales para detectar eliminaciones
            current_pointcloud_topics = set()
            current_image_topics = set()
            current_imu_topics = set()

            # Detectar nuevos tópicos y marcar existentes
            for topic, msg_type in topic_types:
                if 'PointCloud2' in msg_type:
                    current_pointcloud_topics.add(topic)
                    if topic not in self.pointcloud_topics:
                        print(f"  ✅ Detectado nuevo PointCloud2: {topic}")
                        sub = rospy.Subscriber(
                            topic,
                            PointCloud2,
                            lambda msg, t=topic: self._on_pointcloud(msg, t),
                            queue_size=1
                        )
                        self.pointcloud_topics[topic] = sub

                elif 'Disparity' in msg_type or 'disparity' in msg_type.lower():
                    # DisparityImage topics: subscribe and handle as disparity
                    current_image_topics.add(topic)
                    if topic not in self.image_topics:
                        print(f"  ✅ Detectado nuevo DisparityImage: {topic}")
                        try:
                            from stereo_msgs.msg import DisparityImage
                            sub = rospy.Subscriber(
                                topic,
                                DisparityImage,
                                lambda msg, t=topic: self._on_disparity(msg, t),
                                queue_size=1
                            )
                            self.image_topics[topic] = sub
                        except Exception as e:
                            print(f"Error suscribiendo DisparityImage {topic}: {e}")
                elif 'Image' in msg_type:
                    current_image_topics.add(topic)
                    if topic not in self.image_topics:
                        print(f"  ✅ Detectada nueva Image: {topic}")
                        sub = rospy.Subscriber(
                            topic,
                            Image,
                            lambda msg, t=topic: self._on_image(msg, t),
                            queue_size=1
                        )
                        self.image_topics[topic] = sub

                elif 'Imu' in msg_type:
                    current_imu_topics.add(topic)
                    if topic not in self.imu_topics:
                        print(f"  ✅ Detectado nuevo IMU: {topic}")
                        sub = rospy.Subscriber(
                            topic,
                            Imu,
                            self._on_imu,
                            queue_size=1
                        )
                        self.imu_topics[topic] = sub

            # Detectar tópicos que desaparecieron y desuscribir
            removed_pc = set(self.pointcloud_topics.keys()) - current_pointcloud_topics
            for topic in removed_pc:
                try:
                    sub = self.pointcloud_topics.pop(topic)
                    sub.unregister()
                    print(f"  ⚠️ PointCloud2 desaparecido, desuscribiendo: {topic}")
                    if topic in self.current_data['pointclouds']:
                        del self.current_data['pointclouds'][topic]
                except Exception as e:
                    print(f"Error desuscribiendo {topic}: {e}")

            removed_img = set(self.image_topics.keys()) - current_image_topics
            for topic in removed_img:
                try:
                    sub = self.image_topics.pop(topic)
                    sub.unregister()
                    print(f"  ⚠️ Image topic desaparecido, desuscribiendo: {topic}")
                    if topic in self.current_data['images']:
                        del self.current_data['images'][topic]
                except Exception as e:
                    print(f"Error desuscribiendo imagen {topic}: {e}")

            removed_imu = set(self.imu_topics.keys()) - current_imu_topics
            for topic in removed_imu:
                try:
                    sub = self.imu_topics.pop(topic)
                    sub.unregister()
                    print(f"  ⚠️ IMU topic desaparecido, desuscribiendo: {topic}")
                    if self.current_data.get('imu') is not None:
                        self.current_data['imu'] = None
                except Exception as e:
                    print(f"Error desuscribiendo imu {topic}: {e}")

        except Exception as e:
            # Si ocurre un error con master (p.ej. roscore reiniciado), limpiar estructuras y reintentar
            print(f"Error escaneando tópicos (master): {e}")
            try:
                # Intentar limpiar suscriptores existentes para forzar re-scan posterior
                for topic, sub in list(self.pointcloud_topics.items()):
                    try:
                        sub.unregister()
                    except Exception:
                        pass
                self.pointcloud_topics.clear()
                for topic, sub in list(self.image_topics.items()):
                    try:
                        sub.unregister()
                    except Exception:
                        pass
                self.image_topics.clear()
                for topic, sub in list(self.imu_topics.items()):
                    try:
                        sub.unregister()
                    except Exception:
                        pass
                self.imu_topics.clear()
            except Exception:
                pass
    
    def _on_pointcloud(self, msg: PointCloud2, topic: str):
        """Callback para PointCloud2."""
        try:
            # Convertir PointCloud2 a numpy usando frombuffer (vectorizado, sin loops)
            if not HAS_PC2:
                return

            field_map = {f.name: f for f in msg.fields}
            has_rgb = 'rgb' in field_map or 'rgba' in field_map
            rgb_field_name = 'rgb' if 'rgb' in field_map else ('rgba' if 'rgba' in field_map else None)

            raw = np.frombuffer(msg.data, dtype=np.uint8)
            point_step = msg.point_step
            n_points = msg.width * msg.height

            if n_points == 0:
                return

            raw = raw.reshape(n_points, point_step)

            x_off = field_map['x'].offset
            y_off = field_map['y'].offset
            z_off = field_map['z'].offset

            x = raw[:, x_off:x_off+4].view(np.float32).reshape(-1)
            y = raw[:, y_off:y_off+4].view(np.float32).reshape(-1)
            z = raw[:, z_off:z_off+4].view(np.float32).reshape(-1)

            valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)

            if has_rgb and rgb_field_name:
                rgb_off = field_map[rgb_field_name].offset
                rgb_raw = raw[:, rgb_off:rgb_off+4].view(np.uint32).reshape(-1)
                r = ((rgb_raw >> 16) & 0xFF).astype(np.float32) / 255.0
                g = ((rgb_raw >> 8)  & 0xFF).astype(np.float32) / 255.0
                b = ( rgb_raw        & 0xFF).astype(np.float32) / 255.0
                pc_array = np.stack([x, y, z, r, g, b], axis=1)[valid].astype(np.float32)
            else:
                pc_array = np.stack([x, y, z], axis=1)[valid].astype(np.float32)
            
            if len(pc_array) > 0:
                with self.lock:
                    self.current_data['pointclouds'][topic] = pc_array
                    self.current_data['timestamp'] = msg.header.stamp.to_sec()
                    self.current_data['available_sensors'].add('pointcloud')
                    
                    # Guardar frame en historial
                    frame_copy = {
                        'timestamp': self.current_data['timestamp'],
                        'pointclouds': self.current_data['pointclouds'].copy(),
                        'images': self.current_data['images'].copy(),
                        'imu': self.current_data['imu'],
                        'available_sensors': self.current_data['available_sensors'].copy(),
                    }
                    
                    # Agregar al historial con índice
                    frame_idx = len(self.frame_history)
                    self.frame_history[frame_idx] = frame_copy
                    self.current_frame_index = frame_idx
                    
                    # Mantener tamaño máximo del buffer
                    if len(self.frame_history) > self.cache_size:
                        oldest_key = next(iter(self.frame_history))
                        del self.frame_history[oldest_key]
        
        except Exception as e:
            print(f"Error procesando PointCloud2 de {topic}: {e}")
    
    def _on_image(self, msg: Image, topic: str):
        """Callback para Image."""
        try:
            if not HAS_CV_BRIDGE:
                return
            
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            
            with self.lock:
                self.current_data['images'][topic] = cv_image
                self.current_data['timestamp'] = msg.header.stamp.to_sec()
                self.current_data['available_sensors'].add('image')
        
        except Exception as e:
            print(f"Error procesando Image de {topic}: {e}")

    def _on_disparity(self, msg, topic: str):
        """Callback para DisparityImage: convierte a numpy (float32) y guarda en current_data['images']"""
        try:
            if not HAS_CV_BRIDGE:
                return
            # DisparityImage.msg has .image which is a sensor_msgs/Image
            # Use CvBridge to convert it; keep float32 precision
            disp_cv = self.bridge.imgmsg_to_cv2(msg.image, desired_encoding='passthrough')
            disp_arr = np.array(disp_cv, dtype=np.float32)
            with self.lock:
                self.current_data['images'][topic] = disp_arr
                self.current_data['timestamp'] = msg.header.stamp.to_sec()
                self.current_data['available_sensors'].add('image')
        except Exception as e:
            print(f"Error en _on_disparity({topic}): {e}")
    
    def _on_imu(self, msg: Imu):
        """Callback para IMU."""
        try:
            imu_data = {
                'accel': {
                    'x': msg.linear_acceleration.x,
                    'y': msg.linear_acceleration.y,
                    'z': msg.linear_acceleration.z,
                },
                'angular_vel': {
                    'x': msg.angular_velocity.x,
                    'y': msg.angular_velocity.y,
                    'z': msg.angular_velocity.z,
                }
            }
            
            with self.lock:
                self.current_data['imu'] = imu_data
                self.current_data['timestamp'] = msg.header.stamp.to_sec()
                self.current_data['available_sensors'].add('imu')
        
        except Exception as e:
            print(f"Error procesando IMU: {e}")
    
    def get_current_frame_data(self) -> Dict[str, Any]:
        """
        Obtiene los datos actuales de los sensores.
        
        Returns:
            Dict con estructura idéntica a MessageLoader:
            - 'timestamp': float
            - 'pointclouds': Dict[topic -> array]
            - 'images': Dict[topic -> array]
            - 'imu': dict o None
            - 'available_sensors': set
        """
        # Escanear nuevos tópicos
        self.scan_and_subscribe_topics()
        
        # Retornar copia de datos actuales
        with self.lock:
            data = {
                'timestamp': self.current_data['timestamp'],
                'pointclouds': self.current_data['pointclouds'].copy(),
                'images': self.current_data['images'].copy(),
                'imu': self.current_data['imu'],
                'available_sensors': self.current_data['available_sensors'].copy(),
            }
        
        # Para backward compatibility, guardar primer pointcloud
        if data['pointclouds']:
            first_topic = list(data['pointclouds'].keys())[0]
            data['pointcloud'] = data['pointclouds'][first_topic]
        else:
            data['pointcloud'] = None
        
        return data
    
    def get_available_lidar_topics(self) -> List[str]:
        """Retorna lista de tópicos PointCloud2 disponibles."""
        return list(self.pointcloud_topics.keys())
    
    def get_available_image_topics(self) -> List[str]:
        """Retorna lista de tópicos Image disponibles."""
        return list(self.image_topics.keys())
    
    def get_total_frames(self) -> int:
        """Retorna cantidad total de frames en el historial."""
        with self.lock:
            return len(self.frame_history)
    
    def get_current_frame_index(self) -> int:
        """Retorna el índice del frame actual en el historial."""
        with self.lock:
            return self.current_frame_index
    
    def navigate_to_frame(self, frame_index: int) -> bool:
        """
        Navega a un frame específico en el historial.
        
        Args:
            frame_index: Índice del frame (0 a total_frames-1)
        
        Returns:
            True si la navegación fue exitosa, False si índice inválido
        """
        with self.lock:
            if frame_index not in self.frame_history:
                return False
            
            self.current_frame_index = frame_index
            # Actualizar current_data con el frame seleccionado
            frame_data = self.frame_history[frame_index]
            self.current_data = frame_data.copy()
            return True
    
    def get_frame(self, frame_index: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene un frame específico del historial.
        
        Args:
            frame_index: Índice del frame
        
        Returns:
            Dict con datos del frame, o None si índice inválido
        """
        with self.lock:
            if frame_index not in self.frame_history:
                return None
            
            frame = self.frame_history[frame_index]
            # Retornar copia con backward compatibility
            data = {
                'timestamp': frame['timestamp'],
                'pointclouds': frame['pointclouds'].copy(),
                'images': frame['images'].copy(),
                'imu': frame['imu'],
                'available_sensors': frame['available_sensors'].copy(),
            }
            
            if data['pointclouds']:
                first_topic = list(data['pointclouds'].keys())[0]
                data['pointcloud'] = data['pointclouds'][first_topic]
            else:
                data['pointcloud'] = None
            
            return data
    
    def advance_frame(self, steps: int = 1) -> bool:
        """
        Avanza en el historial N frames.
        
        Args:
            steps: Cantidad de frames a avanzar (puede ser negativo para retroceder)
        
        Returns:
            True si fue posible, False si llegó al límite
        """
        with self.lock:
            if not self.frame_history:
                print(f"[ADVANCE] Frame history vacío")
                return False
            
            frame_indices = list(self.frame_history.keys())
            current_pos = None
            
            # Encontrar posición actual en la lista de índices
            try:
                current_pos = frame_indices.index(self.current_frame_index)
            except ValueError:
                current_pos = len(frame_indices) - 1
            
            new_pos = current_pos + steps
            
            # Validar límites
            if new_pos < 0:
                new_pos = 0
            elif new_pos >= len(frame_indices):
                new_pos = len(frame_indices) - 1
            
            new_index = frame_indices[new_pos]
            self.current_frame_index = new_index
            frame_data = self.frame_history[new_index]
            self.current_data = frame_data.copy()
            
            moved = new_pos != current_pos
            print(f"[ADVANCE] Pos: {current_pos} → {new_pos}, Frame: {frame_indices[current_pos] if current_pos < len(frame_indices) else '?'} → {new_index}, moved={moved}")
            
            return moved