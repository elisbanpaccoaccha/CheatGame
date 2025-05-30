#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CheatGame Enhanced - Un juego con múltiples niveles donde gatos con visión limitada
deben encontrar y atrapar a un ratón que puede usar zonas especiales.
"""

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QDialog, QCheckBox,
                           QSlider, QComboBox, QGraphicsDropShadowEffect,
                           QTableWidget, QTableWidgetItem, QStackedWidget)
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtCore import Qt, QSize

from enhanced_game_window import GameWindow
from AStar import BuscadorAEstrella
import json
import os

class MainMenu(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        # Layout principal con margen y espaciado
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Título con estilo mejorado
        title = QLabel("CheatGame")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 48, QFont.Bold))
        title.setStyleSheet("color: #2196F3; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Subtítulo
        subtitle = QLabel("Gato vs Ratón")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setFont(QFont('Arial', 24))
        subtitle.setStyleSheet("color: #757575; margin-bottom: 40px;")
        layout.addWidget(subtitle)
        
        # Panel de dificultad con estilo
        difficulty_panel = QWidget()
        difficulty_panel.setStyleSheet("""
            QWidget {
                background-color: #424242;
                border-radius: 10px;
                padding: 20px;
            }
            QLabel {
                color: white;
                font-size: 16px;
            }
            QComboBox {
                background-color: #616161;
                color: white;
                padding: 8px;
                border: none;
                border-radius: 5px;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
        """)
        
        difficulty_layout = QHBoxLayout(difficulty_panel)
        difficulty_label = QLabel("Dificultad:")
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["Fácil", "Normal", "Difícil"])
        difficulty_layout.addWidget(difficulty_label)
        difficulty_layout.addWidget(self.difficulty_combo)
        layout.addWidget(difficulty_panel)
        
        # Botones con estilo mejorado
        buttons_style = """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 15px;
                font-size: 16px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """
        
        start_button = QPushButton("Iniciar Juego")
        start_button.setStyleSheet(buttons_style)
        start_button.clicked.connect(lambda: self.parent().parent().start_game())
        layout.addWidget(start_button)
        
        high_scores_button = QPushButton("Mejores Puntajes")
        high_scores_button.setStyleSheet(buttons_style)
        high_scores_button.clicked.connect(lambda: self.parent().parent().show_high_scores())
        layout.addWidget(high_scores_button)
        
        tutorial_button = QPushButton("Tutorial")
        tutorial_button.setStyleSheet(buttons_style)
        tutorial_button.clicked.connect(lambda: self.parent().parent().show_tutorial())
        layout.addWidget(tutorial_button)
        
        quit_button = QPushButton("Salir")
        quit_button.setStyleSheet(buttons_style.replace("#2196F3", "#F44336"))  # Botón rojo para salir
        quit_button.clicked.connect(lambda: self.parent().parent().close())
        layout.addWidget(quit_button)
        
        self.setLayout(layout)

class HighScoresWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Título con estilo
        title = QLabel("Mejores Puntajes")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 32, QFont.Bold))
        title.setStyleSheet("color: #2196F3; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Tabla con estilo
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Puntaje', 'Niveles', 'Tiempo', 'Zonas'])
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #424242;
                border: none;
                border-radius: 10px;
                gridline-color: #616161;
            }
            QTableWidget::item {
                color: white;
                padding: 10px;
            }
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 10px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #1976D2;
            }
        """)
        self.load_scores()
        layout.addWidget(self.table)
        
        # Botón volver con estilo
        back_button = QPushButton("Volver al Menú")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 15px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        back_button.clicked.connect(lambda: self.parent().parent().show_menu())
        layout.addWidget(back_button)
        
        self.setLayout(layout)
    
    def load_scores(self):
        try:
            if os.path.exists('high_scores.json'):
                with open('high_scores.json', 'r') as f:
                    scores = json.load(f)
                    self.table.setRowCount(len(scores))
                    for i, score in enumerate(scores):
                        # Puntuación con formato
                        score_item = QTableWidgetItem(f"{score['score']:,}")
                        score_item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(i, 0, score_item)
                        
                        # Niveles completados
                        levels_item = QTableWidgetItem(str(score['levels']))
                        levels_item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(i, 1, levels_item)
                        
                        # Tiempo con formato mm:ss
                        time_str = f"{int(score['time'])//60}:{int(score['time'])%60:02d}"
                        time_item = QTableWidgetItem(time_str)
                        time_item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(i, 2, time_item)
                        
                        # Zonas utilizadas
                        zones_item = QTableWidgetItem(str(score['zones_used']))
                        zones_item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(i, 3, zones_item)
                        
                        # Colorear filas alternadas
                        for col in range(4):
                            item = self.table.item(i, col)
                            if i % 2 == 0:
                                item.setBackground(QColor(66, 66, 66))
                            else:
                                item.setBackground(QColor(77, 77, 77))
        except:
            self.table.setRowCount(0)

class TutorialWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Título con estilo
        title = QLabel("Tutorial")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 32, QFont.Bold))
        title.setStyleSheet("color: #2196F3; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Panel de instrucciones con estilo
        instructions_panel = QWidget()
        instructions_panel.setStyleSheet("""
            QWidget {
                background-color: #424242;
                border-radius: 10px;
                padding: 20px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
        
        instructions_layout = QVBoxLayout(instructions_panel)
        
        sections = [
            ("Objetivo", ["Llegar a la meta verde evitando los gatos"], "#4CAF50"),
            ("Controles", [
                "Flechas: Mover el ratón",
                "R: Reiniciar nivel",
                "ESPACIO: Siguiente nivel",
                "P: Pausar juego"
            ], "#2196F3"),
            ("Zonas Especiales", [
                "I (Amarillo): Inmunidad temporal",
                "V (Púrpura): Invisibilidad temporal",
                "S (Verde): Velocidad aumentada",
                "C (Naranja): Confunde a los gatos cercanos",
                "T (Rosa): Teletransporte aleatorio"
            ], "#9C27B0"),
            ("Tipos de Gatos", [
                "Normal (Rojo): Comportamiento básico",
                "Hunter (Rojo oscuro): Mayor rango de visión",
                "Speedy (Naranja): Más rápido pero menos visión",
                "Smart (Púrpura): Predice tus movimientos"
            ], "#F44336")
        ]
        
        for title, items, color in sections:
            section_title = QLabel(title)
            section_title.setFont(QFont('Arial', 16, QFont.Bold))
            section_title.setStyleSheet(f"color: {color};")
            instructions_layout.addWidget(section_title)
            
            for item in items:
                item_label = QLabel(f"• {item}")
                item_label.setWordWrap(True)
                instructions_layout.addWidget(item_label)
            
            instructions_layout.addSpacing(10)
        
        layout.addWidget(instructions_panel)
        
        # Botón volver con estilo
        back_button = QPushButton("Volver al Menú")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 15px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        back_button.clicked.connect(lambda: self.parent().parent().show_menu())
        layout.addWidget(back_button)
        
        self.setLayout(layout)

class GameUI(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Panel principal con fondo y sombra
        main_panel = QWidget()
        main_panel.setStyleSheet("""
            QWidget {
                background-color: #2C2C2C;
                border-radius: 15px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 0)
        main_panel.setGraphicsEffect(shadow)
        
        panel_layout = QVBoxLayout(main_panel)
        panel_layout.setSpacing(30)
        
        # Título con estilo
        title = QLabel("CheatGame")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 48, QFont.Bold))
        title.setStyleSheet("""
            color: #4CAF50;
            margin: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        """)
        panel_layout.addWidget(title)
        
        # Subtítulo
        subtitle = QLabel("Gato vs Ratón")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setFont(QFont('Arial', 24))
        subtitle.setStyleSheet("color: #78909C;")
        panel_layout.addWidget(subtitle)
        
        # Panel de controles con estilo
        controls_panel = QWidget()
        controls_panel.setStyleSheet("""
            QWidget {
                background-color: #353535;
                border-radius: 10px;
                padding: 20px;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
            }
        """)
        
        controls_layout = QVBoxLayout(controls_panel)
        
        # Botones con efecto hover
        button_style = """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 15px;
                font-size: 18px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
                transform: scale(1.05);
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """
        
        start_button = QPushButton("Jugar")
        start_button.setStyleSheet(button_style)
        start_button.clicked.connect(self.start_game)
        controls_layout.addWidget(start_button)
        
        settings_button = QPushButton("Configuración")
        settings_button.setStyleSheet(button_style.replace("#4CAF50", "#2196F3"))
        settings_button.clicked.connect(self.show_settings)
        controls_layout.addWidget(settings_button)
        
        help_button = QPushButton("Ayuda")
        help_button.setStyleSheet(button_style.replace("#4CAF50", "#FF9800"))
        help_button.clicked.connect(self.show_help)
        controls_layout.addWidget(help_button)
        
        quit_button = QPushButton("Salir")
        quit_button.setStyleSheet(button_style.replace("#4CAF50", "#f44336"))
        quit_button.clicked.connect(self.close)
        controls_layout.addWidget(quit_button)
        
        panel_layout.addWidget(controls_panel)
        
        # Información del juego
        info_label = QLabel("Usa las flechas para mover el ratón y evita los gatos!")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("color: #9E9E9E; font-size: 14px;")
        panel_layout.addWidget(info_label)
        
        layout.addWidget(main_panel)
        self.setLayout(layout)
        
        # Establecer tema oscuro para toda la aplicación
        self.setStyleSheet("""
            QWidget {
                background-color: #212121;
                color: #FFFFFF;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)
    
    def start_game(self):
        from AStar import AStarPathFinder
        self.game_window = GameWindow(AStarPathFinder())
        self.game_window.show()
    
    def show_settings(self):
        settings = SettingsDialog(self)
        settings.exec_()
    
    def show_help(self):
        help_dialog = HelpDialog(self)
        help_dialog.exec_()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('Configuración')
        self.setStyleSheet("""
            QDialog {
                background-color: #2C2C2C;
                border-radius: 10px;
            }
            QLabel {
                color: white;
                font-size: 16px;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                border-radius: 7px;
            }
            QSlider::groove:horizontal {
                background: #424242;
                height: 8px;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Dificultad
        difficulty_layout = QHBoxLayout()
        difficulty_label = QLabel("Dificultad:")
        self.difficulty_slider = QSlider(Qt.Horizontal)
        self.difficulty_slider.setMinimum(1)
        self.difficulty_slider.setMaximum(3)
        self.difficulty_slider.setValue(2)
        difficulty_layout.addWidget(difficulty_label)
        difficulty_layout.addWidget(self.difficulty_slider)
        layout.addLayout(difficulty_layout)
        
        # Efectos de sonido
        sound_layout = QHBoxLayout()
        sound_label = QLabel("Efectos de sonido:")
        self.sound_checkbox = QCheckBox()
        self.sound_checkbox.setChecked(True)
        sound_layout.addWidget(sound_label)
        sound_layout.addWidget(self.sound_checkbox)
        layout.addLayout(sound_layout)
        
        # Tamaño del mapa
        map_size_layout = QHBoxLayout()
        map_size_label = QLabel("Tamaño del mapa:")
        self.map_size_combo = QComboBox()
        self.map_size_combo.addItems(["Pequeño", "Medio", "Grande"])
        self.map_size_combo.setCurrentText("Medio")
        map_size_layout.addWidget(map_size_label)
        map_size_layout.addWidget(self.map_size_combo)
        layout.addLayout(map_size_layout)
        
        # Botones
        button_layout = QHBoxLayout()
        save_button = QPushButton("Guardar")
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_button.clicked.connect(self.accept)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('Ayuda')
        self.setStyleSheet("""
            QDialog {
                background-color: #2C2C2C;
                border-radius: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                line-height: 1.5;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Título
        title = QLabel("Cómo Jugar")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        title.setStyleSheet("color: #4CAF50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Instrucciones
        instructions = [
            ("Objetivo", "Llega a la meta verde evitando los gatos"),
            ("Controles", [
                "⬆️ Flecha arriba: Mover arriba",
                "⬇️ Flecha abajo: Mover abajo",
                "⬅️ Flecha izquierda: Mover izquierda",
                "➡️ Flecha derecha: Mover derecha",
                "R: Reiniciar nivel",
                "P: Pausar juego"
            ]),
            ("Power-ups", [
                "🟡 Amarillo: Inmunidad temporal",
                "🟣 Púrpura: Invisibilidad temporal",
                "🟢 Verde: Velocidad aumentada"
            ]),
            ("Consejos", [
                "Mantén distancia con los gatos",
                "Usa los power-ups estratégicamente",
                "Planea tu ruta con anticipación"
            ])
        ]
        
        for section_title, content in instructions:
            section_label = QLabel(section_title)
            section_label.setFont(QFont('Arial', 16, QFont.Bold))
            section_label.setStyleSheet("color: #2196F3; margin-top: 10px;")
            layout.addWidget(section_label)
            
            if isinstance(content, str):
                item_label = QLabel(content)
                layout.addWidget(item_label)
            else:
                for item in content:
                    item_label = QLabel(f"• {item}")
                    layout.addWidget(item_label)
        
        # Botón cerrar
        close_button = QPushButton("Entendido")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                min-width: 100px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('CheatGame Enhanced')
        self.setMinimumSize(QSize(600, 400))
        
        # Widget central con stacked layout
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        
        # Crear widgets
        self.menu = MainMenu(self.central_widget)
        self.high_scores = HighScoresWidget(self.central_widget)
        self.tutorial = TutorialWidget(self.central_widget)
        
        # Agregar widgets al stacked layout
        self.central_widget.addWidget(self.menu)
        self.central_widget.addWidget(self.high_scores)
        self.central_widget.addWidget(self.tutorial)
        
        self.show_menu()
        self.center()
    
    def show_menu(self):
        self.central_widget.setCurrentWidget(self.menu)
    
    def show_high_scores(self):
        self.high_scores.load_scores()  # Recargar puntajes
        self.central_widget.setCurrentWidget(self.high_scores)
    
    def show_tutorial(self):
        self.central_widget.setCurrentWidget(self.tutorial)
    
    def start_game(self):
        difficulty = self.menu.difficulty_combo.currentText()
        path_finder = BuscadorAEstrella()  # Usar la clase correcta
        
        # Configurar dificultad
        if difficulty == "Fácil":
            GameWindow.DIFFICULTY_MULTIPLIER = 0.8  # Gatos más lentos
        elif difficulty == "Difícil":
            GameWindow.DIFFICULTY_MULTIPLIER = 1.2  # Gatos más rápidos
        else:
            GameWindow.DIFFICULTY_MULTIPLIER = 1.0
        
        self.game_window = GameWindow(path_finder)
        self.game_window.show()
    
    def center(self):
        frame_geometry = self.frameGeometry()
        screen_center = self.screen().availableGeometry().center()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())

def main():
    app = QApplication(sys.argv)
    
    # Aplicar estilo moderno
    app.setStyle('Fusion')
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()