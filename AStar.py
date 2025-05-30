#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Implementación del algoritmo A*
"""

import heapq
import math

class BuscadorAEstrella:
    """Implementa el algoritmo A* para encontrar el camino más corto"""

    def __init__(self):
        """Constructor de la clase"""
        self.nodos_abiertos = []
        self.nodos_cerrados = set()
        self.direcciones = [(0, 1), (1, 0), (0, -1), (-1, 0), 
                           (1, 1), (-1, -1), (1, -1), (-1, 1)]  # Añadir movimientos diagonales

    def distancia_manhattan(self, pos1, pos2):
        """Calcula la distancia Manhattan entre dos posiciones"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def obtener_vecinos(self, pos, matriz):
        """Obtiene los nodos vecinos válidos de una posición"""
        vecinos = []
        height = len(matriz)
        width = len(matriz[0])
        
        for dx, dy in self.direcciones:
            nuevo_x = pos[0] + dx
            nuevo_y = pos[1] + dy
            
            # Verificar límites del mapa
            if (0 <= nuevo_x < width and 
                0 <= nuevo_y < height):
                # Verificar que no hay pared
                if matriz[nuevo_y][nuevo_x] != 1:
                    # Para movimientos diagonales, verificar que no hay paredes adyacentes
                    if abs(dx) == 1 and abs(dy) == 1:
                        if matriz[pos[1]][nuevo_x] != 1 and matriz[nuevo_y][pos[0]] != 1:
                            vecinos.append((nuevo_x, nuevo_y))
                    else:
                        vecinos.append((nuevo_x, nuevo_y))
        return vecinos

    def encontrar_camino(self, inicio, objetivo, matriz):
        """Encuentra el camino más corto entre dos puntos usando A*"""
        if not matriz or not matriz[0]:
            return None
            
        # Verificar que inicio y objetivo son válidos
        height = len(matriz)
        width = len(matriz[0])
        if not (0 <= inicio[0] < width and 0 <= inicio[1] < height and
                0 <= objetivo[0] < width and 0 <= objetivo[1] < height):
            return None
            
        # Si el inicio o el objetivo están en una pared, no hay camino
        if matriz[inicio[1]][inicio[0]] == 1 or matriz[objetivo[1]][objetivo[0]] == 1:
            return None

        # Reiniciar estructuras de datos
        self.nodos_abiertos = []
        self.nodos_cerrados = set()
        
        # Crear nodo inicial
        heapq.heappush(self.nodos_abiertos, (0, inicio, []))
        costo_g = {inicio: 0}

        while self.nodos_abiertos:
            f_actual, pos_actual, camino = heapq.heappop(self.nodos_abiertos)
            
            if pos_actual == objetivo:
                return camino + [pos_actual]

            if pos_actual in self.nodos_cerrados:
                continue

            self.nodos_cerrados.add(pos_actual)

            for vecino in self.obtener_vecinos(pos_actual, matriz):
                if vecino in self.nodos_cerrados:
                    continue

                # Calcular costo g (costo real desde el inicio)
                g_nuevo = costo_g[pos_actual] + (1.4 if abs(vecino[0] - pos_actual[0]) + abs(vecino[1] - pos_actual[1]) == 2 else 1.0)
                
                if vecino not in costo_g or g_nuevo < costo_g[vecino]:
                    costo_g[vecino] = g_nuevo
                    h = self.distancia_manhattan(vecino, objetivo)
                    f = g_nuevo + h
                    heapq.heappush(self.nodos_abiertos, (f, vecino, camino + [pos_actual]))

        return None

    def find_path(self, matriz, inicio, objetivo):
        """Alias para encontrar_camino para mantener consistencia de interfaz"""
        camino = self.encontrar_camino(inicio, objetivo, matriz)
        if not camino:
            # Si no encuentra camino, intentar encontrar un punto intermedio
            return self.encontrar_camino_alternativo(inicio, objetivo, matriz)
        return camino

    def encontrar_camino_alternativo(self, inicio, objetivo, matriz):
        """Intenta encontrar un camino alternativo cuando no hay ruta directa"""
        # Buscar puntos intermedios posibles
        height = len(matriz)
        width = len(matriz[0])
        puntos_intermedios = []
        
        # Buscar espacios libres cercanos al objetivo
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                x = objetivo[0] + dx
                y = objetivo[1] + dy
                if (0 <= x < width and 0 <= y < height and 
                    matriz[y][x] != 1):
                    puntos_intermedios.append((x, y))
        
        # Intentar encontrar un camino a través de cada punto intermedio
        mejor_camino = None
        menor_distancia = float('inf')
        
        for punto in puntos_intermedios:
            camino1 = self.encontrar_camino(inicio, punto, matriz)
            if camino1:
                camino2 = self.encontrar_camino(punto, objetivo, matriz)
                if camino2:
                    camino_total = camino1[:-1] + camino2
                    distancia = len(camino_total)
                    if distancia < menor_distancia:
                        menor_distancia = distancia
                        mejor_camino = camino_total
        
        return mejor_camino

