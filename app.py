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
CONFIG_FILE = "config.json"

# Configurações padrão
DEFAULT_CONFIG = {
    "measure_interval": 3600,  # 1 hora em segundos
    "monitor_start_hour": 6,
    "monitor_end_hour": 18,
    "speedtest_flags": ["--accept-license", "--accept-gdpr", "-f", "json"],
    "skip_download": False,  # Pular teste de download
    "skip_upload": False     # Pular teste de upload
}


# Variáveis globais de configuração
config = DEFAULT_CONFIG.copy()
config_changed = threading.Event()
last_test_time = None




def load_config():
    """Carrega configurações do arquivo JSON."""
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded = json.load(f)
                config.update(loaded)
                print(f"[INFO] Configuração carregada: {config}")
        except Exception as e:
            print(f"[ERRO] Falha ao carregar config: {e}")
            config = DEFAULT_CONFIG.copy()
    else:
        save_config()

def save_config():
    """Salva configurações no arquivo JSON."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"[INFO] Configuração salva: {config}")
        # Sinalizar que a configuração mudou
        config_changed.set()
    except Exception as e:
        print(f"[ERRO] Falha ao salvar config: {e}")

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
            upload_mbps REAL,
            jitter REAL,
            packet_loss REAL,
            provider TEXT,
            data_consumed_mb REAL
        )
    """)
    
    # Migração: adicionar coluna provider se não existir
    try:
        cursor.execute("SELECT provider FROM metrics LIMIT 1")
    except sqlite3.OperationalError:
        print("[INFO] Adicionando coluna 'provider' à tabela existente...")
        cursor.execute("ALTER TABLE metrics ADD COLUMN provider TEXT")
        print("[INFO] Coluna 'provider' adicionada com sucesso!")
    
    # Migração: adicionar coluna data_consumed_mb se não existir
    try:
        cursor.execute("SELECT data_consumed_mb FROM metrics LIMIT 1")
    except sqlite3.OperationalError:
        print("[INFO] Adicionando coluna 'data_consumed_mb' à tabela existente...")
        cursor.execute("ALTER TABLE metrics ADD COLUMN data_consumed_mb REAL")
        print("[INFO] Coluna 'data_consumed_mb' adicionada com sucesso!")
    
    conn.commit()
    conn.close()
    print("[INFO] Banco de dados inicializado:", DB_FILE)

# === Função para obter estatísticas de rede ===
def get_network_stats(interface=None):
    """Obtém bytes transmitidos e recebidos da interface de rede."""
    try:
        if interface is None:
            # Detectar interface ativa automaticamente
            result = subprocess.run(["ip", "route", "get", "8.8.8.8"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'dev' in line:
                        parts = line.split()
                        if 'dev' in parts:
                            idx = parts.index('dev')
                            if idx + 1 < len(parts):
                                interface = parts[idx + 1]
                                break
        
        if interface is None:
            interface = "eth0"  # fallback
        
        # Ler estatísticas do /sys/class/net
        rx_path = f"/sys/class/net/{interface}/statistics/rx_bytes"
        tx_path = f"/sys/class/net/{interface}/statistics/tx_bytes"
        
        with open(rx_path, 'r') as f:
            rx_bytes = int(f.read().strip())
        with open(tx_path, 'r') as f:
            tx_bytes = int(f.read().strip())
        
        return rx_bytes, tx_bytes, interface
    except Exception as e:
        print(f"[WARN] Não foi possível obter estatísticas de rede: {e}")
        return 0, 0, "unknown"

# === Executa o speedtest oficial ===
def executar_speedtest():
    """Executa o speedtest e retorna ping, download, upload, jitter, packet loss, provider e consumo."""
    try:
        # Capturar estatísticas de rede antes do teste
        rx_before, tx_before, interface = get_network_stats()
        
        # Construir comando - usar speedtest-cli ao invés de speedtest
        command = ["speedtest-cli", "--json"]
        
        # Adicionar flags para pular download ou upload se configurado
        if config.get("skip_download", False):
            command.append("--no-download")
            print("[INFO] Download desabilitado - pulando teste de download", flush=True)
        
        if config.get("skip_upload", False):
            command.append("--no-upload")
            print("[INFO] Upload desabilitado - pulando teste de upload", flush=True)
        
        result = subprocess.run(
            command,
            capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            print(f"[ERRO] Speedtest falhou: {result.stderr.strip()}", flush=True)
            return None, None, None, None, None, None, None

        data = json.loads(result.stdout)

        # speedtest-cli retorna formato diferente
        ping = data.get("ping", 0)
        jitter = 0  # speedtest-cli não retorna jitter
        download = data.get("download", 0) / 1e6  # bytes/s → Mbps
        upload = data.get("upload", 0) / 1e6
        packet_loss = 0  # speedtest-cli não retorna packet loss
        provider = data.get("client", {}).get("isp", "Unknown")
        
        # Capturar estatísticas de rede depois do teste
        rx_after, tx_after, _ = get_network_stats(interface)
        
        # Calcular consumo de dados em MB
        data_consumed_bytes = (rx_after - rx_before) + (tx_after - tx_before)
        data_consumed_mb = data_consumed_bytes / (1024 * 1024)
        
        # Também tentar obter do JSON do speedtest-cli
        bytes_sent = data.get("bytes_sent", 0)
        bytes_received = data.get("bytes_received", 0)
        if bytes_sent > 0 or bytes_received > 0:
            speedtest_consumed_mb = (bytes_sent + bytes_received) / (1024 * 1024)
            # Usar o maior valor entre os dois métodos
            data_consumed_mb = max(data_consumed_mb, speedtest_consumed_mb)
        
        print(f"[INFO] Consumo do teste: {data_consumed_mb:.2f} MB (interface: {interface})", flush=True)

        return ping, download, upload, jitter, packet_loss, provider, data_consumed_mb

    except FileNotFoundError:
        print("[ERRO] O executável 'speedtest-cli' não foi encontrado.", flush=True)
        print("Instale com:", flush=True)
        print("  pip install speedtest-cli", flush=True)
        print("ou", flush=True)
        print("  sudo apt install speedtest-cli", flush=True)
    except json.JSONDecodeError as e:
        print(f"[ERRO EXECUTAR_SPEEDTEST] Erro ao interpretar JSON: {e}", flush=True)
        print("Saída recebida:", result.stdout[:200], "...", flush=True)
    except Exception as e:
        print(f"[ERRO EXECUTAR_SPEEDTEST] {e}", flush=True)

    return None, None, None, None, None, None, None

# === Coletor de dados (usando Ookla) ===
def collect_metrics():
    global last_test_time
    
    print("[INFO] Thread de coleta iniciada!", flush=True)
    
    while True:
        try:
            # Verificar se o OLED pausou o monitoramento
            
            
            # Verificar se está dentro do horário de monitoramento
            current_hour = datetime.now().hour
            start_hour = config["monitor_start_hour"]
            end_hour = config["monitor_end_hour"]
            
            if current_hour < start_hour or current_hour >= end_hour:
                print(f"[INFO] Fora do horário de monitoramento ({start_hour}h-{end_hour}h). Aguardando...", flush=True)
                # Aguardar até entrar no horário ou config mudar
                config_changed.wait(timeout=300)  # 5 minutos
                config_changed.clear()
                continue
            
            # Calcular quando deve ser o próximo teste
            now = datetime.now()
            interval = config["measure_interval"]
            
            if last_test_time is None:
                # Primeiro teste, executar imediatamente
                print("[INFO] Primeiro teste - executando imediatamente...", flush=True)
            else:
                time_since_last = (now - last_test_time).total_seconds()
                
                if time_since_last < interval:
                    # Ainda não é hora, aguardar
                    wait_time = max(1, interval - time_since_last)  # Mínimo 1 segundo
                    print(f"[INFO] Próximo teste em {wait_time:.0f}s (intervalo: {interval}s, tempo decorrido: {time_since_last:.0f}s)", flush=True)
                    
                    # Aguardar com possibilidade de interrupção por mudança de config
                    config_changed.wait(timeout=wait_time)
                    config_changed.clear()
                    # Após acordar, voltar ao início do loop para reavaliar
                    continue
                else:
                    print(f"[INFO] Intervalo completo ({time_since_last:.0f}s >= {interval}s) - executando teste...", flush=True)
            
            # Executar o teste
            print("[INFO] Executando speedtest oficial...", flush=True)
            ping, download, upload, jitter, packet_loss, provider, data_consumed = executar_speedtest()

            if ping is not None and download is not None and upload is not None:
                last_test_time = datetime.now()
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO metrics (timestamp, ping_avg, download_mbps, upload_mbps, jitter, packet_loss, provider, data_consumed_mb) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ping, download, upload, jitter, packet_loss, provider, data_consumed)
                )
                conn.commit()
                conn.close()
                print(f"[OK] Registro salvo: provider={provider} | ping={ping:.2f} ms | jitter={jitter:.2f} ms | ↓ {download:.2f} Mbps | ↑ {upload:.2f} Mbps | perda={packet_loss:.2f}% | consumo={data_consumed:.2f} MB", flush=True)
            else:
                # Se falhou, NÃO atualizar last_test_time para tentar novamente mais rápido
                print("[WARN] Speedtest retornou dados incompletos. Tentando novamente em 60s...", flush=True)
                time.sleep(60)  # Aguardar 1 minuto antes de tentar novamente
                continue

        except Exception as e:
            print(f"[ERRO COLETA] {e}", flush=True)
            import traceback
            traceback.print_exc()
            # Em caso de erro, aguardar um pouco antes de tentar novamente
            time.sleep(60)

# === Rota principal ===
@app.route("/")
def index():
    return render_template("index.html")

# === API de provedores disponíveis ===
@app.route("/providers")
def providers():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT provider FROM metrics WHERE provider IS NOT NULL ORDER BY provider")
    providers_list = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(providers_list)

# === API de consumo total de dados ===
@app.route("/data-usage")
def data_usage():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Consumo total
    cursor.execute("SELECT SUM(data_consumed_mb) FROM metrics WHERE data_consumed_mb IS NOT NULL")
    total = cursor.fetchone()[0] or 0
    
    # Consumo por dia (últimos 30 dias)
    cursor.execute("""
        SELECT DATE(timestamp) as day, SUM(data_consumed_mb) as daily_total
        FROM metrics 
        WHERE data_consumed_mb IS NOT NULL 
        AND timestamp >= datetime('now', '-30 days')
        GROUP BY DATE(timestamp)
        ORDER BY day DESC
    """)
    daily = [{"date": row[0], "mb": row[1]} for row in cursor.fetchall()]
    
    # Número de testes realizados
    cursor.execute("SELECT COUNT(*) FROM metrics")
    test_count = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "total_mb": round(total, 2),
        "total_gb": round(total / 1024, 2),
        "test_count": test_count,
        "daily_usage": daily
    })

# === API de status do monitor ===
@app.route("/status")
def get_status():
    global last_test_time
    now = datetime.now()
    
    in_schedule = config["monitor_start_hour"] <= now.hour < config["monitor_end_hour"]
    
    status = {
        "is_monitoring": True,
        "current_hour": now.hour,
        "monitor_start_hour": config["monitor_start_hour"],
        "monitor_end_hour": config["monitor_end_hour"],
        "in_schedule": in_schedule,
        "last_test": last_test_time.strftime("%Y-%m-%d %H:%M:%S") if last_test_time else None,
        "next_test_in_seconds": None,
        "current_interval": config["measure_interval"],
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if last_test_time and in_schedule:
        elapsed = (now - last_test_time).total_seconds()
        interval = config["measure_interval"]
        if elapsed < interval:
            status["next_test_in_seconds"] = int(interval - elapsed)
        else:
            status["next_test_in_seconds"] = 0
    
    return jsonify(status)

# === API de configuração ===
@app.route("/config")
def get_config():
    return jsonify(config)

@app.route("/config", methods=["POST"])
def update_config():
    global config
    try:
        new_config = request.get_json()
        
        # Validar configurações
        if "measure_interval" in new_config:
            interval = int(new_config["measure_interval"])
            if interval < 60:
                return jsonify({"error": "Intervalo mínimo é 60 segundos"}), 400
            config["measure_interval"] = interval
        
        if "monitor_start_hour" in new_config:
            start = int(new_config["monitor_start_hour"])
            if start < 0 or start > 23:
                return jsonify({"error": "Hora inicial deve estar entre 0 e 23"}), 400
            config["monitor_start_hour"] = start
        
        if "monitor_end_hour" in new_config:
            end = int(new_config["monitor_end_hour"])
            if end < 0 or end > 23:
                return jsonify({"error": "Hora final deve estar entre 0 e 23"}), 400
            config["monitor_end_hour"] = end
        
        if "speedtest_flags" in new_config:
            if isinstance(new_config["speedtest_flags"], list):
                config["speedtest_flags"] = new_config["speedtest_flags"]
        
        if "skip_download" in new_config:
            config["skip_download"] = bool(new_config["skip_download"])
        
        if "skip_upload" in new_config:
            config["skip_upload"] = bool(new_config["skip_upload"])
        
        save_config()
        return jsonify({"success": True, "config": config})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# === API de dados para o dashboard ===
@app.route("/data")
def data():
    time_range = request.args.get("range", "1h")
    provider_filter = request.args.get("provider", "all")
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
    
    if provider_filter == "all":
        df = pd.read_sql_query(
            "SELECT * FROM metrics WHERE timestamp >= ? ORDER BY timestamp ASC",
            conn,
            params=(start_time.strftime("%Y-%m-%d %H:%M:%S"),)
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM metrics WHERE timestamp >= ? AND provider = ? ORDER BY timestamp ASC",
            conn,
            params=(start_time.strftime("%Y-%m-%d %H:%M:%S"), provider_filter)
        )
    
    conn.close()

    if df.empty:
        return jsonify({
            "timestamps": [], 
            "ping": [], 
            "download": [], 
            "upload": [],
            "jitter": [],
            "packet_loss": [],
            "providers": [],
            "data_consumed": [],
            "total_data_consumed_mb": 0,
            "stats": {
                "download": {"min": 0, "max": 0},
                "upload": {"min": 0, "max": 0},
                "ping": {"min": 0, "max": 0},
                "jitter": {"min": 0, "max": 0},
                "packet_loss": {"min": 0, "max": 0}
            }
        })

    # Calcular estatísticas
    stats = {
        "download": {
            "min": float(df["download_mbps"].min()),
            "max": float(df["download_mbps"].max())
        },
        "upload": {
            "min": float(df["upload_mbps"].min()),
            "max": float(df["upload_mbps"].max())
        },
        "ping": {
            "min": float(df["ping_avg"].min()),
            "max": float(df["ping_avg"].max())
        },
        "jitter": {
            "min": float(df["jitter"].min()) if "jitter" in df.columns else 0,
            "max": float(df["jitter"].max()) if "jitter" in df.columns else 0
        },
        "packet_loss": {
            "min": float(df["packet_loss"].min()) if "packet_loss" in df.columns else 0,
            "max": float(df["packet_loss"].max()) if "packet_loss" in df.columns else 0
        }
    }

    # Calcular consumo total de dados
    total_data_consumed = 0
    if "data_consumed_mb" in df.columns:
        total_data_consumed = float(df["data_consumed_mb"].sum())
        # Substituir NaN por 0 para evitar problemas no JSON
        if pd.isna(total_data_consumed):
            total_data_consumed = 0

    # Preparar listas de dados, substituindo NaN por None ou 0
    data_consumed_list = []
    if "data_consumed_mb" in df.columns:
        data_consumed_list = [0 if pd.isna(x) else float(x) for x in df["data_consumed_mb"].tolist()]

    return jsonify({
        "timestamps": df["timestamp"].tolist(),
        "ping": df["ping_avg"].tolist(),
        "download": df["download_mbps"].tolist(),
        "upload": df["upload_mbps"].tolist(),
        "jitter": df["jitter"].tolist() if "jitter" in df.columns else [],
        "packet_loss": df["packet_loss"].tolist() if "packet_loss" in df.columns else [],
        "providers": df["provider"].tolist() if "provider" in df.columns else [],
        "data_consumed": data_consumed_list,
        "total_data_consumed_mb": total_data_consumed,
        "stats": stats
    })

# === Inicialização ===
if __name__ == "__main__":
    load_config()
    init_db()

    # Inicia coleta em background
    collector_thread = threading.Thread(target=collect_metrics, daemon=True)
    collector_thread.start()

    print("[INFO] Servidor Flask iniciado em http://0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080, debug=False)
