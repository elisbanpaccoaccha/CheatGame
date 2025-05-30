#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Versión mejorada y corregida del juego con múltiples niveles, gatos con visión limitada,
zonas especiales, sistema de puntuación y mejoras de rendimiento.
"""

import random
import time
import math
import json
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QPushButton, QProgressBar, QFrame, QGridLayout,
                           QMessageBox, QSlider, QCheckBox, QSpinBox, QComboBox)
from PyQt5.QtGui import QPainter, QColor, QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal
from PyQt5.QtMultimedia import QSound

class Particle:
    def __init__(self, x, y, color, lifetime=30):
        self.x = x
        self.y = y
        self.dx = random.uniform(-2, 2)
        self.dy = random.uniform(-2, 2)
        self.life = lifetime
        self.max_life = lifetime
        self.color = QColor(color)
        self.size = random.uniform(2, 6)
        self.rotation = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-5, 5)
        
    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.dy += 0.1  # Gravedad
        self.dx *= 0.99  # Fricción
        self.dy *= 0.99
        self.life -= 1
        self.size *= 0.95  # Reducir tamaño gradualmente
        self.rotation += self.rotation_speed
        
        # Hacer que la partícula se desvanezca
        alpha = int((self.life / self.max_life) * 255)
        self.color.setAlpha(alpha)
    
    def is_alive(self):
        return self.life > 0

class Trail:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = QColor(color)
        self.life = 20
        self.max_life = 20
    
    def update(self):
        self.life -= 1
        alpha = int((self.life / self.max_life) * 100)
        self.color.setAlpha(alpha)
    
    def is_alive(self):
        return self.life > 0

class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.trails = []
    
    def add_particle(self, x, y, color):
        self.particles.append(Particle(x, y, color))
    
    def add_explosion(self, x, y, color, num_particles=20):
        for _ in range(num_particles):
            particle = Particle(x, y, color)
            # Explosión en círculo
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 3)
            particle.dx = math.cos(angle) * speed
            particle.dy = math.sin(angle) * speed
            self.particles.append(particle)
    
    def add_trail(self, x, y, color):
        self.trails.append(Trail(x, y, color))
    
    def update(self):
        # Actualizar y filtrar partículas muertas
        self.particles = [p for p in self.particles if p.is_alive()]
        for particle in self.particles:
            particle.update()
        
        # Actualizar y filtrar trails muertos
        self.trails = [t for t in self.trails if t.is_alive()]
        for trail in self.trails:
            trail.update()
    
    def draw(self, painter):
        # Dibujar trails primero (están detrás de las partículas)
        for trail in self.trails:
            gradient = QRadialGradient(
                QPointF(trail.x, trail.y),
                10
            )
            gradient.setColorAt(0, trail.color)
            color_transparent = QColor(trail.color)
            color_transparent.setAlpha(0)
            gradient.setColorAt(1, color_transparent)
            painter.setBrush(gradient)
            painter.setPen(trail.color)
            painter.drawEllipse(
                int(trail.x - 5),
                int(trail.y - 5),
                10,
                10
            )
        
        # Dibujar partículas
        for particle in self.particles:
            painter.setBrush(particle.color)
            painter.setPen(particle.color)
            
            # Guardar el estado actual del painter
            painter.save()
            
            # Trasladar al centro de la partícula
            painter.translate(
                int(particle.x),
                int(particle.y)
            )
            
            # Rotar
            painter.rotate(particle.rotation)
            
            # Dibujar formas diferentes según el tipo de partícula
            shape_type = random.randint(0, 2)
            if shape_type == 0:  # Círculo
                painter.drawEllipse(
                    -int(particle.size/2),
                    -int(particle.size/2),
                    int(particle.size),
                    int(particle.size)
                )
            elif shape_type == 1:  # Cuadrado
                painter.drawRect(
                    -int(particle.size/2),
                    -int(particle.size/2),
                    int(particle.size),
                    int(particle.size)
                )
            else:  # Estrella
                points = []
                num_points = 5
                for i in range(num_points * 2):
                    angle = (i * math.pi) / num_points
                    r = particle.size if i % 2 == 0 else particle.size/2
                    x = math.cos(angle) * r
                    y = math.sin(angle) * r
                    points.append(QPointF(x, y))
                painter.drawPolygon(points)
            
            # Restaurar el estado del painter
            painter.restore()

class GlowEffect:
    def __init__(self, x, y, color, size=20):
        self.x = x
        self.y = y
        self.color = QColor(color)
        self.size = size
        self.alpha = 255
        self.fade_speed = 5
    
    def update(self):
        self.alpha = max(0, self.alpha - self.fade_speed)
    
    def is_alive(self):
        return self.alpha > 0
    
    def draw(self, painter):
        if not self.is_alive():
            return
        
        gradient = QRadialGradient(
            QPointF(self.x, self.y),
            self.size
        )
        
        # Color central más brillante
        glow_color = QColor(self.color)
        glow_color.setAlpha(self.alpha)
        gradient.setColorAt(0, glow_color)
        
        # Borde exterior transparente
        transparent_color = QColor(self.color)
        transparent_color.setAlpha(0)
        gradient.setColorAt(1, transparent_color)
        
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            int(self.x - self.size),
            int(self.y - self.size),
            int(self.size * 2),
            int(self.size * 2)
        )
class GameStats:
    """Sistema de estadísticas y puntuación"""
    def __init__(self):
        self.score = 0
        self.lives = 3
        self.level_start_time = time.time()
        self.total_time = 0
        self.zones_used = 0
        self.levels_completed = 0
        self.high_scores = self.load_high_scores()
    
    def reset_level(self):
        self.level_start_time = time.time()
    
    def complete_level(self):
        level_time = time.time() - self.level_start_time
        self.total_time += level_time
        
        # Puntuación por tiempo (bonus por ser rápido)
        time_bonus = max(0, 1000 - int(level_time * 10))
        self.score += time_bonus + 500  # 500 puntos base por completar nivel
        self.levels_completed += 1
    
    def use_zone(self, zone_type):
        self.zones_used += 1
        if zone_type == 'immunity':
            self.score += 50
        elif zone_type == 'invisibility':
            self.score += 75
    
    def lose_life(self):
        self.lives -= 1
        self.score = max(0, self.score - 200)  # Penalización por muerte
    
    def load_high_scores(self):
        try:
            if os.path.exists('high_scores.json'):
                with open('high_scores.json', 'r') as f:
                    return json.load(f)
        except:
            pass
        return []
    
    def save_high_score(self):
        self.high_scores.append({
            'score': self.score,
            'levels': self.levels_completed,
            'time': self.total_time,
            'zones_used': self.zones_used
        })
        self.high_scores.sort(key=lambda x: x['score'], reverse=True)
        self.high_scores = self.high_scores[:10]  # Top 10
        
        try:
            with open('high_scores.json', 'w') as f:
                json.dump(self.high_scores, f)
        except:
            pass

class GameObject:    
    def __init__(self, x, y, size, color):
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.last_position = (x, y)
    
    def draw(self, painter):
        painter.fillRect(self.x * self.size, self.y * self.size, 
                        self.size, self.size, self.color)
    
    def get_position(self):
        return (self.x, self.y)
    
    def set_position(self, x, y):
        self.last_position = self.get_position()
        self.x = x
        self.y = y

class Mouse(GameObject):
    def __init__(self, x, y, size):
        super().__init__(x, y, size, QColor(100, 150, 255))
        self.is_invisible = False
        self.is_immune = False
        self.is_fast = False
        self.immunity_timer = 0
        self.invisibility_timer = 0
        self.speed_timer = 0
        self.move_counter = 0
        self.last_zone_use = 0
    
    def draw(self, painter):
        # Efecto de velocidad
        if self.is_fast:
            painter.setBrush(QColor(255, 200, 100, 150))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                self.x * self.size - 3, 
                self.y * self.size - 3, 
                self.size + 6, 
                self.size + 6
            )
        
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
            
        if self.speed_timer > 0:
            self.speed_timer -= 1
            self.is_fast = True
        else:
            self.is_fast = False
    
    def can_move_fast(self):
        return self.is_fast and self.move_counter % 2 == 0

class Cat(GameObject):
    def __init__(self, x, y, size, path_finder, cat_type='normal', vision_range=3):
        colors = {
            'normal': QColor(255, 120, 120),
            'hunter': QColor(255, 80, 80),    # Rojo más intenso
            'speedy': QColor(255, 180, 120),   # Naranja
            'smart': QColor(180, 120, 255)     # Púrpura
        }
        super().__init__(x, y, size, colors.get(cat_type, QColor(255, 120, 120)))
        
        self.cat_type = cat_type
        self.path_finder = path_finder
        self.path = []
        self.last_update = time.time()
        
        # Configurar según tipo
        if cat_type == 'hunter':
            self.update_interval = 0.4
            self.vision_range = vision_range + 2
        elif cat_type == 'speedy':
            self.update_interval = 0.2
            self.vision_range = max(2, vision_range - 1)
        elif cat_type == 'smart':
            self.update_interval = 0.3
            self.vision_range = vision_range
        else:  # normal
            self.update_interval = 0.3
            self.vision_range = vision_range
            
        self.target_pos = None
        self.last_known_mouse_pos = None
        self.search_mode = True
        self.patrol_points = []
        self.current_patrol_target = 0
        self.stuck_counter = 0
        self.prediction_history = []  # Para gato inteligente
        self.confused_timer = 0
    
    def draw(self, painter):
        # Efecto de confusión
        if self.confused_timer > 0:
            painter.setBrush(QColor(255, 255, 0, 100))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                self.x * self.size - 5, 
                self.y * self.size - 5, 
                self.size + 10, 
                self.size + 10
            )
        
        # Dibujar el gato
        painter.setBrush(self.color)
        painter.setPen(QColor(200, 40, 40))
        painter.drawRect(
            self.x * self.size, 
            self.y * self.size, 
            self.size, 
            self.size
        )
        
        # Dibujar rango de visión (semi-transparente) solo si no está confundido
        if self.confused_timer == 0:
            painter.setBrush(QColor(255, 200, 200, 30))
            painter.setPen(Qt.NoPen)
            vision_size = (2 * self.vision_range + 1) * self.size
            vision_x = (self.x - self.vision_range) * self.size
            vision_y = (self.y - self.vision_range) * self.size
            painter.drawEllipse(vision_x, vision_y, vision_size, vision_size)
        
        # Mostrar camino si está persiguiendo
        if self.path and not self.search_mode and self.confused_timer == 0:
            painter.setPen(QColor(255, 140, 140, 100))
            for i, (x, y) in enumerate(self.path[1:]):
                alpha = max(50, 150 - i * 20)
                painter.setPen(QColor(255, 140, 140, alpha))
                painter.drawRect(
                    x * self.size + self.size // 4, 
                    y * self.size + self.size // 4, 
                    self.size // 2, 
                    self.size // 2
                )
    
    def can_see_mouse(self, mouse_pos):
        """Verifica si el gato puede ver al ratón"""
        if self.confused_timer > 0:
            return False
        distance = math.sqrt((self.x - mouse_pos[0])**2 + (self.y - mouse_pos[1])**2)
        return distance <= self.vision_range
    
    def generate_patrol_points(self, grid_width, grid_height, grid):
        """Genera puntos de patrullaje válidos (sin paredes)"""
        self.patrol_points = []
        max_attempts = 50
        
        for _ in range(4):
            attempts = 0
            while attempts < max_attempts:
                x = random.randint(1, grid_width - 2)
                y = random.randint(1, grid_height - 2)
                
                # Verificar que no sea una pared
                if grid[y][x] == 0:
                    self.patrol_points.append((x, y))
                    break
                attempts += 1
        
        # Si no se pudieron generar suficientes puntos, usar esquinas
        if len(self.patrol_points) < 2:
            corners = [(1, 1), (grid_width-2, 1), (1, grid_height-2), (grid_width-2, grid_height-2)]
            for corner in corners:
                if grid[corner[1]][corner[0]] == 0:
                    self.patrol_points.append(corner)
    
    def predict_mouse_position(self, mouse_pos, mouse_history):
        """Predicción para gato inteligente"""
        if self.cat_type != 'smart' or len(mouse_history) < 3:
            return mouse_pos
        
        # Calcular dirección promedio del ratón
        recent_moves = mouse_history[-3:]
        dx_total = sum(move['dx'] for move in recent_moves)
        dy_total = sum(move['dy'] for move in recent_moves)
        
        predicted_x = mouse_pos[0] + dx_total // 3
        predicted_y = mouse_pos[1] + dy_total // 3
        
        return (predicted_x, predicted_y)
    
    def update_path(self, grid, mouse_pos, mouse_invisible=False, mouse_history=None):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
            
        self.last_update = current_time
        
        # Actualizar confusión
        if self.confused_timer > 0:
            self.confused_timer -= 1
            # Movimiento aleatorio cuando está confundido
            if random.random() < 0.3:
                directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
                dx, dy = random.choice(directions)
                new_x = max(0, min(len(grid[0])-1, self.x + dx))
                new_y = max(0, min(len(grid)-1, self.y + dy))
                if grid[new_y][new_x] == 0:
                    self.set_position(new_x, new_y)
            return
        
        # Verificar si está atascado
        if self.get_position() == self.last_position:
            self.stuck_counter += 1
        else:
            self.stuck_counter = 0
        
        # Si está atascado, cambiar estrategia
        if self.stuck_counter > 8:
            self.search_mode = True
            self.stuck_counter = 0
            self.path = []
        
        # Si puede ver al ratón y no es invisible
        if not mouse_invisible and self.can_see_mouse(mouse_pos):
            self.search_mode = False
            self.last_known_mouse_pos = mouse_pos
            
            # Usar predicción para gato inteligente
            if self.cat_type == 'smart' and mouse_history:
                target = self.predict_mouse_position(mouse_pos, mouse_history)
                # Verificar que la predicción sea válida
                if (0 <= target[0] < len(grid[0]) and 
                    0 <= target[1] < len(grid) and 
                    grid[target[1]][target[0]] == 0):
                    self.target_pos = target
                else:
                    self.target_pos = mouse_pos
            else:
                self.target_pos = mouse_pos
                
        elif self.last_known_mouse_pos and not self.search_mode:
            # Ir a la última posición conocida
            if self.get_position() == self.last_known_mouse_pos:
                self.search_mode = True
                self.last_known_mouse_pos = None
            else:
                self.target_pos = self.last_known_mouse_pos
        else:
            # Modo búsqueda: patrullar
            self.search_mode = True
            if not self.patrol_points:
                self.generate_patrol_points(len(grid[0]), len(grid), grid)
            
            if self.patrol_points:
                current_target = self.patrol_points[self.current_patrol_target]
                if self.get_position() == current_target:
                    self.current_patrol_target = (self.current_patrol_target + 1) % len(self.patrol_points)
                    current_target = self.patrol_points[self.current_patrol_target]
                self.target_pos = current_target
        
        # Calcular camino hacia el objetivo
        if self.target_pos:
            new_path = self.path_finder.find_path(grid, self.get_position(), self.target_pos)
            if new_path:
                self.path = new_path

    def move(self, occupied_positions):
        if len(self.path) > 1: 
            next_pos = self.path[1]
            
            # Verificar colisión con otros gatos
            if next_pos not in occupied_positions:
                self.x, self.y = next_pos
                self.path = self.path[1:]
                return True
        return False
    
    def confuse(self, duration=60):
        """Confundir al gato"""
        self.confused_timer = duration
        self.path = []
        self.search_mode = True

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
    def __init__(self, x, y, size):
        super().__init__(x, y, size, QColor(80, 80, 80))

class SpecialZone(GameObject):
    def __init__(self, x, y, size, zone_type):
        self.zone_type = zone_type
        colors = {
            'immunity': QColor(255, 255, 100, 150),
            'invisibility': QColor(200, 100, 255, 150),
            'speed': QColor(100, 255, 200, 150),
            'confusion': QColor(255, 150, 100, 150),
            'teleport': QColor(255, 100, 255, 150)
        }
        super().__init__(x, y, size, colors.get(zone_type, QColor(150, 150, 150, 150)))
        self.used_recently = False
        self.cooldown = 0
    
    def draw(self, painter):
        if self.cooldown > 0:
            self.cooldown -= 1
            
        # Zona desactivada si está en cooldown
        if self.cooldown > 0:
            painter.setBrush(QColor(100, 100, 100, 100))
        else:
            painter.setBrush(self.color)
            
        painter.setPen(Qt.NoPen)
        painter.drawRect(
            self.x * self.size, 
            self.y * self.size, 
            self.size, 
            self.size
        )
        
        # Indicador del tipo de zona
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont('Arial', 8, QFont.Bold))
        text = {
            'immunity': 'I',
            'invisibility': 'V',
            'speed': 'S',
            'confusion': 'C',
            'teleport': 'T'
        }.get(self.zone_type, '?')
        
        painter.drawText(
            self.x * self.size + self.size//3,
            self.y * self.size + 2*self.size//3,
            text
        )
    
    def can_use(self):
        return self.cooldown == 0
    
    def use(self):
        self.cooldown = 90  # 15 segundos de cooldown aprox

class GameArea(QWidget):
    score_changed = pyqtSignal(int)
    lives_changed = pyqtSignal(int)
    level_changed = pyqtSignal(int)
    
    def __init__(self, parent, path_finder):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Configuración del mapa
        self.grid_size = 20
        self.grid_width = 30
        self.grid_height = 20
        
        self.grid = [[0 for _ in range(self.grid_width)] for _ in range(self.grid_height)]
        
        # Objetos del juego
        self.path_finder = path_finder
        self.mouse = Mouse(1, 1, self.grid_size)
        self.cats = []
        self.goal = Goal(self.grid_width - 2, 1, self.grid_size)
        self.walls = []
        self.special_zones = []
        
        # Sistemas adicionales
        self.particles = ParticleSystem()
        self.stats = GameStats()
        self.mouse_history = []
        
        # Configuración de niveles
        self.current_level = 1
        self.max_level = 6
        self.levels_config = {
            1: {'cats': [('normal', 1)], 'vision_range': 4, 'wall_density': 0.15, 'special_zones': 2},
            2: {'cats': [('normal', 2)], 'vision_range': 3, 'wall_density': 0.2, 'special_zones': 3},
            3: {'cats': [('normal', 1), ('hunter', 1)], 'vision_range': 4, 'wall_density': 0.25, 'special_zones': 3},
            4: {'cats': [('normal', 1), ('speedy', 1)], 'vision_range': 3, 'wall_density': 0.3, 'special_zones': 4},
            5: {'cats': [('normal', 1), ('smart', 1)], 'vision_range': 4, 'wall_density': 0.25, 'special_zones': 4},
            6: {'cats': [('normal', 1), ('hunter', 1), ('speedy', 1)], 'vision_range': 3, 'wall_density': 0.35, 'special_zones': 5}
        }
        
        # Estado del juego
        self.game_over = False
        self.game_won = False
        self.level_completed = False
        self.paused = False
        self.should_continue = True
        self.move_directions = {
            Qt.Key_Up: (0, -1),
            Qt.Key_Down: (0, 1),
            Qt.Key_Left: (-1, 0),
            Qt.Key_Right: (1, 0),
        }
        
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_game)
        self.game_timer.start(150)
        
        self.setup_level()
        
        self.setFixedSize(self.grid_width * self.grid_size, self.grid_height * self.grid_size)
    
    def setup_level(self):
        """Configura el nivel actual"""
        config = self.levels_config[self.current_level]
        
        # Limpiar objetos anteriores
        self.cats = []
        self.walls = []
        self.special_zones = []
        self.mouse_history = []
        
        # Crear gatos según el nivel
        for cat_type, count in config['cats']:
            for i in range(count):
                attempts = 0
                while attempts < 50:
                    x = random.randint(self.grid_width//2, self.grid_width - 2)
                    y = random.randint(1, self.grid_height - 2)
                    
                    # Verificar que no esté ocupado
                    occupied = False
                    if (x, y) == self.mouse.get_position() or (x, y) == self.goal.get_position():
                        occupied = True
                    for existing_cat in self.cats:
                        if (x, y) == existing_cat.get_position():
                            occupied = True
                            break
                    
                    if not occupied:
                        cat = Cat(x, y, self.grid_size, self.path_finder, cat_type, config['vision_range'])
                        self.cats.append(cat)
                        break
                    attempts += 1
        
        # Generar mapa con límite de intentos
        attempts = 0
        while attempts < 10:
            if self.generate_walls_safe(config['wall_density']):
                break
            attempts += 1
        
        self.generate_special_zones(config['special_zones'])
        
        # Reiniciar posición del ratón
        self.mouse.set_position(1, 1)
        self.mouse.immunity_timer = 0
        self.mouse.invisibility_timer = 0
        self.mouse.speed_timer = 0
        
        # Generar puntos de patrulla para cada gato
        for cat in self.cats:
            cat.generate_patrol_points(self.grid_width, self.grid_height, self.grid)
        
        # Reiniciar estadísticas del nivel
        self.stats.reset_level()
        
        # Emitir señales
        self.level_changed.emit(self.current_level)
        self.lives_changed.emit(self.stats.lives)
    
    def generate_walls_safe(self, density):
        """Genera paredes con verificación de camino válido"""
        self.walls = []
        self.grid = [[0 for _ in range(self.grid_width)] for _ in range(self.grid_height)]
        
        num_walls = int(self.grid_width * self.grid_height * density)
        
        # Posiciones reservadas
        reserved_positions = [self.mouse.get_position(), self.goal.get_position()]
        for cat in self.cats:
            reserved_positions.append(cat.get_position())
        
        walls_added = 0
        max_attempts = num_walls * 3
        attempts = 0
        
        while walls_added < num_walls and attempts < max_attempts:
            x = random.randint(0, self.grid_width - 1)
            y = random.randint(0, self.grid_height - 1)
            
            if (x, y) not in reserved_positions and self.grid[y][x] == 0:
                # Probar agregar la pared
                self.grid[y][x] = 1
                
                # Verificar que aún existe camino
                path = self.path_finder.find_path(self.grid, self.mouse.get_position(), self.goal.get_position())
                if path:
                    self.walls.append(Wall(x, y, self.grid_size))
                    walls_added += 1
                else:
                    # Revertir si no hay camino
                    self.grid[y][x] = 0
            
            attempts += 1
        
        # Verificación final
        final_path = self.path_finder.find_path(self.grid, self.mouse.get_position(), self.goal.get_position())
        return len(final_path) > 0
    
    def generate_special_zones(self, num_zones):
        """Genera zonas especiales"""
        self.special_zones = []
        zone_types = ['immunity', 'invisibility', 'speed', 'confusion']
        
        if self.current_level >= 4:
            zone_types.append('teleport')
        
        for _ in range(num_zones):
            attempts = 0
            while attempts < 50:
                x = random.randint(0, self.grid_width - 1)
                y = random.randint(0, self.grid_height - 1)
                
                # Verificar que no esté ocupada
                occupied = False
                if self.grid[y][x] == 1:  # Pared
                    occupied = True
                if (x, y) == self.mouse.get_position() or (x, y) == self.goal.get_position():
                    occupied = True
                for cat in self.cats:
                    if (x, y) == cat.get_position():
                        occupied = True
                for zone in self.special_zones:
                    if (x, y) == zone.get_position():
                        occupied = True
                
                if not occupied:
                    zone_type = random.choice(zone_types)
                    self.special_zones.append(SpecialZone(x, y, self.grid_size, zone_type))
                    break
                
                attempts += 1
    
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
        
        # Dibujar partículas
        self.particles.draw(painter, self.grid_size)
        
        # HUD mejorado
        if not (self.game_over or self.game_won or self.level_completed):
            # Barra de vidas
            painter.setPen(Qt.NoPen)
            for i in range(self.stats.lives):
                painter.setBrush(QColor(255, 100, 100))
                painter.drawEllipse(10 + i * 25, 10, 20, 20)
            
            # Puntuación
            painter.setPen(QColor(50, 50, 50))
            painter.setFont(QFont('Arial', 12, QFont.Bold))
            painter.drawText(10, 50, f"Score: {self.stats.score}")
            
            # Temporizadores de efectos
            if self.mouse.immunity_timer > 0:
                painter.setBrush(QColor(255, 255, 100, 200))
                width = (self.mouse.immunity_timer / 30) * 100
                painter.drawRect(10, 60, width, 10)
            
            if self.mouse.invisibility_timer > 0:
                painter.setBrush(QColor(200, 100, 255, 200))
                width = (self.mouse.invisibility_timer / 30) * 100
                painter.drawRect(10, 75, width, 10)
            
            if self.mouse.speed_timer > 0:
                painter.setBrush(QColor(100, 255, 200, 200))
                width = (self.mouse.speed_timer / 30) * 100
                painter.drawRect(10, 90, width, 10)
        
        # Interfaz de juego para estados especiales
        if self.game_over or self.game_won or self.level_completed:
            painter.fillRect(0, 0, self.width(), self.height(), QColor(0, 0, 0, 150))
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont('Arial', 20, QFont.Bold))
            
            if self.level_completed:
                if self.current_level >= self.max_level:
                    message = f"¡JUEGO COMPLETADO!\nPuntuación final: {self.stats.score}"
                else:
                    message = f"¡NIVEL {self.current_level} COMPLETADO!\nPuntuación: {self.stats.score}"
            else:
                message = "¡GANASTE!" if self.game_won else "¡PERDISTE!"
            
            rect = QRect(0, 0, self.width(), self.height())
            painter.drawText(rect, Qt.AlignCenter, message)
    
    def update_game(self):
        """Actualización principal del juego con optimizaciones"""
        if self.game_over or self.game_won or self.paused:
            return
        
        # Ask if should continue every 30 moves
        if self.mouse.move_counter > 0 and self.mouse.move_counter % 30 == 0:
            self.pause_and_ask_continue()
            return

        # Actualizar ratón y efectos
        self.mouse.update()
        self.particles.update()
        
        # Actualizar historial de movimientos del ratón
        if len(self.mouse_history) > 10:
            self.mouse_history.pop(0)
        
        # Verificar zonas especiales
        mouse_pos = self.mouse.get_position()
        for zone in self.special_zones:
            if mouse_pos == zone.get_position() and zone.can_use():
                self.activate_special_zone(zone)
        
        # Obtener posiciones ocupadas por gatos para evitar colisiones
        occupied_positions = set()
        for cat in self.cats:
            occupied_positions.add(cat.get_position())
        
        # Actualizar gatos con optimizaciones
        current_time = time.time()
        for cat in self.cats:
            if current_time - cat.last_update >= cat.update_interval:
                cat.update_path(self.grid, mouse_pos, self.mouse.is_invisible, self.mouse_history)
                # Solo mover si no hay colisión con otros gatos
                cat.move(occupied_positions)
                
                # Verificar captura (solo si el ratón no es inmune)
                if cat.get_position() == mouse_pos and not self.mouse.is_immune:
                    self.on_mouse_caught()
                    return
        
        # Verificar victoria
        if mouse_pos == self.goal.get_position():
            self.on_level_complete()
        
        # Emitir señales
        self.score_changed.emit(self.stats.score)
        self.lives_changed.emit(self.stats.lives)
        self.level_changed.emit(self.current_level)
        
        self.update()
    
    def pause_and_ask_continue(self):
        self.paused = True
        reply = QMessageBox.question(self, 'Continuar', 
                                   '¿Desea continuar iterando?',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.paused = False
        else:
            self.game_over = True
            self.game_timer.stop()

    def activate_special_zone(self, zone):
        """Activar efectos de zona especial"""
        if zone.cooldown > 0:
            return
            
        zone.use()
        self.stats.use_zone(zone.zone_type)
        
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
    
    def on_mouse_caught(self):
        """Manejo de captura del ratón"""
        self.stats.lose_life()
        
        if self.stats.lives <= 0:
            self.game_over = True
            self.game_timer.stop()
            self.stats.save_high_score()
        else:
            # Reiniciar posiciones pero mantener el nivel
            self.mouse.set_position(1, 1)
            self.mouse.immunity_timer = 30  # Inmunidad temporal al reaparecer
            
            # Aleatorizar posiciones de los gatos
            for cat in self.cats:
                attempts = 0
                while attempts < 50:
                    x = random.randint(self.grid_width//2, self.grid_width - 2)
                    y = random.randint(1, self.grid_height - 2)
                    if self.grid[y][x] == 0:
                        cat.set_position(x, y)
                        break
                    attempts += 1
        
        # Emitir señal de vidas
        self.lives_changed.emit(self.stats.lives)

    def on_level_complete(self):
        """Manejo de completar un nivel"""
        self.level_completed = True
        self.game_timer.stop()
        self.stats.complete_level()
        
        if self.current_level >= self.max_level:
            self.game_won = True
            self.stats.save_high_score()
        
        # Emitir señal de nivel
        self.level_changed.emit(self.current_level)