# Internet_Monitor
Application to monitor internet through a raspberry pi running Raspberry OS

## Instruction
Clone este repositorio

Instale os Requirements.txt

### Instalação do Speedtest CLI

O sistema utiliza o **speedtest-cli** (Python package) para realizar os testes de velocidade:

```bash
# Instalar via pip
pip3 install speedtest-cli

# OU via apt (Debian/Ubuntu)
sudo apt-get install speedtest-cli
```

**Nota**: Este projeto foi atualizado para usar `speedtest-cli` ao invés do Speedtest CLI oficial da Ookla.

---

## 📊 Cálculo de Consumo de Dados
O sistema rastreia o volume de dados consumido por cada teste de velocidade usando **dois métodos complementares**:

### Método 1: Monitoramento da Interface de Rede (Sistema Operacional)

O sistema lê os contadores de bytes da interface de rede diretamente do kernel Linux:

```python
# Antes do teste
rx_before = ler("/sys/class/net/{interface}/statistics/rx_bytes")  # Bytes recebidos
tx_before = ler("/sys/class/net/{interface}/statistics/tx_bytes")  # Bytes transmitidos

# Executar speedtest
...

# Depois do teste
rx_after = ler("/sys/class/net/{interface}/statistics/rx_bytes")
tx_after = ler("/sys/class/net/{interface}/statistics/tx_bytes")

# Calcular consumo total
consumo_mb = ((rx_after - rx_before) + (tx_after - tx_before)) / (1024 * 1024)
```

**Vantagens**:
- ✅ Captura **TODO** o tráfego de rede durante o teste (incluindo overhead de protocolo, DNS, conexões auxiliares)
- ✅ Funciona com qualquer ferramenta de speedtest
- ✅ Dados diretos do kernel (precisão do sistema operacional)

**Detalhes**:
- Interface detectada automaticamente usando `ip route get 8.8.8.8`
- Lê arquivos do `/sys/class/net/` que são atualizados em tempo real pelo kernel
- Captura tráfego de todas as camadas (Ethernet, IP, TCP, HTTP, etc.)

### Método 2: Dados Reportados pelo Speedtest-CLI

O speedtest-cli retorna no JSON a quantidade exata de dados transferidos:

```json
{
  "bytes_sent": 148389888,      // ~148 MB transmitidos (upload)
  "bytes_received": 0,          // Download desabilitado
  ...
}
```

```python
speedtest_consumed_mb = (bytes_sent + bytes_received) / (1024 * 1024)
```

**Vantagens**:
- ✅ Valor exato reportado pela ferramenta de teste
- ✅ Não inclui overhead de outros processos

**Limitações**:
- ⚠️ Não captura tráfego de DNS, handshake SSL, etc.

### Método Híbrido (Implementado)

O sistema usa **o maior valor entre os dois métodos**:

```python
data_consumed_mb = max(metodo_interface, metodo_speedtest)
```

**Por quê?**
- Garante que o consumo **real** seja registrado
- Na prática, o **Método 1 (interface)** geralmente é maior porque captura todo o overhead
- Se houver discrepância significativa, o maior valor reflete melhor o impacto real na banda

### Exemplo Real

Teste com `--no-download` (apenas upload):

```
Método 1 (Interface): 160.93 MB
Método 2 (Speedtest):  141.47 MB  (148389888 bytes_sent / 1024² )
Registrado no banco:   160.93 MB  ← max(160.93, 141.47)
```

**Diferença de ~20 MB** devido a:
- Headers TCP/IP (~3-5%)
- Overhead de TLS/SSL
- Retransmissões de pacotes perdidos
- Tráfego de controle (ACKs, handshakes)
- DNS queries
- Tráfego de background do sistema

### Configuração de Testes

Para economizar dados, você pode desabilitar download ou upload:

**Via Frontend** (http://localhost:8080):
- Abrir "Configurações"
- Toggle "Desabilitar teste de Download" → ON
- Toggle "Desabilitar teste de Upload" → ON

**Via Display OLED**:
- Navegar até Menu
- Selecionar "Skip Download" → DOWN para alternar ON/OFF
- Selecionar "Skip Upload" → DOWN para alternar ON/OFF

**Consumo Típico**:
- Teste completo (download + upload): ~250-350 MB
- Apenas upload (`--no-download`): ~150-200 MB
- Apenas download (`--no-upload`): ~200-300 MB

### Visualização no Dashboard

O consumo total acumulado é exibido em:
- **Gráfico de Consumo de Dados**: Mostra MB consumidos por teste ao longo do tempo
- **Estatísticas**: Painel lateral com consumo total

---

##  Configuração do Serviço `internet_monitor` no Raspberry Pi

Guia completo para criar, configurar e iniciar automaticamente o **Monitor de Qualidade da Internet** usando o `systemd` no Raspberry Pi.

---

##  1️ Localizar o projeto

Certifique-se de estar na pasta do projeto:

```bash
cd ~/internet_monitor
```

> Ajuste o caminho se o projeto estiver em outro diretório.

---

## 2️ Descobrir o caminho do Python dentro do `pipenv`

Execute o comando:

```bash
pipenv --venv
```

Exemplo de saída:

```
/home/raspi4/.local/share/virtualenvs/internet_monitor-bnYQ4fFi
```

Esse é o **diretório do ambiente virtual**.  
Agora, descubra o **caminho completo do Python**:

```bash
ls $(pipenv --venv)/bin/python
```

Resultado esperado:

```
/home/raspi4/.local/share/virtualenvs/internet_monitor-bnYQ4fFi/bin/python
```

Copie esse caminho — ele será usado no arquivo de serviço.

---

## 3️ Criar o arquivo de serviço `systemd`

Abra o arquivo de serviço:

```bash
sudo nano /etc/systemd/system/internet_monitor.service
```

Cole o conteúdo abaixo (ajuste os caminhos conforme seu ambiente):

```ini
[Unit]
Description=Monitor de Qualidade da Internet (Flask + Speedtest)
After=network.target

[Service]
# Caminho completo do Python do seu ambiente pipenv
ExecStart=/home/raspi4/.local/share/virtualenvs/internet_monitor-bnYQ4fFi/bin/python /home/raspi4/internet_monitor/app.py

# Diretório do projeto
WorkingDirectory=/home/raspi4/internet_monitor

# Usuário que executa o serviço
User=raspi4
Group=raspi4

# Reiniciar automaticamente em caso de falha
Restart=always
RestartSec=10

# Variáveis de ambiente (opcional)
Environment="FLASK_ENV=production"
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

Salve com **`Ctrl + O`**, pressione **Enter**, e saia com **`Ctrl + X`**.

---

##  4️ Recarregar o `systemd` e habilitar o serviço

```bash
sudo systemctl daemon-reload
sudo systemctl enable internet_monitor.service
sudo systemctl start internet_monitor.service
```

---

## 5️ Verificar o status do serviço

```bash
sudo systemctl status internet_monitor.service
```

Saída esperada:

```
● internet_monitor.service - Monitor de Qualidade da Internet
     Loaded: loaded (/etc/systemd/system/internet_monitor.service; enabled)
     Active: active (running)
   Main PID: 1234 (python)
```

Se aparecer **“active (running)”**, o serviço está funcionando corretamente ✅.

---

## 🧰 6️⃣ Comandos úteis

| Ação | Comando |
|------|----------|
| Ver status | `sudo systemctl status internet_monitor.service` |
| Parar o serviço | `sudo systemctl stop internet_monitor.service` |
| Iniciar manualmente | `sudo systemctl start internet_monitor.service` |
| Reiniciar | `sudo systemctl restart internet_monitor.service` |
| Ver logs em tempo real | `sudo journalctl -u internet_monitor.service -f` |
| Desativar no boot | `sudo systemctl disable internet_monitor.service` |

---

## ✅ 7️ Testar inicialização automática

Reinicie o Raspberry Pi:

```bash
sudo reboot
```

Após reiniciar, verifique se o serviço iniciou automaticamente:

```bash
sudo systemctl status internet_monitor.service
```

---

## 🖥️ Display OLED (Opcional)

O sistema inclui suporte para display OLED 0.96" (128x64 pixels, SSD1306) com controle por botões físicos.

### Funcionalidades do Display

- **Tela de Estatísticas**: MIN/MAX das últimas 4 horas (ping, download, upload, jitter, packet loss)
- **Gráfico**: Barras das últimas 10 medições (download e upload)
- **Menu de Configurações**: Ajustar intervalo, horários, skip download/upload
- **Botão PAUSE**: Pausar/retomar monitoramento sem parar o serviço

### Instalação Rápida

```bash
# Habilitar I2C
sudo raspi-config
# Interface Options → I2C → Enable

# Instalar dependências
pip3 install -r requirements_oled.txt

# Iniciar display
./start_oled.sh

# Ver logs
tail -f oled.log

# Parar display
./stop_oled.sh
```

### Conexões

**Display OLED (I2C)**:
- VCC → 3.3V
- GND → GND
- SCL → GPIO3 (Pino 5)
- SDA → GPIO2 (Pino 3)

**Botões**:
- SELECT (GPIO17, Pino 11) → Navegar entre telas
- UP (GPIO27, Pino 13) → Subir no menu
- DOWN (GPIO22, Pino 15) → Ajustar valores/descer
- PAUSE (GPIO23, Pino 16) → Pausar/retomar testes

### Documentação Completa

Para instruções detalhadas de instalação, troubleshooting e customização, consulte:
- **[OLED_SETUP.md](OLED_SETUP.md)** - Guia completo de configuração do display

---
