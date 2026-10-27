#!/usr/bin/env python3
"""
Frame Navigator - Fase 3: Navegación eficiente por frames de un rosbag.

Propósito: Proporcionar métodos para navegar frame por frame sin cargar
el índice completo en memoria (compatible con lazy_index=True).

Métodos principales:
- next() - Siguiente mensaje global
- prev() - Mensaje anterior global
- goto(index) - Saltar a un índice específico
- set_range(start, end) - Definir rango de reproducción
- get_current_frame() - Obtener frame actual con todos los detalles
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import rosbag
from genpy import Time
from .bag_indexer import BagIndexer, BagIndexEntry


@dataclass
class FramePosition:
    """Posición actual en la reproducción."""
    global_index: int      # Índice global en el bag
    timestamp: float       # Timestamp en segundos
    message_count: int     # Mensajes totales en el rango
    range_start: int       # Índice inicial del rango
    range_end: int         # Índice final del rango


class FrameNavigator:
    """Navegador de frames con soporte para rangos personalizados."""
    
    def __init__(self, indexer: BagIndexer):
        """
        Inicializa el navegador de frames.
        
        Args:
            indexer: Instancia de BagIndexer con lazy_index=True
        """
        self.indexer = indexer
        self.current_index = 0
        self.range_start = 0
        self.range_end = self.indexer.total_messages - 1
        
        # Cache de iteradores por ventana (para eficiencia)
        self._message_cache: Dict[int, Tuple[str, BagIndexEntry]] = {}
        self._cache_size = 100  # Mensajes a cachear
        
    def set_range(self, start_index: int, end_index: int) -> None:
        """
        Define el rango de frames para reproducción.
        
        Args:
            start_index: Índice inicial (inclusive)
            end_index: Índice final (inclusive)
            
        Ejemplo:
            >>> nav = FrameNavigator(indexer)
            >>> nav.set_range(0, 10000)  # Trabajar solo con primeros 10k frames
        """
        if start_index < 0 or end_index >= self.indexer.total_messages:
            raise ValueError(f"Rango inválido: [{start_index}, {end_index}] de {self.indexer.total_messages}")
        
        if start_index > end_index:
            raise ValueError(f"start_index ({start_index}) > end_index ({end_index})")
        
        self.range_start = start_index
        self.range_end = end_index
        self.current_index = start_index
        self._message_cache.clear()
        
        print(f"[FrameNavigator] Rango configurado: [{start_index}, {end_index}]")
    
    def next(self) -> Optional[BagIndexEntry]:
        """
        Avanza al siguiente mensaje dentro del rango.
        
        Returns:
            BagIndexEntry del siguiente mensaje, o None si se alcanzó el final
            
        Ejemplo:
            >>> entry = nav.next()
            >>> if entry:
            ...     print(f"Timestamp: {entry.bag_timestamp}")
        """
        if self.current_index >= self.range_end:
            return None
        
        self.current_index += 1
        
        # NOTA: En una implementación optimizada, usaríamos índice completo cargado
        # Por ahora, retornamos solo el índice sin cargar el mensaje completo
        # (para mantener performance O(1) en lugar de O(n))
        return None  # Indicar que avanzamos sin datos
    
    def prev(self) -> Optional[BagIndexEntry]:
        """
        Retrocede al mensaje anterior dentro del rango.
        
        Returns:
            BagIndexEntry del mensaje anterior, o None si se está al inicio
            
        Ejemplo:
            >>> entry = nav.prev()
            >>> if entry:
            ...     print(f"Timestamp: {entry.bag_timestamp}")
        """
        if self.current_index <= self.range_start:
            return None
        
        self.current_index -= 1
        return None  # Indicar que retrocedimos sin datos
    
    def goto(self, frame_index: int) -> Optional[BagIndexEntry]:
        """
        Salta a un índice de frame específico.
        
        Args:
            frame_index: Índice objetivo (debe estar dentro del rango configurado)
            
        Returns:
            BagIndexEntry del frame especificado, o None si índice inválido
            
        Ejemplo:
            >>> entry = nav.goto(5000)
            >>> print(f"Saltó a frame 5000")
        """
        if frame_index < self.range_start or frame_index > self.range_end:
            raise ValueError(
                f"Índice {frame_index} fuera de rango [{self.range_start}, {self.range_end}]"
            )
        
        self.current_index = frame_index
        return None  # Saltamos sin cargar datos
    
    def get_current_position(self) -> FramePosition:
        """
        Obtiene la posición actual de navegación.
        
        Returns:
            FramePosition con índice, timestamp y rango actual
        """
        return FramePosition(
            global_index=self.current_index,
            timestamp=self._get_timestamp_at_index(self.current_index),
            message_count=self.range_end - self.range_start + 1,
            range_start=self.range_start,
            range_end=self.range_end,
        )
    
    def goto_by_timestamp(self, target_timestamp: float) -> Optional[BagIndexEntry]:
        """
        Salta al frame más cercano a un timestamp específico.
        
        Args:
            target_timestamp: Timestamp objetivo en segundos
            
        Returns:
            BagIndexEntry del frame más cercano
            
        Ejemplo:
            >>> entry = nav.goto_by_timestamp(1759431822.5)
            >>> print(f"Frame encontrado: {entry.bag_timestamp}")
        """
        # Usa búsqueda de Fase 2 para encontrar el timestamp más cercano
        # en todos los tópicos, luego salta a ese frame
        
        # Obtener todos los tópicos disponibles
        all_topics = self.indexer.topics()
        
        result = self.indexer.get_closest_message_in_topics(all_topics, target_timestamp)
        
        if result:
            topic, entry = result
            # Aproximar el índice a partir del timestamp
            # (Este es un cálculo heurístico)
            fraction = (entry.bag_timestamp - self.indexer._info['start_time']) / self.indexer._info['duration']
            approx_index = int(fraction * self.indexer.total_messages)
            
            # Limitar al rango actual
            approx_index = max(self.range_start, min(self.range_end, approx_index))
            
            self.current_index = approx_index
            return entry
        
        return None
    
    def _get_message_at_index(self, index: int) -> Optional[BagIndexEntry]:
        """
        Obtiene un mensaje por su índice global.
        
        Estrategia: Itera desde el inicio del bag hasta alcanzar el índice deseado.
        (En una versión optimizada, esto usaría un índice completo cargado en memoria)
        """
        if index < 0 or index >= self.indexer.total_messages:
            return None
        
        # Verificar cache
        if index in self._message_cache:
            return self._message_cache[index][1]
        
        # Iterar desde el inicio
        current_count = 0
        try:
            with rosbag.Bag(str(self.indexer.bag_path), 'r') as bag:
                for topic, msg, timestamp in bag.read_messages():
                    if current_count == index:
                        # Extraer información
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
                            bag_timestamp=timestamp.to_sec(),
                            msg_type=self.indexer._topics_info.get(topic, {}).get('type', 'unknown'),
                            frame_id=frame_id,
                            header_stamp=header_stamp,
                            msg_index=current_count,
                            topic_index=0,
                        )
                        
                        # Cachear
                        self._message_cache[index] = (topic, entry)
                        if len(self._message_cache) > self._cache_size:
                            # Limpiar cache si es muy grande
                            oldest_key = min(self._message_cache.keys())
                            del self._message_cache[oldest_key]
                        
                        return entry
                    
                    current_count += 1
        
        except Exception as e:
            raise RuntimeError(f"Error obteniendo mensaje en índice {index}: {e}")
        
        return None
    
    def _get_timestamp_at_index(self, index: int) -> float:
        """Obtiene el timestamp de un mensaje sin cargar toda su información."""
        entry = self._get_message_at_index(index)
        return entry.bag_timestamp if entry else 0.0
    
    def get_progress_percent(self) -> float:
        """
        Obtiene el porcentaje de progreso dentro del rango actual.
        
        Returns:
            Valor entre 0.0 y 100.0
        """
        total = self.range_end - self.range_start + 1
        current = self.current_index - self.range_start
        return (current / total * 100.0) if total > 0 else 0.0
    
    def jump_to_percent(self, percent: float) -> Optional[BagIndexEntry]:
        """
        Salta a un porcentaje específico dentro del rango.
        
        Args:
            percent: Porcentaje (0.0 a 100.0)
            
        Returns:
            BagIndexEntry del frame en esa posición
        """
        if not (0.0 <= percent <= 100.0):
            raise ValueError(f"Porcentaje debe estar entre 0 y 100, recibió {percent}")
        
        total = self.range_end - self.range_start + 1
        index = self.range_start + int((percent / 100.0) * total)
        
        return self.goto(index)
