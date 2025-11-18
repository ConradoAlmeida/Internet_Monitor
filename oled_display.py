#!/usr/bin/env python3
"""
Interface OLED 0.96" (128x64) para monitoramento de Internet
Suporta displays SSD1306 via I2C
Versão Simplificada - Mostra apenas médias das últimas 4h
"""

import time
import sqlite3
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import board
import busio
from adafruit_ssd1306 import SSD1306_I2C
import RPi.GPIO as GPIO
import json
import os
import socket

# Configurações do display
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64

# Configurações dos botões GPIO
BUTTON_PAUSE = 23   # GPIO23 - Botão PAUSE/RESUME

class OLEDMonitor:
    def __init__(self):
        """Inicializa o display OLED e configura GPIO."""
        # Configurar I2C
        i2c = busio.I2C(board.SCL, board.SDA)
        self.display = SSD1306_I2C(DISPLAY_WIDTH, DISPLAY_HEIGHT, i2c)
        
        # Limpar display
        self.display.fill(0)
        self.display.show()
        
        # Configurar GPIO apenas para botão PAUSE
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PAUSE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Estado
        self.paused = False
        self.last_button_time = 0
        self.debounce_time = 0.3  # 300ms debounce
        
        # Font
     
        self.font_small = ImageFont.truetype('/home/rubens/.fonts/DejaVuSans.ttf', 8)
        self.font_medium = ImageFont.truetype('/home/rubens/.fonts/DejaVuSans.ttf', 10)
        self.font_large = ImageFont.truetype('/home/rubens/.fonts/DejaVuSans.ttf', 12)

    
    def get_local_ip(self):
        """Obtém o IP local do servidor."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "N/A"
    
    def get_avg_stats_4h(self):
        """Obtém médias das últimas 4 horas do banco de dados."""
        try:
            conn = sqlite3.connect('internet.db')
            cursor = conn.cursor()
            
            # Timestamp de 4 horas atrás
            four_hours_ago = (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Query para obter médias
            cursor.execute("""
                SELECT 
                    AVG(ping_avg) as avg_ping,
                    AVG(download_mbps) as avg_down,
                    AVG(upload_mbps) as avg_up,
                    AVG(jitter) as avg_jitter,
                    COUNT(*) as count
                FROM metrics
                WHERE timestamp >= ?
            """, (four_hours_ago,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] is not None and row[4] > 0:
                return {
                    'ping': row[0],
                    'download': row[1],
                    'upload': row[2],
                    'jitter': row[3],
                    'count': row[4]
                }
            return None
        except Exception as e:
            print(f"[ERRO] Falha ao obter stats: {e}")
            return None
    
    def draw_main_screen(self, draw):
        """Desenha tela principal com médias das últimas 4h."""
        stats = self.get_avg_stats_4h()
        ip = self.get_local_ip()
        # Porta (usa var de ambiente ou padrão 8080)
        port = os.getenv("INTERNET_MONITOR_PORT") or os.getenv("FLASK_RUN_PORT") or "8080"
        
        # Título somente ip:porta
        draw.text((0, 0), f"{ip}:{port}", font=self.font_large, fill=255)
        
        # Linha separadora
        draw.line([(0, 13), (128, 13)], fill=255)
        
        if not stats:
            draw.text((20, 28), "Sem dados", font=self.font_medium, fill=255)
            if self.paused:
                draw.text((35, 55), "PAUSADO", font=self.font_medium, fill=255)
            return
        
        # Formatar valores como inteiros
        down_text = str(int(stats['download'])) if stats['download'] else "0"
        up_text = str(int(stats['upload'])) if stats['upload'] else "0"
        jitter_text = str(int(stats['jitter'])) if stats['jitter'] else "0"
        ping_text = str(int(stats['ping'])) if stats['ping'] else "0"
        
        # Posições da tabela 2x2
        col1_x = 0      # Coluna esquerda
        col2_x = 64     # Coluna direita (meio da tela)
        row1_y = 20     # Primeira linha
        row2_y = 35     # Segunda linha
        
        # Desenhar tabela 2x2
        draw.text((col1_x, row1_y), f"D:{down_text}", font=self.font_large, fill=255)
        draw.text((col2_x, row1_y), f"U:{up_text}", font=self.font_large, fill=255)
        draw.text((col1_x, row2_y), f"J:{jitter_text}", font=self.font_large, fill=255)
        draw.text((col2_x, row2_y), f"L:{ping_text}", font=self.font_large, fill=255)
        
        # Rodapé: Média de quantas amostras e status
        # draw.line([(0, 54), (128, 54)], fill=255)
        footer_text = f"Med.4h ({stats['count']} tests)"
        if self.paused:
            footer_text = "PAUSADO"
        draw.text((0, 50), footer_text, font=self.font_medium, fill=255)
    
    def handle_button_pause(self):
        """Trata pressionamento do botão PAUSE."""
        current_time = time.time()
        if current_time - self.last_button_time < self.debounce_time:
            return
        self.last_button_time = current_time
        
        # Alternar pausa
        self.paused = not self.paused
        
        # Salvar estado de pausa em arquivo para comunicação com app.py
        try:
            with open('oled_pause_state.txt', 'w') as f:
                f.write('1' if self.paused else '0')
        except:
            pass
        
        print(f"[OLED] Monitor {'PAUSADO' if self.paused else 'RETOMADO'}")
    
    def update_display(self):
        """Atualiza o display com a tela principal."""
        # Criar imagem
        image = Image.new("1", (DISPLAY_WIDTH, DISPLAY_HEIGHT))
        draw = ImageDraw.Draw(image)
        
        # Desenhar tela principal
        self.draw_main_screen(draw)
        
        # Atualizar display
        self.display.image(image)
        self.display.show()
    
    def run(self):
        """Loop principal."""
        print("[INFO] OLED Monitor iniciado!")
        print("[INFO] Versão simplificada - Mostra médias das últimas 4h")
        print("[INFO] Botão PAUSE: GPIO23")
        
        try:
            while True:
                # Verificar botão PAUSE
                if GPIO.input(BUTTON_PAUSE) == GPIO.LOW:
                    self.handle_button_pause()
                
                # Atualizar display
                self.update_display()
                
                # Aguardar um pouco
                time.sleep(0.5)  # Atualiza a cada 0.5s
                
        except KeyboardInterrupt:
            print("\n[INFO] Encerrando OLED Monitor...")
        finally:
            # Limpar
            self.display.fill(0)
            self.display.show()
            GPIO.cleanup()

if __name__ == "__main__":
    monitor = OLEDMonitor()
    monitor.run()
