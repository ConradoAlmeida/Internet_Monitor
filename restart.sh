#!/bin/bash

echo "🔄 Parando aplicação Internet Monitor..."
pkill -f "python.*app.py" || echo "Nenhum processo encontrado"

sleep 2

echo "🚀 Iniciando aplicação Internet Monitor..."
cd /home/rubens/Internet_Monitor
nohup python3 -u app.py > monitor.log 2>&1 &

sleep 2

echo "✅ Aplicação reiniciada!"
echo "📋 Para ver os logs: tail -f /home/rubens/Internet_Monitor/monitor.log"
echo "🌐 Acesse: http://localhost:8080"
