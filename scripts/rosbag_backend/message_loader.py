#!/usr/bin/env python3
"""
Fase 4: MessageLoader
Carga y convierte datos reales de sensores a formato renderizable.

Conversiones soportadas:
- PointCloud2 → numpy (n_points, 3)
- Image → numpy (H, W, C)
- Imu → dict {accel, angular_vel}
"""

import numpy as np
import rosbag
from typing import Dict, Optional, Any, Set, Tuple
from collections import OrderedDict
from pathlib import Path
import genpy

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

from .bag_indexer import BagIndexer
from .frame_navigator import FrameNavigator


class MessageLoader:
    """
    Carga y convierte datos de sensores a formato renderizable.
    
    Características:
    - Caché inteligente de mensajes recientes (LRU)
    - Conversiones automáticas de tipos ROS a numpy
    - Integración con FrameNavigator para posición actual
    - Manejo robusto de tópicos faltantes
    """

    def __init__(self, indexer: BagIndexer, nav: FrameNavigator, 
                 cache_size: int = 20):
        """
        Inicializa el cargador de mensajes.

        Args:
            indexer (BagIndexer): Indexador de la bolsa rosbag
            nav (FrameNavigator): Navegador para obtener posición actual
            cache_size (int): Cantidad máxima de mensajes a cachear (default: 20)
        
        Raises:
            ValueError: Si cache_size < 1
        """
        if cache_size < 1:
            raise ValueError(f"cache_size debe ser >= 1, recibido: {cache_size}")

        self.indexer = indexer
        self.nav = nav
        self.cache_size = cache_size
        
        # Cache LRU: {frame_index: {topic: message}}
        self.cache: OrderedDict[int, Dict[str, Any]] = OrderedDict()
        
        # Información de sensores disponibles
        self._sensor_topics = self._identify_sensor_topics()
        
        print(f"✓ MessageLoader inicializado")
        print(f"  - Cache size: {cache_size}")
        print(f"  - Tópicos de sensores: {len(self._sensor_topics)}")
        if self._sensor_topics:
            for sensor_type, topics in self._sensor_topics.items():
                print(f"    • {sensor_type}: {len(topics)} tópico(s)")

    def _identify_sensor_topics(self) -> Dict[str, list]:
        """
        Identifica y categoriza tópicos de sensores disponibles.
        
        Returns:
            Dict[str, list]: Mapa de tipo_sensor -> [lista de tópicos]
        """
        sensor_topics = {
            'pointcloud': [],
            'image': [],
            'imu': [],
            'other': []
        }

        all_topics = self.indexer.topics
        
        for topic in all_topics:
            msg_type = self.indexer._topics_info.get(topic, {}).get('type', '')
            
            if 'PointCloud2' in msg_type:
                sensor_topics['pointcloud'].append(topic)
            elif 'DisparityImage' in msg_type or 'disparity' in msg_type.lower():
                # Aceptar tópicos de Disparity (se tratarán como imágenes para visualización)
                sensor_topics['image'].append(topic)
            elif msg_type == 'sensor_msgs/Image' or 'Image' in msg_type:
                # sensor_msgs/Image u otros tipos que contienen Image
                sensor_topics['image'].append(topic)
            elif 'Imu' in msg_type:
                sensor_topics['imu'].append(topic)
            else:
                sensor_topics['other'].append(topic)

        return {k: v for k, v in sensor_topics.items() if v}

    def _ensure_frame_cached(self, frame_index: int) -> None:
        """
        Asegura que un frame está cacheado.
        
        Estrategia optimizada: En lugar de iterar por índice,
        usa timestamps del FrameNavigator para leer ventana temporal.
        
        Args:
            frame_index (int): Índice del frame a cachear
        """
        # Si ya existe, mover al final (LRU)
        if frame_index in self.cache:
            self.cache.move_to_end(frame_index)
            return

        # Si cache está lleno, remover elementos antiguos
        while len(self.cache) >= self.cache_size:
            self.cache.popitem(last=False)  # Remover primero (más antiguo)

        # Usar ventana temporal del indexer
        try:
            current_pos = self.nav.get_current_position()
            
            # Obtener timestamp del frame actual usando el indexer
            # Si no hay timestamps directos, crear entrada básica
            self.cache[frame_index] = {'_metadata': {
                'frame_index': frame_index,
                'timestamp': current_pos.timestamp,
            }}
            
        except Exception as e:
            print(f"⚠ Error cacheando frame {frame_index}: {e}")
            if frame_index not in self.cache:
                self.cache[frame_index] = {}

    def _get_message_for_topic(self, topic: str, frame_index: int) -> Optional[Any]:
        """
        Obtiene el mensaje de un tópico para un frame específico.
        
        Usa búsqueda temporal eficiente en lugar de iteración.
        
        Args:
            topic (str): Nombre del tópico
            frame_index (int): Índice del frame
        
        Returns:
            Mensaje ROS o None si no existe
        """
        if topic not in self.indexer.topics:
            return None

        # Obtener timestamp del frame actual
        pos = self.nav.get_current_position()
        if pos.timestamp is None or pos.timestamp == 0:
            return None

        # Buscar el mensaje más cercano en este tópico usando el indexer
        try:
            # Usar el método de búsqueda eficiente del indexer
            found_topic, entry = self.indexer.get_closest_message_in_topics(
                [topic], pos.timestamp
            )
            
            if found_topic is None or entry is None:
                return None

            # Cargar el mensaje desde el bag usando genpy.Time
            with rosbag.Bag(str(self.indexer.bag_path), 'r') as bag:
                # bag_timestamp es float, convertir a genpy.Time
                # Crear ventana temporal pequeña (±1ms)
                start_time = genpy.Time.from_sec(entry.bag_timestamp - 0.001)
                end_time = genpy.Time.from_sec(entry.bag_timestamp + 0.001)
                
                for msg_topic, msg, ts in bag.read_messages(
                    topics=[topic],
                    start_time=start_time,
                    end_time=end_time
                ):
                    return msg
            
            return None

        except Exception as e:
            print(f"⚠ Error obteniendo mensaje de {topic}: {e}")
            return None

    @staticmethod
    @staticmethod
    def _pointcloud2_to_array(msg) -> Optional[np.ndarray]:
        """
        Convierte PointCloud2 a array numpy usando np.frombuffer (vectorizado).

        Returns:
            np.ndarray (n_points, 6) con XYZRGB si el campo rgb existe,
            np.ndarray (n_points, 3) con solo XYZ si no hay color,
            o None si falla.
        """
        if not HAS_PC2:
            return None

        try:
            # Leer campos disponibles del mensaje
            field_map = {f.name: f for f in msg.fields}
            has_rgb = 'rgb' in field_map or 'rgba' in field_map
            rgb_field_name = 'rgb' if 'rgb' in field_map else ('rgba' if 'rgba' in field_map else None)

            # Leer buffer crudo del mensaje de forma vectorizada
            raw = np.frombuffer(msg.data, dtype=np.uint8)
            point_step = msg.point_step
            n_points = msg.width * msg.height

            if n_points == 0:
                return np.empty((0, 6 if has_rgb else 3), dtype=np.float32)

            # Reshape a (n_points, point_step)
            raw = raw.reshape(n_points, point_step)

            # Extraer XYZ (siempre float32, offsets estándar: x=0, y=4, z=8)
            x_off = field_map['x'].offset
            y_off = field_map['y'].offset
            z_off = field_map['z'].offset

            x = raw[:, x_off:x_off+4].view(np.float32).reshape(-1)
            y = raw[:, y_off:y_off+4].view(np.float32).reshape(-1)
            z = raw[:, z_off:z_off+4].view(np.float32).reshape(-1)

            # Filtrar NaN
            valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)

            if has_rgb and rgb_field_name:
                rgb_off = field_map[rgb_field_name].offset
                # rgb empaquetado como float32 → leer como uint32
                rgb_raw = raw[:, rgb_off:rgb_off+4].view(np.uint32).reshape(-1)
                r = ((rgb_raw >> 16) & 0xFF).astype(np.float32) / 255.0
                g = ((rgb_raw >> 8)  & 0xFF).astype(np.float32) / 255.0
                b = ( rgb_raw        & 0xFF).astype(np.float32) / 255.0
                result = np.stack([x, y, z, r, g, b], axis=1)[valid]
            else:
                result = np.stack([x, y, z], axis=1)[valid]

            return result.astype(np.float32)

        except Exception as e:
            print(f"⚠ Error convirtiendo PointCloud2: {e}")
            return None

    @staticmethod
    def _image_to_array(msg) -> Optional[np.ndarray]:
        """
        Convierte Image msg a array numpy.
        
        Args:
            msg: sensor_msgs.Image
        
        Returns:
            np.ndarray de forma (H, W, C) tipo uint8,
            o None si falla la conversión
        """
        if not HAS_CV_BRIDGE:
            return None

        try:
            bridge = CvBridge()

            # sensor_msgs/Image has 'encoding'; DisparityImage has 'image' field
            if hasattr(msg, 'encoding'):
                cv_image = bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
                return np.array(cv_image, dtype=np.uint8)

            # Support stereo_msgs/DisparityImage: convert inner image to float32
            if hasattr(msg, 'image'):
                try:
                    disp = bridge.imgmsg_to_cv2(msg.image, desired_encoding='passthrough')
                    return np.array(disp, dtype=np.float32)
                except Exception:
                    # Fallback: try converting msg directly
                    cv_image = bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
                    return np.array(cv_image, dtype=np.uint8)

            print(f"⚠ Mensaje no es sensor_msgs/Image ni DisparityImage")
            return None

        except Exception as e:
            print(f"⚠ Error convirtiendo Image/Disparity: {e}")
            return None

    @staticmethod
    def _imu_to_dict(msg) -> Optional[Dict]:
        """
        Convierte Imu msg a dict.
        
        Args:
            msg: sensor_msgs.Imu
        
        Returns:
            Dict con claves 'accel', 'angular_vel', 'timestamp'
        """
        try:
            return {
                'accel': np.array([
                    msg.linear_acceleration.x,
                    msg.linear_acceleration.y,
                    msg.linear_acceleration.z
                ], dtype=np.float32),
                'angular_vel': np.array([
                    msg.angular_velocity.x,
                    msg.angular_velocity.y,
                    msg.angular_velocity.z
                ], dtype=np.float32),
                'timestamp': msg.header.stamp.to_sec()
            }
        except Exception as e:
            print(f"⚠ Error convirtiendo IMU: {e}")
            return None

    def load_pointcloud(self, topic: str) -> Optional[np.ndarray]:
        """
        Carga PointCloud2 del frame actual.
        
        Args:
            topic (str): Nombre del tópico (ej: '/velodyne_points')
        
        Returns:
            Array numpy de forma (n_points, 3) con coordenadas XYZ,
            o None si no está disponible
        """
        if not HAS_PC2:
            print("⚠ sensor_msgs.point_cloud2 no disponible")
            return None

        if topic not in self.indexer.topics:
            return None

        frame_idx = self.nav.get_current_position().global_index
        msg = self._get_message_for_topic(topic, frame_idx)
        
        if msg is None:
            return None
        
        result = self._pointcloud2_to_array(msg)
        if result is not None:
            return result
        
        return None

    def load_image(self, topic: str) -> Optional[np.ndarray]:
        """
        Carga Image del frame actual.
        
        Args:
            topic (str): Nombre del tópico
                        (ej: '/zed/zed_node/left/image_rect_color')
        
        Returns:
            Array numpy de forma (H, W, C) tipo uint8,
            o None si no está disponible
        """
        if not HAS_CV_BRIDGE:
            print("⚠ cv_bridge no disponible")
            return None

        frame_idx = self.nav.get_current_position().global_index
        msg = self._get_message_for_topic(topic, frame_idx)
        
        if msg is None:
            return None
        
        return self._image_to_array(msg)

    def load_imu(self, topic: str) -> Optional[Dict]:
        """
        Carga datos IMU del frame actual.
        
        Args:
            topic (str): Nombre del tópico (ej: '/imu/data')
        
        Returns:
            Dict con claves 'accel', 'angular_vel', 'timestamp',
            o None si no está disponible
        """
        frame_idx = self.nav.get_current_position().global_index
        msg = self._get_message_for_topic(topic, frame_idx)
        
        if msg is None:
            return None
        
        return self._imu_to_dict(msg)

    def get_current_frame_data(self) -> Dict[str, Any]:
        """
        Obtiene todos los datos disponibles del frame actual.
        
        Combina todos los sensores disponibles en un diccionario
        listo para renderizar.
        
        Returns:
            Dict con claves:
            - 'position': FramePosition con info de navegación
            - 'pointcloud': np.ndarray (n, 3) si PointCloud2 disponible (first one for backward compat)
            - 'pointclouds': Dict[topic -> np.ndarray] para cada pointcloud disponible
            - 'images': Dict[topic -> np.ndarray] para cada imagen
            - 'imu': Dict con accel y angular_vel si IMU disponible
            - 'timestamp': float con timestamp del frame
            - 'available_sensors': Set de tipos de sensor disponibles
        """
        pos = self.nav.get_current_position()
        frame_idx = pos.global_index
        
        data = {
            'position': pos,
            'timestamp': pos.timestamp,
            'available_sensors': set(),
            'pointcloud': None,
            'pointclouds': {},  # Nuevo: dict con todos los pointclouds
            'images': {},
            'imu': None,
        }

        # Cargar PointClouds si disponibles (ahora retorna todos)
        for topic in self._sensor_topics.get('pointcloud', []):
            pc = self.load_pointcloud(topic)
            if pc is not None:
                data['pointclouds'][topic] = pc
                # Para backward compatibility, guardar el primero en 'pointcloud'
                if data['pointcloud'] is None:
                    data['pointcloud'] = pc
                data['available_sensors'].add('pointcloud')

        # Cargar imágenes si disponibles
        for topic in self._sensor_topics.get('image', []):
            img = self.load_image(topic)
            if img is not None:
                data['images'][topic] = img
                data['available_sensors'].add('image')

        # Cargar IMU si disponible
        for topic in self._sensor_topics.get('imu', []):
            imu = self.load_imu(topic)
            if imu is not None:
                data['imu'] = imu
                data['available_sensors'].add('imu')
                break  # Usar el primero encontrado

        return data

    def get_sensor_topics(self) -> Dict[str, list]:
        """
        Obtiene lista de tópicos de sensores identificados.
        
        Returns:
            Dict[sensor_type -> [topics]]
        """
        return self._sensor_topics.copy()

    def clear_cache(self) -> None:
        """
        Limpia el caché de mensajes para liberar memoria.
        """
        self.cache.clear()
        print("✓ Cache limpiado")

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Obtiene información del estado del caché.
        
        Returns:
            Dict con info de cache
        """
        return {
            'size': len(self.cache),
            'max_size': self.cache_size,
            'memory_usage_mb': sum(
                sum(len(str(v)) for v in msgs.values()) 
                for msgs in self.cache.values()
            ) / (1024 * 1024),
        }