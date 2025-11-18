#!/bin/bash
# Script para iniciar o display OLED

echo "🖥️  Iniciando OLED Monitor..."

# Verificar se as dependências estão instaladas
if ! python3 -c "import adafruit_ssd1306" 2>/dev/null; then
    echo "⚠️  Instalando dependências do OLED..."
    pip3 install -r requirements_oled.txt
fi

# Iniciar display em background
python3 -u oled_display.py >> oled.log 2>&1 &
OLED_PID=$!

echo "✅ OLED Monitor iniciado (PID: $OLED_PID)"
echo "📋 Para ver os logs: tail -f oled.log"
echo "🛑 Para parar: kill $OLED_PID"

# Salvar PID
echo $OLED_PID > oled.pid
