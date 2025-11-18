#!/bin/bash
# Script para parar o display OLED

if [ -f oled.pid ]; then
    PID=$(cat oled.pid)
    echo "🛑 Parando OLED Monitor (PID: $PID)..."
    kill $PID 2>/dev/null
    rm oled.pid
    echo "✅ OLED Monitor parado!"
else
    echo "⚠️  Nenhum processo OLED encontrado"
    # Tentar parar pelo nome
    pkill -f oled_display.py
fi
