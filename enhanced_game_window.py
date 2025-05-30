#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Versión mejorada del juego con múltiples niveles, gatos con visión limitada,
zonas especiales y múltiples agentes.
"""

import random
import time
import math
import os
import json
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
from PyQt5.QtGui import QPainter, QColor, QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal
from mejora import ParticleSystem

class GameObject:    
    def __init__(self, x, y, size, color):
        self.x = x
        self.y = y
        self.size = size
        self.color = color
    
    def draw(self, painter):
        painter.fillRect(self.x * self.size, self.y * self.size, 
                        self.size, self.size, self.color)
    
    def get_position(self):
        return (self.x, self.y)
    
    def set_position(self, x, y):
        self.x = x
        self.y = y

class Mouse(GameObject):
    def __init__(self, x, y, size):
        super().__init__(x, y, size, QColor(100, 150, 255))
        self.is_invisible = False
        self.is_immune = False
        self.immunity_timer = 0
        self.invisibility_timer = 0
    
    def draw(self, painter):
        # Si es invisible, dibuja con transparencia
        if self.is_invisible:
            painter.setBrush(QColor(100, 150, 255, 100))
        else:
            painter.setBrush(self.color)
        
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            self.x * self.size, 
            self.y * self.size, 
            self.size, 
            self.size
        )
        
        # Indicador de inmunidad
        if self.is_immune:
            painter.setBrush(QColor(255, 255, 0, 150))
            painter.drawEllipse(
                self.x * self.size - 2, 
                self.y * self.size - 2, 
                self.size + 4, 
                self.size + 4
            )
    
    def update(self):
        # Actualizar efectos especiales
        if self.immunity_timer > 0:
            self.immunity_timer -= 1
            self.is_immune = True
        else:
            self.is_immune = False
            
        if self.invisibility_timer > 0:
            self.invisibility_timer -= 1
            self.is_invisible = True
        else:
            self.is_invisible = False

class Cat(GameObject):
    def __init__(self, x, y, size, path_finder, grid, cat_type='normal', vision_range=5):
        colors = {
            'normal': QColor(255, 100, 100),    # Rojo más vivo
            'hunter': QColor(200, 50, 50),      # Rojo oscuro
            'speedy': QColor(255, 160, 80),     # Naranja
            'smart': QColor(180, 100, 255)      # Púrpura
        }
        super().__init__(x, y, size, colors.get(cat_type, QColor(255, 100, 100)))
        
        self.cat_type = cat_type
        self.path_finder = path_finder
        self.grid = grid  # Almacenar referencia al grid
        self.path = []
        self.last_update = time.time()
        self.vision_range = vision_range
        
        # Configurar comportamiento según tipo
        if cat_type == 'hunter':
            self.update_interval = 0.2  # Más rápido
            self.vision_range = vision_range + 3
        elif cat_type == 'speedy':
            self.update_interval = 0.15  # El más rápido
            self.vision_range = max(3, vision_range - 1)
        elif cat_type == 'smart':
            self.update_interval = 0.25
            self.vision_range = vision_range + 1
        else:  # normal
            self.update_interval = 0.3
            self.vision_range = vision_range
            
        self.target_pos = None
        self.last_known_mouse_pos = None
        self.search_mode = True
        self.patrol_points = []
        self.current_patrol_target = 0
        self.stuck_counter = 0
        self.last_position = (x, y)
        self.stuck_time = 0
        self.direction_change_timer = 0
        self.last_valid_path = None

    def draw(self, painter):
        # Dibujar el cuerpo del gato
        painter.setBrush(self.color)
        painter.setPen(Qt.NoPen)
        
        # Posición central del gato
        center_x = self.x * self.size + self.size // 2
        center_y = self.y * self.size + self.size // 2
        
        # Dibujar el cuerpo principal (más redondeado)
        body_size = int(self.size * 0.8)
        body_x = center_x - body_size // 2
        body_y = center_y - body_size // 2
        painter.drawEllipse(body_x, body_y, body_size, body_size)
        
        # Dibujar las orejas - convertir todos los valores a enteros
        ear_size = int(self.size * 0.3)
        ear_height = int(ear_size * 1.5)
        
        # Oreja izquierda
        painter.drawPolygon([
            QPoint(center_x - ear_size, center_y - ear_size),
            QPoint(center_x - ear_size//2, center_y - ear_height),
            QPoint(center_x, center_y - ear_size)
        ])
        
        # Oreja derecha
        painter.drawPolygon([
            QPoint(center_x, center_y - ear_size),
            QPoint(center_x + ear_size//2, center_y - ear_height),
            QPoint(center_x + ear_size, center_y - ear_size)
        ])
        
        # Dibujar los ojos
        painter.setBrush(QColor(255, 255, 100))  # Ojos amarillos
        eye_size = int(self.size * 0.15)
        painter.drawEllipse(center_x - eye_size*2, center_y - eye_size, eye_size, eye_size)
        painter.drawEllipse(center_x + eye_size, center_y - eye_size, eye_size, eye_size)
        
        # Dibujar rango de visión (semi-transparente)
        if not self.search_mode:  # Solo mostrar cuando está persiguiendo
            vision_color = QColor(self.color.red(), self.color.green(), self.color.blue(), 30)
            painter.setBrush(vision_color)
            vision_size = (2 * self.vision_range + 1) * self.size
            vision_x = (self.x - self.vision_range) * self.size
            vision_y = (self.y - self.vision_range) * self.size
            painter.drawEllipse(vision_x, vision_y, vision_size, vision_size)
    
    def update_path(self, grid, mouse_pos, mouse_invisible=False):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Verificar si está atascado
        if self.get_position() == self.last_position:
            self.stuck_counter += 1
            self.stuck_time += self.update_interval
        else:
            self.stuck_counter = 0
            self.stuck_time = 0
            self.last_position = self.get_position()
        
        # Si está atascado por mucho tiempo, tomar acción más drástica
        if self.stuck_time > 2.0:  # Si está atascado por más de 2 segundos
            self.find_escape_route(grid)
            self.stuck_time = 0
            return
        
        # Verificar si puede ver al ratón
        can_see = self.can_see_mouse(mouse_pos) and not mouse_invisible
        
        if can_see:
            # El gato ve al ratón - perseguir directamente
            self.search_mode = False
            self.last_known_mouse_pos = mouse_pos
            
            if self.cat_type == 'smart':
                # Predecir movimiento del ratón
                dx = mouse_pos[0] - self.x
                dy = mouse_pos[1] - self.y
                predicted_x = mouse_pos[0] + (dx//2)
                predicted_y = mouse_pos[1] + (dy//2)
                if 0 <= predicted_x < len(grid[0]) and 0 <= predicted_y < len(grid):
                    if grid[predicted_y][predicted_x] == 0:
                        mouse_pos = (predicted_x, predicted_y)
            
            new_path = self.path_finder.find_path(grid, self.get_position(), mouse_pos)
            if new_path:
                self.path = new_path
                self.last_valid_path = new_path
            elif self.last_valid_path:
                # Si no encuentra nuevo camino, intentar seguir el último válido
                self.path = self.last_valid_path
            
        else:
            # No puede ver al ratón
            if self.last_known_mouse_pos and not self.search_mode:
                if self.get_position() != self.last_known_mouse_pos:
                    new_path = self.path_finder.find_path(grid, self.get_position(), self.last_known_mouse_pos)
                    if new_path:
                        self.path = new_path
                    else:
                        self.search_mode = True
                        self.generate_patrol_points(len(grid[0]), len(grid), grid)
                else:
                    self.search_mode = True
                    self.generate_patrol_points(len(grid[0]), len(grid), grid)
            else:
                self.patrol_mode(grid)
        
        # Si no hay path y no está en modo patrulla, cambiar a modo patrulla
        if not self.path and not self.search_mode:
            self.search_mode = True
            self.generate_patrol_points(len(grid[0]), len(grid), grid)

    def find_escape_route(self, grid):
        """Busca una ruta de escape cuando está atascado"""
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0), 
                     (1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        # Intentar moverse en una dirección aleatoria
        random.shuffle(directions)
        for dx, dy in directions:
            new_x = self.x + dx
            new_y = self.y + dy
            
            # Verificar si la nueva posición es válida
            if (0 <= new_x < len(grid[0]) and 
                0 <= new_y < len(grid) and 
                grid[new_y][new_x] == 0):
                
                # Intentar encontrar un camino hacia esta nueva posición
                escape_path = self.path_finder.find_path(grid, 
                                                       self.get_position(), 
                                                       (new_x, new_y))
                if escape_path:
                    self.path = escape_path
                    return True
        return False

    def patrol_mode(self, grid):
        """Implementa el comportamiento de patrulla cuando no ve al ratón"""
        # Si no hay puntos de patrulla o la lista está vacía, generar nuevos
        if not self.patrol_points:
            self.generate_patrol_points(len(grid[0]), len(grid), grid)
            # Si aún no hay puntos después de generar, crear un punto por defecto
            if not self.patrol_points:
                self.create_default_patrol_point(grid)
        
        # Asegurarse de que current_patrol_target es válido
        if self.current_patrol_target >= len(self.patrol_points):
            self.current_patrol_target = 0
        
        # Actualizar el tiempo para cambio de dirección
        self.direction_change_timer += self.update_interval
        
        # Cambiar de objetivo cada cierto tiempo incluso si no se ha alcanzado
        if self.direction_change_timer >= 3.0:  # Cambiar dirección cada 3 segundos
            self.current_patrol_target = (self.current_patrol_target + 1) % len(self.patrol_points)
            self.direction_change_timer = 0
            
        target = self.patrol_points[self.current_patrol_target]
        
        # Si llegamos al objetivo o estamos atascados
        if self.get_position() == target or self.stuck_counter > 3:
            self.current_patrol_target = (self.current_patrol_target + 1) % len(self.patrol_points)
            self.stuck_counter = 0
        
        new_path = self.path_finder.find_path(grid, self.get_position(), target)
        if new_path:
            self.path = new_path
        else:
            # Si no encuentra camino, intentar generar nuevos puntos
            self.generate_patrol_points(len(grid[0]), len(grid), grid)
            if not self.patrol_points:
                self.create_default_patrol_point(grid)

    def create_default_patrol_point(self, grid):
        """Crea un punto de patrulla por defecto cuando no se pueden generar puntos normales"""
        # Buscar en espiral desde la posición actual
        x, y = self.x, self.y
        for radius in range(1, max(len(grid), len(grid[0]))):
            for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:  # Cuatro direcciones principales
                new_x = x + dx * radius
                new_y = y + dy * radius
                
                # Verificar si la posición es válida
                if (0 <= new_x < len(grid[0]) and 
                    0 <= new_y < len(grid) and 
                    grid[new_y][new_x] == 0):
                    # Encontramos un punto válido
                    self.patrol_points = [(new_x, new_y)]
                    return
        
        # Si no encontramos ningún punto, usar la posición actual
        self.patrol_points = [(self.x, self.y)]

    def generate_patrol_points(self, width, height, grid):
        """Genera puntos de patrulla en el mapa de manera más inteligente"""
        self.patrol_points = []
        attempts = 0
        num_points = 6  # Aumentar número de puntos de patrulla
        
        # Dividir el mapa en sectores
        sector_width = max(1, width // 2)
        sector_height = max(1, height // 2)
        
        while len(self.patrol_points) < num_points and attempts < 50:
            # Elegir un sector
            sector_x = random.randint(0, 1)
            sector_y = random.randint(0, 1)
            
            # Generar punto dentro del sector
            x = random.randint(sector_x * sector_width, 
                             min((sector_x + 1) * sector_width - 1, width - 1))
            y = random.randint(sector_y * sector_height, 
                             min((sector_y + 1) * sector_height - 1, height - 1))
            
            # Verificar que el punto es válido y alcanzable
            if ((x, y) not in self.patrol_points and 
                0 <= x < width and 0 <= y < height and
                grid[y][x] == 0 and 
                self.path_finder.find_path(grid, self.get_position(), (x, y))):
                
                self.patrol_points.append((x, y))
            attempts += 1

    def move(self):
        """Mueve al gato siguiendo su path actual"""
        if self.path and len(self.path) > 1:
            next_pos = self.path[1]  # El siguiente punto en el camino
            self.set_position(next_pos[0], next_pos[1])
            self.path = self.path[1:]  # Eliminar el punto actual del camino
        elif self.path:  # Si solo queda un punto en el path
            self.path = []  # Limpiar el path

    def can_see_mouse(self, mouse_pos):
        """Verifica si el gato puede ver al ratón basado en la distancia Manhattan y los obstáculos"""
        if not mouse_pos:
            return False
            
        # Calcular distancia Manhattan
        distance = abs(self.x - mouse_pos[0]) + abs(self.y - mouse_pos[1])
        
        # Si está fuera del rango de visión, no puede ver
        if distance > self.vision_range:
            return False
            
        # Verificar si hay obstáculos en la línea de visión
        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        steps = max(abs(dx), abs(dy))
        
        if steps == 0:
            return True
            
        x_step = dx / steps
        y_step = dy / steps
        
        current_x = float(self.x)
        current_y = float(self.y)
        
        # Comprobar cada punto en la línea entre el gato y el ratón
        for _ in range(int(steps)):
            current_x += x_step
            current_y += y_step
            
            # Redondear al punto de la cuadrícula más cercano
            check_x = int(round(current_x))
            check_y = int(round(current_y))
            
            # Si hay una pared en el camino, no puede ver
            try:
                if self.grid[check_y][check_x] == 1:
                    return False
            except (IndexError, AttributeError):
                return False
        
        return True

class Goal(GameObject):
    def __init__(self, x, y, size):
        super().__init__(x, y, size, QColor(120, 255, 120))
    
    def draw(self, painter):
        painter.setBrush(self.color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            self.x * self.size, 
            self.y * self.size, 
            self.size, 
            self.size
        )

class Wall(GameObject):
    def __init__(self, x, y, size, wall_type='normal'):
        self.wall_type = wall_type
        if wall_type == 'heavy':
            color = QColor(60, 60, 60)  # Más oscuro para paredes resistentes
        elif wall_type == 'cracked':
            color = QColor(120, 100, 100)  # Color para paredes agrietadas
        elif wall_type == 'decorative':
            color = QColor(100, 90, 80)  # Color para paredes decorativas
        else:
            color = QColor(80, 80, 80)  # Color normal
        super().__init__(x, y, size, color)
        
        # Variación visual para cada pared
        self.variation = random.randint(0, 3)
    
    def draw(self, painter):
        # Dibujar el fondo de la pared
        painter.fillRect(self.x * self.size, self.y * self.size, 
                        self.size, self.size, self.color)
        
        # Agregar detalles según el tipo y variación
        painter.setPen(QColor(self.color.red() - 20, self.color.green() - 20, self.color.blue() - 20))
        
        if self.wall_type == 'heavy':
            # Patrón de refuerzo para paredes resistentes
            painter.drawRect(self.x * self.size + 2, self.y * self.size + 2, 
                           self.size - 4, self.size - 4)
            painter.drawLine(self.x * self.size, self.y * self.size, 
                           self.x * self.size + self.size, self.y * self.size + self.size)
            painter.drawLine(self.x * self.size + self.size, self.y * self.size, 
                           self.x * self.size, self.y * self.size + self.size)
                           
        elif self.wall_type == 'cracked':
            # Dibujar grietas aleatorias
            for _ in range(3):
                start_x = self.x * self.size + random.randint(0, self.size)
                start_y = self.y * self.size + random.randint(0, self.size)
                end_x = start_x + random.randint(-self.size//2, self.size//2)
                end_y = start_y + random.randint(-self.size//2, self.size//2)
                painter.drawLine(start_x, start_y, end_x, end_y)
                
        elif self.wall_type == 'decorative':
            # Patrones decorativos según la variación
            if self.variation == 0:
                # Patrón de círculos
                painter.drawEllipse(self.x * self.size + 4, self.y * self.size + 4,
                                  self.size - 8, self.size - 8)
            elif self.variation == 1:
                # Patrón de diamante
                points = [
                    QPoint(self.x * self.size + self.size//2, self.y * self.size + 2),
                    QPoint(self.x * self.size + self.size - 2, self.y * self.size + self.size//2),
                    QPoint(self.x * self.size + self.size//2, self.y * self.size + self.size - 2),
                    QPoint(self.x * self.size + 2, self.y * self.size + self.size//2)
                ]
                for i in range(4):
                    painter.drawLine(points[i], points[(i + 1) % 4])
            else:
                # Patrón de líneas
                step = self.size // 4
                for i in range(0, self.size, step):
                    painter.drawLine(self.x * self.size + i, self.y * self.size,
                                   self.x * self.size + i, self.y * self.size + self.size)

class SpecialZone(GameObject):
    def __init__(self, x, y, size, zone_type):
        self.zone_type = zone_type  # 'immunity' o 'invisibility'
        if zone_type == 'immunity':
            color = QColor(255, 255, 100, 150)  # Amarillo para inmunidad
        else:
            color = QColor(200, 100, 255, 150)  # Púrpura para invisibilidad
        super().__init__(x, y, size, color)
        self.cooldown = 0  # Tiempo de espera antes de que la zona pueda usarse nuevamente
    
    def draw(self, painter):
        painter.setBrush(self.color)
        painter.setPen(Qt.NoPen)
        painter.drawRect(
            self.x * self.size, 
            self.y * self.size, 
            self.size, 
            self.size
        )

    def can_use(self):
        """Verifica si la zona especial está disponible para su uso"""
        return self.cooldown == 0

    def use(self):
        """Activa la zona especial y establece un tiempo de espera"""
        self.cooldown = 90  # 15 segundos de espera (ajustable)

class GameStats:
    """Clase para manejar las estadísticas y progreso del juego"""
    def __init__(self):
        self.score = 0
        self.level = 1
        self.lives = 3
    
    def reset(self):
        self.score = 0
        self.level = 1
        self.lives = 3

class GameArea(QWidget):
    score_changed = pyqtSignal(int)
    lives_changed = pyqtSignal(int)
    level_changed = pyqtSignal(int)

    def __init__(self, parent, path_finder):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Ajustar tamaño de la cuadrícula para mejor visualización
        self.grid_size = 20  # Tamaño de cada celda
        self.grid_width = 30  # Ancho del tablero
        self.grid_height = 20  # Alto del tablero
        
        # Configuración de niveles con bonus
        self.levels_config = {
            1: {'cats': [('normal', 1)], 'special_zones': 2, 'bonus': 500},
            2: {'cats': [('normal', 2)], 'special_zones': 3, 'bonus': 750},
            3: {'cats': [('normal', 1), ('hunter', 1)], 'special_zones': 3, 'bonus': 1000},
            4: {'cats': [('normal', 1), ('speedy', 1)], 'special_zones': 4, 'bonus': 1250},
            5: {'cats': [('normal', 1), ('smart', 1)], 'special_zones': 4, 'bonus': 1500},
            6: {'cats': [('normal', 1), ('hunter', 1), ('speedy', 1)], 'special_zones': 5, 'bonus': 2000}
        }
        
        # Diseños predefinidos de niveles (1 = pared, 0 = espacio libre, S = inicio, G = meta)
        self.level_designs = {
            1: [  # Nivel 1: Laberinto con Callejones
                "000000000010000000010000100000",
                "0S0010001110100000010100100000",
                "000010101010101010101010101000",
                "001000000100100010000000101000",
                "000010100000101000101010001000",
                "001010001010001000001000101000",
                "000000101000100010100010001000",
                "001010001010001000001000101000",
                "000010100000101010101010001000",
                "001010001010001000001000101000",
                "000010100010101010101010101000",
                "001000001000001000001000001000",
                "000010101010101010101010101000",
                "001010001000001000001G00001000",
                "000010100010101010101010100000",
                "001000001010001000001000101000",
                "000010101000101010101010001000",
                "001010001010001000001000101000",
                "000010100010111010101010001000",
                "000010100000010000000000000000"
            ],
            2: [  # Nivel 2: Fortaleza con Múltiples Barreras
                "000000000110000000000000000000",
                "0S0101010101010101010101000000",
                "000000000000100000000000001000",
                "001111111110101011111111101000",
                "001000000000101000000000101000",
                "001010111110101010111110101000",
                "001010000010100010000010101000",
                "001010101110101110101110101000",
                "001010100000100000100010101000",
                "001010101111101111101010101000",
                "0010101000001000G0100010101000",
                "001010111110101110111110101000",
                "001010000010100010000010101000",
                "001011111010101010111110101000",
                "001000001010101010000000101000",
                "001111101010101010111111101000",
                "000000101010101010100000001000",
                "001111101010101010111111101000",
                "000000000010000010000000001000",
                "001111111111111111111111111000"
            ],
            3: [  # Nivel 3: Laberinto Espiral Reforzado
                "000000000010000100000000000000",
                "0S1111111110111100111111100000",
                "000000000000000000000000101000",
                "001111111111111111111110101000",
                "001000000000000000000010101000",
                "001011111111111111111010101000",
                "001010000000000000001010101000",
                "001010111111111111101010101000",
                "001010100000000000101010101000",
                "001010101111111110101010101000",
                "001010101000000G10101010101000",
                "001010101011111110101010101000",
                "001010101010000010101010101000",
                "001010101010111110101010101000",
                "001010101010100010101010101000",
                "001010101010101110101010101000",
                "001010101010000000101010101000",
                "001010101011111111101010101000",
                "001000000000000000000000101000",
                "001111111111111111111111101000"
            ],
            4: [  # Nivel 4: Castillo Fortificado
                "000000000000000000000000000000",
                "0S0111111100000111111100000000",
                "000100000100001000000111111100",
                "000101110111111011110100000100",
                "000101010100001000010111110100",
                "000101010111101011110100010100",
                "000101010000101010000101110100",
                "000101011110101010111101010100",
                "000101000010101010100001010100",
                "0001011111101G1010101111010100",
                "000100000000101010100000010100",
                "000111111111101010101111110100",
                "000000000000001010100000000100",
                "001111111111101010111111111100",
                "001000000000101010000000000100",
                "001011111110101011111111110100",
                "001010000010101000000000010100",
                "001010111110101111111111110100",
                "001000000000100000000000000100",
                "001111111111111111111111111100"
            ],
            5: [  # Nivel 5: Ciudad Amurallada
                "000000000010000100001100000000",
                "0S0111110011111001111100100000",
                "000100010010001001000100101000",
                "000101110011111001111100101000",
                "000100010010001001000000101000",
                "000111110011111001111111101000",
                "000000010000001001000000101000",
                "001111110111101001011110101000",
                "001000000100001001010000101000",
                "001011111101111001010111101000",
                "001010000100001G01010000101000",
                "001010110111111001011110101000",
                "001010010000001001000010101000",
                "001010011111101111111010101000",
                "001010010000100000001010101000",
                "001010010110111111101010101000",
                "001010010010000000101010101000",
                "001011110011111111101010101000",
                "001000000000000000001010001000",
                "001111111111111111111011111000"
            ],
            6: [  # Nivel 6: Metrópolis del Caos
                "000000000000000000000000000000",
                "0S0100000000000000000000000000",
                "000011111111111111111111111100",
                "000010000000000000000000000100",
                "000010111111111111111111110100",
                "000010100000000000000000010100",
                "000010101111111111111111010100",
                "000010101000000000000001010100",
                "000010101011111111111101010100",
                "000010101010000000000101010100",
                "000010101010111111110101010100",
                "000010101010100000010101G10100",
                "000010101010101111110101010100",
                "000010101010101000010101010100",
                "000010101010101011110101010100",
                "000010101010101000000101010100",
                "000010101010101111111101010100",
                "000010101010000000000001010100",
                "000010101011111111111111010100",
                "000000000000000000000000000000"
            ]
        }
        
        # Inicialización del juego
        self.grid = [[0 for _ in range(self.grid_width)] for _ in range(self.grid_height)]
        
        # Objetos del juego
        self.path_finder = path_finder
        self.mouse = Mouse(1, 1, self.grid_size)
        self.cats = []
        self.goal = Goal(self.grid_width - 2, 1, self.grid_size)
        self.walls = []
        self.special_zones = []
        self.particles = ParticleSystem()
        
        # Estado del juego con valores ajustados
        self.current_level = 1
        self.max_level = 6
        self.lives = 5  # Aumentado a 5 vidas iniciales
        self.score = 0
        self.bonus_multiplier = 1.0
        self.consecutive_captures = 0  # Nueva variable para rastrear capturas consecutivas
        self.time_bonus = 1000  # Bonus inicial por tiempo
        self.power_ups_collected = 0  # Contador de power-ups recolectados
        self.game_over = False
        self.game_won = False
        self.level_completed = False
        self.paused = False
        
        # Controles
        self.move_directions = {
            Qt.Key_Up: (0, -1),
            Qt.Key_Down: (0, 1),
            Qt.Key_Left: (-1, 0),
            Qt.Key_Right: (1, 0),
        }
        
        # Timer
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_game)
        self.game_timer.start(150)
        
        # Configurar nivel inicial
        self.setup_level()
        
        # Ajustar tamaño de la ventana
        self.setFixedSize(self.grid_width * self.grid_size, self.grid_height * self.grid_size)
        
        # Emitir señales iniciales
        self.lives_changed.emit(self.lives)
        self.level_changed.emit(self.current_level)
        self.score_changed.emit(self.score)

    def setup_level(self):
        """Configura el nivel actual usando el diseño predefinido"""
        config = self.levels_config.get(self.current_level, self.levels_config[1])
        level_design = self.level_designs.get(self.current_level, self.level_designs[1])
        
        # Limpiar objetos anteriores
        self.cats = []
        self.walls = []
        self.special_zones = []
        
        # Cargar el diseño del nivel
        self.grid = [[0 for _ in range(self.grid_width)] for _ in range(self.grid_height)]
        start_pos = None
        goal_pos = None
        
        # Crear caminos seguros primero
        safe_zone_width = 2  # Ancho del camino seguro
        
        # Interpretar el diseño del nivel con consideraciones de jugabilidad
        for y, row in enumerate(level_design):
            for x, cell in enumerate(row):
                if cell == '1':
                    # Verificar si estamos cerca del inicio o la meta
                    near_start = x < 5 and y < 5  # Zona inicial más amplia
                    near_goal = x > self.grid_width - 6 and y < 5  # Zona final más amplia
                    
                    # No colocar paredes en zonas seguras
                    if near_start or near_goal:
                        continue
                    
                    # Evitar crear callejones sin salida
                    neighbors = 0
                    for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                            if self.grid[ny][nx] == 1:
                                neighbors += 1
                    
                    # Solo colocar la pared si no crea un callejón sin salida
                    if neighbors <= 2:
                        self.grid[y][x] = 1
                        wall_type = random.choice(['normal', 'normal', 'normal', 'heavy', 'cracked', 'decorative'])
                        self.walls.append(Wall(x, y, self.grid_size, wall_type))
                elif cell == 'S':
                    start_pos = (x, y)
                elif cell == 'G':
                    goal_pos = (x, y)
        
        # Asegurar que hay suficientes espacios abiertos
        self.create_safe_paths()
        
        # Configurar posiciones iniciales
        if start_pos:
            self.mouse.set_position(start_pos[0], start_pos[1])
        if goal_pos:
            self.goal.set_position(goal_pos[0], goal_pos[1])
        
        # Crear gatos según la configuración del nivel pero con posiciones más justas
        for cat_type, count in config['cats']:
            for _ in range(count):
                self.spawn_cat_balanced(cat_type)
        
        # Generar zonas especiales en lugares estratégicos
        self.generate_strategic_special_zones(config['special_zones'])
        
        # Reiniciar estados
        self.mouse.immunity_timer = 0
        self.mouse.invisibility_timer = 0
        self.mouse.speed_timer = 0
        self.level_completed = False
        
        # Emitir señales
        self.level_changed.emit(self.current_level)
        self.lives_changed.emit(self.lives)

    def create_safe_paths(self):
        """Crea caminos seguros en el nivel"""
        # Asegurar que hay un camino principal
        start = self.mouse.get_position()
        goal = self.goal.get_position()
        
        # Crear un camino principal limpio
        path = self.path_finder.find_path(self.grid, start, goal)
        if path:
            # Ensanchar el camino principal
            for x, y in path:
                # Limpiar un área alrededor del camino
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                            if random.random() < 0.7:  # 70% de probabilidad de limpiar
                                self.grid[ny][nx] = 0
                                # Eliminar la pared si existe
                                self.walls = [w for w in self.walls if not (w.x == nx and w.y == ny)]

    def spawn_cat_balanced(self, cat_type):
        """Genera un gato en una posición equilibrada"""
        attempts = 0
        min_distance = 8  # Distancia mínima del ratón
        
        while attempts < 50:
            x = random.randint(self.grid_width//2, self.grid_width - 2)
            y = random.randint(1, self.grid_height - 2)
            
            # Calcular distancia al ratón
            mouse_pos = self.mouse.get_position()
            distance = abs(x - mouse_pos[0]) + abs(y - mouse_pos[1])
            
            # Verificar si la posición es válida y está lo suficientemente lejos
            if (self.grid[y][x] == 0 and 
                distance >= min_distance and 
                (x, y) != self.goal.get_position()):
                
                cat = Cat(x, y, self.grid_size, self.path_finder, self.grid, cat_type)
                cat.generate_patrol_points(self.grid_width, self.grid_height, self.grid)
                self.cats.append(cat)
                return True
                
            attempts += 1
        return False

    def generate_strategic_special_zones(self, num_zones):
        """Genera zonas especiales en ubicaciones estratégicas"""
        self.special_zones = []
        min_distance = 4  # Distancia mínima entre zonas
        
        for _ in range(num_zones):
            attempts = 0
            while attempts < 50:
                x = random.randint(0, self.grid_width - 1)
                y = random.randint(0, self.grid_height - 1)
                
                # Verificar si la posición es válida y estratégica
                if self.is_strategic_position(x, y, min_distance):
                    zone_type = self.choose_strategic_zone_type(x, y)
                    self.special_zones.append(SpecialZone(x, y, self.grid_size, zone_type))
                    break
                    
                attempts += 1

    def is_strategic_position(self, x, y, min_distance):
        """Verifica si una posición es estratégica para una zona especial"""
        if self.grid[y][x] == 1:  # No colocar en paredes
            return False
            
        # Verificar distancia con otras zonas especiales
        for zone in self.special_zones:
            if abs(zone.x - x) + abs(zone.y - y) < min_distance:
                return False
                
        # Evitar posiciones muy cerca del inicio o meta
        if (abs(x - self.mouse.x) + abs(y - self.mouse.y) < 3 or 
            abs(x - self.goal.x) + abs(y - self.goal.y) < 3):
            return False
            
        # Preferir posiciones cerca de intersecciones o caminos
        open_neighbors = 0
        for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < self.grid_width and 
                0 <= ny < self.grid_height and 
                self.grid[ny][nx] == 0):
                open_neighbors += 1
                
        return open_neighbors >= 2  # Al menos dos caminos adyacentes

    def choose_strategic_zone_type(self, x, y):
        """Elige el tipo de zona especial según la ubicación"""
        # Calcular distancias
        dist_to_start = abs(x - self.mouse.x) + abs(y - self.mouse.y)
        dist_to_goal = abs(x - self.goal.x) + abs(y - self.goal.y)
        
        # Favorecer invisibilidad en zonas más cercanas a los gatos
        near_cats = any(abs(cat.x - x) + abs(cat.y - y) < 5 for cat in self.cats)
        
        if near_cats:
            return 'invisibility'
        else:
            return 'immunity'
        
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Fondo
        painter.fillRect(0, 0, self.width(), self.height(), QColor(240, 240, 240))
        
        # Grilla
        painter.setPen(QColor(220, 220, 220))
        for i in range(self.grid_width + 1):
            painter.drawLine(i * self.grid_size, 0, i * self.grid_size, self.height())
        for i in range(self.grid_height + 1):
            painter.drawLine(0, i * self.grid_size, self.width(), i * self.grid_size)
        
        # Dibujar objetos
        for zone in self.special_zones:
            zone.draw(painter)
        
        for wall in self.walls:
            wall.draw(painter)
    
        self.goal.draw(painter)
        
        for cat in self.cats:
            cat.draw(painter)
        
        self.mouse.draw(painter)
        
        # Interfaz de juego
        if self.game_over or self.game_won or self.level_completed:
            painter.fillRect(0, 0, self.width(), self.height(), QColor(0, 0, 0, 150))
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont('Arial', 20, QFont.Bold))
            
            if self.level_completed:
                if self.current_level >= self.max_level:
                    message = "¡JUEGO COMPLETADO!"
                else:
                    message = f"¡NIVEL {self.current_level} COMPLETADO!"
            else:
                message = "¡GANASTE!" if self.game_won else "¡PERDISTE!"
            
            rect = QRect(0, 0, self.width(), self.height())
            painter.drawText(rect, Qt.AlignCenter, message)
    
    def update_score(self, points):
        """Actualiza la puntuación con sistema de multiplicador mejorado"""
        # Calcular multiplicador basado en nivel y rendimiento
        level_multiplier = 1.0 + (self.current_level - 1) * 0.2
        performance_multiplier = 1.0 + (self.power_ups_collected * 0.1)
        time_multiplier = max(0.5, self.time_bonus / 1000)
        
        # Aplicar multiplicadores
        final_points = int(points * level_multiplier * performance_multiplier * time_multiplier)
        
        # Ajustar score
        self.score += final_points
        
        # Bonus por cada 5000 puntos: vida extra
        if (self.score // 5000) > ((self.score - final_points) // 5000):
            self.add_life("¡Vida extra por puntuación!")
        
        self.score_changed.emit(self.score)

    def add_life(self, reason=""):
        """Añade una vida con límite máximo"""
        if self.lives < 7:  # Máximo 7 vidas
            self.lives += 1
            self.lives_changed.emit(self.lives)

    def on_mouse_caught(self):
        """Manejo mejorado cuando el ratón es atrapado por un gato"""
        self.lives -= 1
        self.lives_changed.emit(self.lives)
        
        # Penalización por muerte más severa en niveles altos
        base_penalty = -200 * (1 + (self.current_level - 1) * 0.3)
        self.consecutive_captures += 1
        
        # Penalización adicional por muertes consecutivas
        if self.consecutive_captures > 1:
            base_penalty *= (1 + (self.consecutive_captures - 1) * 0.2)
        
        self.update_score(int(base_penalty))
        
        if self.lives <= 0:
            self.game_over = True
            self.game_timer.stop()
            self.save_high_score()  # Guardar puntuación al perder
        else:
            # Dar inmunidad temporal al reaparecer
            self.mouse.immunity_timer = 45  # Aumentado a 45 frames
            self.reset_positions()

    def on_level_complete(self):
        """Manejo mejorado de completar un nivel"""
        self.level_completed = True
        self.game_timer.stop()
        
        # Resetear contador de capturas consecutivas
        self.consecutive_captures = 0
        
        # Cálculo de bonus mejorado
        level_bonus = self.levels_config[self.current_level]['bonus']
        time_bonus = max(0, self.time_bonus)
        health_bonus = self.lives * 200  # Bonus por vidas restantes
        powerup_bonus = self.power_ups_collected * 150  # Bonus por power-ups
        
        # Bonus total
        total_bonus = level_bonus + time_bonus + health_bonus + powerup_bonus
        
        # Bonus adicional por completar sin morir
        if self.lives == 5:
            total_bonus *= 1.5  # 50% extra por no morir
        
        self.update_score(int(total_bonus))
        
        # Vida extra por completar nivel sin morir
        if self.lives == 5:
            self.add_life("¡Vida extra por nivel perfecto!")
        
        if self.current_level >= self.max_level:
            self.game_won = True
            self.save_high_score()  # Guardar puntuación al ganar
        
        # Emitir señales
        self.level_changed.emit(self.current_level)

    def activate_special_zone(self, zone):
        """Activar efectos de zona especial con mejores recompensas"""
        if zone.cooldown > 0:
            return
            
        zone.use()
        self.power_ups_collected += 1
        
        # Puntos mejorados por usar zonas especiales
        points = {
            'immunity': 100,
            'invisibility': 150,
            'speed': 200
        }.get(zone.zone_type, 0)
        
        # Bonus adicional por usar zonas estratégicamente
        if self.consecutive_captures > 0:
            points *= 1.5  # 50% extra si se usa después de una muerte
        
        self.update_score(int(points))
        
        # Efectos de partículas
        self.particles.add_explosion(zone.x + 0.5, zone.y + 0.5, zone.color.name(), 15)
        
        if zone.zone_type == 'immunity':
            self.mouse.immunity_timer = 60  # 10 segundos
        elif zone.zone_type == 'invisibility':
            self.mouse.invisibility_timer = 60
        elif zone.zone_type == 'speed':
            self.mouse.speed_timer = 90
        elif zone.zone_type == 'confusion':
            # Confundir a todos los gatos cercanos
            for cat in self.cats:
                if math.sqrt((cat.x - zone.x)**2 + (cat.y - zone.y)**2) < 5:
                    cat.confuse()
        elif zone.zone_type == 'teleport':
            # Encontrar una posición válida aleatoria
            attempts = 0
            while attempts < 50:
                new_x = random.randint(1, self.grid_width - 2)
                new_y = random.randint(1, self.grid_height - 2)
                if self.grid[new_y][new_x] == 0:
                    self.mouse.set_position(new_x, new_y)
                    self.particles.add_explosion(new_x + 0.5, new_y + 0.5, "#FF00FF", 20)
                    break
                attempts += 1

    def update_game(self):
        """Actualización principal del juego con manejo de tiempo"""
        if self.game_over or self.game_won or self.paused:
            return
        
        # Reducir bonus por tiempo gradualmente
        if self.time_bonus > 0:
            self.time_bonus -= 0.5  # Reducción más gradual
        
        # Actualizar ratón y efectos
        self.mouse.update()
        self.particles.update()
        
        # Verificar zonas especiales
        mouse_pos = self.mouse.get_position()
        for zone in self.special_zones:
            if mouse_pos == zone.get_position() and zone.can_use():
                self.activate_special_zone(zone)
        
        # Obtener posiciones ocupadas por gatos
        occupied_positions = set()
        for cat in self.cats:
            occupied_positions.add(cat.get_position())
        
        # Actualizar gatos
        for cat in self.cats:
            cat.update_path(self.grid, mouse_pos, self.mouse.is_invisible)
            cat.move()
            
            # Verificar captura
            if cat.get_position() == mouse_pos and not self.mouse.is_immune:
                self.on_mouse_caught()
                return
        
        # Verificar victoria del nivel
        if mouse_pos == self.goal.get_position():
            self.on_level_complete()
        
        self.update()
    
    def keyPressEvent(self, event):
        if self.game_over:
            if event.key() == Qt.Key_R:
                self.reset_level()
            return
        
        if self.level_completed:
            if event.key() == Qt.Key_Space:
                self.next_level()
            elif event.key() == Qt.Key_R:
                self.reset_level()
            return
        
        if event.key() in self.move_directions:
            dx, dy = self.move_directions[event.key()]
            new_x = self.mouse.x + dx
            new_y = self.mouse.y + dy
            
            if 0 <= new_x < self.grid_width and 0 <= new_y < self.grid_height:
                if self.grid[new_y][new_x] == 0:
                    self.mouse.set_position(new_x, new_y)
        
        self.update()
    
    def on_mouse_caught(self):
        """Manejo cuando el ratón es atrapado por un gato"""
        self.lives -= 1
        self.lives_changed.emit(self.lives)
        
        # Penalización por muerte
        self.update_score(-200)
        
        if self.lives <= 0:
            self.game_over = True
            self.game_timer.stop()
        else:
            # Dar inmunidad temporal al reaparecer
            self.mouse.immunity_timer = 30
            # Reiniciar posiciones pero mantener el nivel actual
            self.reset_positions()

    def reset_positions(self):
        """Reinicia las posiciones de los personajes manteniendo el nivel"""
        self.mouse.set_position(1, 1)
        # Reposicionar gatos lejos del ratón
        for cat in self.cats:
            attempts = 0
            while attempts < 50:
                x = random.randint(self.grid_width//2, self.grid_width - 2)
                y = random.randint(1, self.grid_height - 2)
                if self.grid[y][x] == 0:  # Asegurar que no hay pared
                    cat.set_position(x, y)
                    break
                attempts += 1

    def reset_level(self):
        """Reinicia el nivel actual"""
        if not self.game_over:  # Si no es game over, mantener las vidas
            self.setup_level()
        else:  # Si es game over, reiniciar todo
            self.lives = 3
            self.lives_changed.emit(self.lives)
            self.setup_level()
        
        self.game_over = False
        self.game_won = False
        self.level_completed = False
        self.game_timer.start()
    
    def next_level(self):
        if self.current_level < self.max_level:
            self.current_level += 1
            self.level_completed = False
            # Aumentar el multiplicador de bonus para niveles más altos
            self.bonus_multiplier = 1.0 + (self.current_level - 1) * 0.2
            self.setup_level()
            self.game_timer.start()
            # Emitir señal de cambio de nivel
            self.level_changed.emit(self.current_level)
        else:
            self.game_won = True

    def reset_game(self):
        """Reinicia completamente el juego"""
        self.current_level = 1
        self.lives = 3
        self.game_over = False
        self.game_won = False
        self.level_completed = False
        self.setup_level()
        self.game_timer.start()
        # Emitir señales de actualización
        self.lives_changed.emit(self.lives)
        self.level_changed.emit(self.current_level)

class GameStatusPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Panel de vidas con iconos
        self.lives_panel = QWidget()
        self.lives_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 100);
                border-radius: 10px;
                padding: 5px;
            }
        """)
        lives_layout = QHBoxLayout(self.lives_panel)
        self.heart_labels = []
        for _ in range(3):
            heart = QLabel("❤️")
            heart.setStyleSheet("font-size: 20px;")
            self.heart_labels.append(heart)
            lives_layout.addWidget(heart)
        layout.addWidget(self.lives_panel)
        
        layout.addStretch()
        
        # Panel de efectos activos
        self.effects_panel = QWidget()
        self.effects_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 100);
                border-radius: 10px;
                padding: 5px;
            }
            QLabel {
                color: white;
                font-size: 12px;
                padding: 3px 8px;
                border-radius: 5px;
                margin: 0 2px;
            }
        """)
        self.effects_layout = QHBoxLayout(self.effects_panel)
        layout.addWidget(self.effects_panel)
        
        layout.addStretch()
        
        # Panel de puntuación
        self.score_panel = QWidget()
        self.score_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 100);
                border-radius: 10px;
                padding: 5px;
            }
            QLabel {
                color: white;
                font-size: 16px;
            }
        """)
        score_layout = QHBoxLayout(self.score_panel)
        self.score_label = QLabel("Score: 0")
        score_layout.addWidget(self.score_label)
        layout.addWidget(self.score_panel)
        
        self.setLayout(layout)
    
    def update_lives(self, lives):
        for i, heart in enumerate(self.heart_labels):
            heart.setStyleSheet(f"font-size: 20px; color: {'red' if i < lives else 'gray'};")
    
    def update_score(self, score):
        self.score_label.setText(f"Score: {score:,}")
    
    def update_effects(self, effects):
        # Limpiar efectos anteriores
        for i in reversed(range(self.effects_layout.count())): 
            self.effects_layout.itemAt(i).widget().deleteLater()
        
        # Agregar efectos activos
        effect_styles = {
            'immunity': ('🛡️', '#FFD700'),
            'invisibility': ('👻', '#9C27B0'),
            'speed': ('⚡', '#4CAF50')
        }
        
        for effect, duration in effects.items():
            if duration > 0 and effect in effect_styles:
                icon, color = effect_styles[effect]
                effect_label = QLabel(f"{icon} {duration//10}")
                effect_label.setStyleSheet(f"background-color: {color};")
                self.effects_layout.addWidget(effect_label)

class GameWindow(QMainWindow):
    def __init__(self, path_finder):
        super().__init__()
        self.path_finder = path_finder
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('CheatGame - Nivel 1')
        self.setStyleSheet("""
            QMainWindow {
                background-color: #212121;
            }
        """)
        
        # Widget central con layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Panel de estado
        self.status_panel = GameStatusPanel()
        layout.addWidget(self.status_panel)
        
        # Área de juego
        self.game_area = GameArea(self, self.path_finder)
        layout.addWidget(self.game_area)
        
        # Panel de controles
        controls_panel = QWidget()
        controls_panel.setStyleSheet("""
            QWidget {
                background-color: #2C2C2C;
                border-top: 1px solid #424242;
            }
            QPushButton {
                background-color: #424242;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #4CAF50;
            }
        """)
        
        controls_layout = QHBoxLayout(controls_panel)
        
        pause_button = QPushButton("⏸️ Pausar")
        pause_button.clicked.connect(self.toggle_pause)
        controls_layout.addWidget(pause_button)
        
        restart_button = QPushButton("🔄 Reiniciar")
        restart_button.clicked.connect(self.game_area.reset_game)
        controls_layout.addWidget(restart_button)
        
        controls_layout.addStretch()
        
        menu_button = QPushButton("🏠 Menú")
        menu_button.clicked.connect(self.close)
        controls_layout.addWidget(menu_button)
        
        layout.addWidget(controls_panel)
        
        self.setCentralWidget(central_widget)
        self.adjustSize()
        self.center()
    
    def toggle_pause(self):
        self.game_area.paused = not self.game_area.paused
        if self.game_area.paused:
            self.game_area.game_timer.stop()
        else:
            self.game_area.game_timer.start()
    
    def center(self):
        frame_geometry = self.frameGeometry()
        screen_center = self.screen().availableGeometry().center()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())