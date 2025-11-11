from flask import Flask, render_template, jsonify, request
import sqlite3
import threading
import time
from datetime import datetime, timedelta
import subprocess
import pandas as pd
import json
import os

app = Flask(__name__)

DB_FILE = "internet.db"
MEASURE_INTERVAL = 60  # segundos (5 minutos)

# === Banco de dados ===
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ping_avg REAL,
            download_mbps REAL,
            upload_mbps REAL
        )
    """)
    conn.commit()
    conn.close()
    print("[INFO] Banco de dados inicializado:", DB_FILE)

# === Executa o speedtest oficial ===
def executar_speedtest():
    """Executa o speedtest oficial da Ookla e retorna ping, download e upload em Mbps."""
    try:
        result = subprocess.run(
            ["speedtest", "--accept-license", "--accept-gdpr", "-f", "json"],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            print(f"[ERRO] Speedtest falhou: {result.stderr.strip()}")
            return None, None, None

        data = json.loads(result.stdout)

        ping = data["ping"]["latency"]
        download = data["download"]["bandwidth"] * 8 / 1e6  # bits/s → Mbps
        upload = data["upload"]["bandwidth"] * 8 / 1e6

        return ping, download, upload

    except FileNotFoundError:
        print("[ERRO] O executável 'speedtest' não foi encontrado.")
        print("Instale com:")
        print("  curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash")
        print("  sudo apt install speedtest -y")
    except json.JSONDecodeError as e:
        print(f"[ERRO EXECUTAR_SPEEDTEST] Erro ao interpretar JSON: {e}")
        print("Saída recebida:", result.stdout[:200], "...")
    except Exception as e:
        print(f"[ERRO EXECUTAR_SPEEDTEST] {e}")

    return None, None, None

# === Coletor de dados (usando Ookla) ===
def collect_metrics():
    while True:
        try:
            print("[INFO] Executando speedtest oficial...")
            ping, download, upload = executar_speedtest()

            if ping and download and upload:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO metrics (timestamp, ping_avg, download_mbps, upload_mbps) VALUES (?, ?, ?, ?)",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ping, download, upload)
                )
                conn.commit()
                conn.close()
                print(f"[OK] Registro salvo: ping={ping:.2f} ms | ↓ {download:.2f} Mbps | ↑ {upload:.2f} Mbps")
            else:
                print("[WARN] Speedtest retornou dados incompletos.")

        except Exception as e:
            print(f"[ERRO COLETA] {e}")

        time.sleep(MEASURE_INTERVAL)

# === Rota principal ===
@app.route("/")
def index():
    return render_template("index.html")

# === API de dados para o dashboard ===
@app.route("/data")
def data():
    time_range = request.args.get("range", "1h")
    now = datetime.now()

    ranges = {
        "1h": now - timedelta(hours=1),
        "4h": now - timedelta(hours=4),
        "12h": now - timedelta(hours=12),
        "1d": now - timedelta(days=1),
        "7d": now - timedelta(days=7),
        "total": datetime(1970, 1, 1)
    }
    start_time = ranges.get(time_range, ranges["1h"])

    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT * FROM metrics WHERE timestamp >= ? ORDER BY timestamp ASC",
        conn,
        params=(start_time.strftime("%Y-%m-%d %H:%M:%S"),)
    )
    conn.close()

    if df.empty:
        return jsonify({"timestamps": [], "ping": [], "download": [], "upload": []})

    return jsonify({
        "timestamps": df["timestamp"].tolist(),
        "ping": df["ping_avg"].tolist(),
        "download": df["download_mbps"].tolist(),
        "upload": df["upload_mbps"].tolist()
    })

# === Inicialização ===
if __name__ == "__main__":
    init_db()

    # Inicia coleta em background
    collector_thread = threading.Thread(target=collect_metrics, daemon=True)
    collector_thread.start()

    print("[INFO] Servidor Flask iniciado em http://0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080, debug=False)
