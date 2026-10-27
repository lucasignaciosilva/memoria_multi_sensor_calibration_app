#!/usr/bin/env python3
"""
Indexador de rosbag para navegación eficiente sin cargar mensajes completos en memoria.

Estrategia:
1. Usar `rosbag info` (binario, ultra-rápido) para metadatos
2. Bajo demanda: iterar mensajes solo si se solicitan timestamps exactos
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import rosbag
import subprocess
import yaml
import numpy as np


@dataclass
class BagIndexEntry:
    """Entrada de índice para un mensaje en el rosbag."""
    
    topic: str
    bag_timestamp: float  # timestamp del rosbag (cuando se escribió el mensaje)
    msg_type: str  # tipo de mensaje (e.g., 'sensor_msgs/PointCloud2')
    frame_id: Optional[str] = None  # frame_id del header, si existe
    header_stamp: Optional[float] = None  # timestamp del header.stamp, si existe
    msg_index: int = 0  # índice secuencial del mensaje en el bag
    topic_index: int = 0  # índice dentro del topic
    
    def __repr__(self):
        return (
            f"BagIndexEntry(topic={self.topic!r}, "
            f"bag_ts={self.bag_timestamp:.3f}, "
            f"frame_id={self.frame_id!r}, "
            f"type={self.msg_type})"
        )


class BagIndexer:
    """Construye y gestiona un índice de metadatos de un rosbag."""
    
    def __init__(self, bag_path: str, lazy_index: bool = True):
        """
        Inicializa el indexador con la ruta de un rosbag.
        
        Args:
            bag_path: ruta al archivo .bag
            lazy_index: si True, solo indexa topics rápidamente sin iterar mensajes.
                       Los timestamps se cargan bajo demanda.
            
        Raises:
            FileNotFoundError: si el archivo no existe
            RuntimeError: si el bag está corrupto o no se puede abrir
        """
        self.bag_path = Path(bag_path)
        self.lazy_index = lazy_index
        
        if not self.bag_path.exists():
            raise FileNotFoundError(f"Rosbag no encontrado: {bag_path}")
        
        self._entries: List[BagIndexEntry] = []
        self._entries_by_topic: Dict[str, List[BagIndexEntry]] = {}
        self._topics_info: Dict[str, Dict] = {}
        self._full_index_loaded = False
        self._info = {}
        
        # Intentar indexar (forma rápida inicialmente)
        try:
            self._build_index_fast()
            if not lazy_index:
                self._build_full_index()
        except Exception as e:
            raise RuntimeError(f"Error al indexar rosbag {bag_path}: {e}")
    def _build_index_fast(self):
        """Construye índice rápido usando binario 'rosbag info' (ULTRA-RÁPIDO)."""
        try:
            # Usar el comando 'rosbag info -y' que es compilado en C++ y MUCHO más rápido
            result = subprocess.run(
                ['rosbag', 'info', '-y', str(self.bag_path)],
                capture_output=True,
                text=True,
                timeout=60  # Aumentado a 60s para bags grandes
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"rosbag info error: {result.stderr}")
            
            # Parsear YAML directamente
            data = yaml.safe_load(result.stdout)
            
            # Extraer información general
            self._info = {
                'duration': data.get('duration', 0.0),
                'start_time': data.get('start', 0.0),
                'end_time': data.get('end', 0.0),
                'message_count': data.get('messages', 0),
            }
            
            # Extraer topics desde YAML
            if 'topics' in data:
                for topic_entry in data['topics']:
                    topic = topic_entry['topic']
                    msg_type = topic_entry['type']
                    msg_count = topic_entry['messages']
                    
                    self._topics_info[topic] = {
                        'type': msg_type,
                        'message_count': msg_count,
                        'connections': 1,
                    }
                    self._entries_by_topic[topic] = []
            
            # Validar que se extrajo información
            if not self._topics_info:
                raise RuntimeError("No se pudieron extraer topics de rosbag info")
        
        except subprocess.TimeoutExpired:
            raise RuntimeError("rosbag info timeout (bag muy grande)")
        except FileNotFoundError:
            # Si rosbag info no existe, usar método alternativo (más lento)
            self._build_index_fallback()
        except Exception as e:
            raise RuntimeError(f"Error leyendo metadata del rosbag: {e}")
    
    def _build_index_fallback(self):
        """Fallback a iteración si rosbag info no está disponible."""
        try:
            with rosbag.Bag(str(self.bag_path), 'r') as bag:
                start_time = bag.get_start_time()
                end_time = bag.get_end_time()
                
                self._info = {
                    'duration': end_time - start_time,
                    'start_time': start_time,
                    'end_time': end_time,
                    'message_count': bag.get_message_count(),
                }
                
                # Leer solo primer mensaje de cada topic
                topics_seen = set()
                for topic, msg, timestamp in bag.read_messages():
                    if topic not in topics_seen:
                        topics_seen.add(topic)
                        msg_type = msg.__class__.__module__.replace('sensor_msgs.msg._', '').replace('velodyne_msgs.msg._', '') + '/' + msg.__class__.__name__
                        msg_count = bag.get_message_count(topic)
                        
                        self._topics_info[topic] = {
                            'type': msg_type,
                            'message_count': msg_count,
                            'connections': 1,
                        }
                        self._entries_by_topic[topic] = []
                    
                    # Si ya tenemos todos los topics, salir
                    if len(topics_seen) == len(set(t for t, _, _ in bag.read_messages() if t)):
                        break
        
        except Exception as e:
            raise RuntimeError(f"Error en fallback: {e}")
    
    def _build_full_index(self):
        """Itera sobre todos los mensajes para construir índice completo.
        
        ADVERTENCIA: Esto puede ser muy lento para bags grandes.
        Se usa bajo demanda cuando se necesitan timestamps exactos.
        """
        if self._full_index_loaded:
            return
        
        self._entries.clear()
        for topic in self._entries_by_topic:
            self._entries_by_topic[topic].clear()
        
        msg_index = 0
        topic_indices: Dict[str, int] = {t: 0 for t in self._topics_info.keys()}
        
        try:
            with rosbag.Bag(str(self.bag_path), 'r') as bag:
                # Iterar sobre todos los mensajes
                for topic, msg, timestamp in bag.read_messages():
                    # Extraer header info si existe
                    frame_id = None
                    header_stamp = None
                    
                    try:
                        # Intentar acceder al header del mensaje
                        if hasattr(msg, 'header'):
                            frame_id = msg.header.frame_id if hasattr(msg.header, 'frame_id') else None
                            if hasattr(msg.header, 'stamp'):
                                header_stamp = msg.header.stamp.to_sec()
                    except Exception:
                        # Si no se puede extraer header, continuar sin él
                        pass
                    
                    # Crear entrada de índice
                    entry = BagIndexEntry(
                        topic=topic,
                        bag_timestamp=timestamp.to_sec(),
                        msg_type=self._topics_info[topic]['type'],
                        frame_id=frame_id,
                        header_stamp=header_stamp,
                        msg_index=msg_index,
                        topic_index=topic_indices[topic],
                    )
                    
                    self._entries.append(entry)
                    self._entries_by_topic[topic].append(entry)
                    topic_indices[topic] += 1
                    msg_index += 1
        
        except Exception as e:
            raise RuntimeError(f"Error leyendo rosbag: {e}")
        
        self._full_index_loaded = True
    
    @property
    def topics(self) -> List[str]:
        """Retorna lista de topics en el bag."""
        return sorted(self._entries_by_topic.keys())
    
    def topic_info(self, topic: str) -> Optional[Dict]:
        """Retorna información del topic (tipo, cantidad de mensajes)."""
        return self._topics_info.get(topic)
    
    def messages_for_topic(self, topic: str) -> List[BagIndexEntry]:
        """Retorna todas las entradas de índice para un topic."""
        if not self._full_index_loaded:
            self._build_full_index()
        return self._entries_by_topic.get(topic, [])
    
    def get_entry(self, index: int) -> Optional[BagIndexEntry]:
        """Retorna entrada de índice por índice global."""
        if 0 <= index < len(self._entries):
            return self._entries[index]
        return None
    
    def entries_in_range(self, start_ts: float, end_ts: float) -> List[BagIndexEntry]:
        """Retorna entradas de índice dentro de un rango temporal."""
        if not self._full_index_loaded:
            self._build_full_index()
        return [e for e in self._entries if start_ts <= e.bag_timestamp <= end_ts]
    
    def entries_for_topic_in_range(
        self,
        topic: str,
        start_ts: float,
        end_ts: float,
    ) -> List[BagIndexEntry]:
        """Retorna entradas de un topic dentro de un rango temporal."""
        if not self._full_index_loaded:
            self._build_full_index()
        entries = self._entries_by_topic.get(topic, [])
        return [e for e in entries if start_ts <= e.bag_timestamp <= end_ts]
    
    def get_summary(self) -> str:
        """Retorna un resumen textual del índice."""
        lines = [
            f"Rosbag: {self.bag_path.name}",
            f"Duración: {self._info['duration']:.2f} s",
            f"Rango temporal: {self._info['start_time']:.2f} - {self._info['end_time']:.2f}",
            f"Total de mensajes: {self.total_messages}",
        ]
        
        if self._full_index_loaded:
            lines.append("")
            lines.append("Topics:")
            
            for topic in self.topics():
                entries = self._entries_by_topic[topic]
                info = self._topics_info[topic]
                lines.append(
                    f"  {topic}: "
                    f"tipo={info['type']}, "
                    f"mensajes={len(entries)}"
                )
        else:
            lines.append("")
            lines.append("Topics (sin indexación completa):")
            
            for topic in self.topics():
                info = self._topics_info[topic]
                lines.append(
                    f"  {topic}: "
                    f"tipo={info['type']}, "
                    f"mensajes={info['message_count']}"
                )
        
        return "\n".join(lines)
    
    @property
    def total_messages(self) -> int:
        """Total de mensajes indexados."""
        if not self._full_index_loaded:
            return self._info.get('message_count', 0)
        return len(self._entries)
    
    @property
    def message_timestamps(self) -> np.ndarray:
        """Array NumPy de todos los timestamps del bag (en orden)."""
        if not self._full_index_loaded:
            self._build_full_index()
        return np.array([e.bag_timestamp for e in self._entries])
    
    def get_closest_message_in_topics(
        self,
        topics: List[str],
        target_timestamp: float,
    ) -> Optional[Tuple[str, BagIndexEntry]]:
        """
        Busca el mensaje más cercano a un timestamp en una lista de tópicos específicos.
        
        Estrategia: Lee solo mensajes cercanos al timestamp objetivo sin cargar índice completo.
        Esto es mucho más rápido que iterar todo el bag.
        
        Args:
            topics: Lista de nombres de tópicos
            target_timestamp: Timestamp objetivo en segundos
        
        Returns:
            (topic_name, entry) del mensaje más cercano, o None si no hay
            
        Ejemplo:
            >>> indexer = BagIndexer('mi_bag.bag')  # lazy_index=True (por defecto)
            >>> topic, entry = indexer.get_closest_message_in_topics(
            ...     ["/velodyne_points", "/camera"],
            ...     1759431815.5
            ... )
        """
        best_result = None
        min_diff = float('inf')
        
        # Usar rosbag.Bag con start_time y end_time para lectura dirigida
        try:
            from rosgraph_msgs.msg import Clock
            
            with rosbag.Bag(str(self.bag_path), 'r') as bag:
                # Ventana de búsqueda: +/- 1 segundo alrededor del timestamp objetivo
                search_window = 2.0  # segundos
                start_secs = int(target_timestamp - search_window)
                start_nsecs = int((target_timestamp - search_window - start_secs) * 1e9)
                end_secs = int(target_timestamp + search_window)
                end_nsecs = int((target_timestamp + search_window - end_secs) * 1e9)
                
                # Crear timestamps ROS
                from genpy import Time
                start_time = Time(secs=start_secs, nsecs=start_nsecs)
                end_time = Time(secs=end_secs, nsecs=end_nsecs)
                
                for topic, msg, timestamp in bag.read_messages(
                    topics=topics,
                    start_time=start_time,
                    end_time=end_time
                ):
                    msg_timestamp = timestamp.to_sec()
                    diff = abs(msg_timestamp - target_timestamp)
                    
                    if diff < min_diff:
                        min_diff = diff
                        
                        # Extraer header info
                        frame_id = None
                        header_stamp = None
                        try:
                            if hasattr(msg, 'header'):
                                frame_id = getattr(msg.header, 'frame_id', None)
                                if hasattr(msg.header, 'stamp'):
                                    header_stamp = msg.header.stamp.to_sec()
                        except Exception:
                            pass
                        
                        entry = BagIndexEntry(
                            topic=topic,
                            bag_timestamp=msg_timestamp,
                            msg_type=self._topics_info.get(topic, {}).get('type', 'unknown'),
                            frame_id=frame_id,
                            header_stamp=header_stamp,
                            msg_index=0,
                            topic_index=0,
                        )
                        best_result = (topic, entry)
        
        except Exception as e:
            raise RuntimeError(f"Error en búsqueda: {e}")
        
        return best_result
    
    def get_topic_by_type(self, msg_type: str) -> Optional[str]:
        """Retorna el primer topic que tiene el tipo de mensaje especificado."""
        for topic, info in self._topics_info.items():
            if info['type'] == msg_type:
                return topic
        return None
    
    def get_topics_by_type(self, msg_type: str) -> List[str]:
        """Retorna todos los topics que tienen el tipo de mensaje especificado."""
        return [
            topic for topic, info in self._topics_info.items()
            if info['type'] == msg_type
        ]
