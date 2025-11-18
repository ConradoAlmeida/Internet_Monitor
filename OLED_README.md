# Display OLED para Monitor de Internet

Interface simplificada para display OLED 0.96" (128x64 pixels, SSD1306) mostrando médias das últimas 4 horas.

## Hardware Necessário

- Display OLED 0.96" I2C (SSD1306)
- 1 botão push-button (para pausa)
- Jumpers para conexão

## Conexões GPIO

### Display OLED (I2C)
- VCC → 3.3V
- GND → GND
- SCL → GPIO3 (SCL - Pino 5)
- SDA → GPIO2 (SDA - Pino 3)

### Botão
- **PAUSE** (Pausar/Retomar): GPIO23 (Pino 16) + GND

**Conexão do Botão**: Conecta GPIO23 ao GND quando pressionado.

```
     GPIO23
        │
        │
     ┌──┴──┐
     │ BTN │  ←─ Push Button
     └──┬──┘
        │
       GND
```

## Instalação

```bash
# Instalar dependências
pip3 install -r requirements_oled.txt

# Habilitar I2C no Raspberry Pi
sudo raspi-config
# Interface Options → I2C → Enable

# Verificar se o display foi detectado
sudo i2cdetect -y 1
# Deve mostrar um dispositivo no endereço 0x3C ou 0x3D
```

## Uso

```bash
# Iniciar display OLED
./start_oled.sh

# Parar display OLED
./stop_oled.sh

# Ver logs
tail -f oled.log
```

## Funcionalidades

### Tela Principal (única)

O display mostra **médias das últimas 4 horas** em uma única tela:

- **IP do servidor** (linha superior)
- **D (Download)**: Velocidade média em Mbps
- **U (Upload)**: Velocidade média em Mbps  
- **L (Latência/Ping)**: Tempo médio em ms
- **J (Jitter)**: Variação média em ms
- **Rodapé**: Quantidade de testes na média ou "PAUSADO"

**Layout do display:**
```
┌─────────────────────────┐
│ IP: 192.168.0.206       │
├─────────────────────────┤
│ D:  198.5       Mbps    │
│                         │
│ U:  196.2       Mbps    │
│                         │
│ L:  6.5 ms    J: 0.0 ms │
│                         │
├─────────────────────────┤
│ Med.4h (42 tests)       │
└─────────────────────────┘
```

**Quando pausado:**
```
┌─────────────────────────┐
│ IP: 192.168.0.206       │
├─────────────────────────┤
│ D:  198.5       Mbps    │
│                         │
│ U:  196.2       Mbps    │
│                         │
│ L:  6.5 ms    J: 0.0 ms │
│                         │
├─────────────────────────┤
│ PAUSADO                 │
└─────────────────────────┘
```

### Botão PAUSE

Pressione a qualquer momento para **pausar/retomar** o monitoramento.

- **Estado Ativo**: Mostra "Med.4h (N tests)" no rodapé
- **Estado Pausado**: Mostra "PAUSADO" no rodapé
- **Debounce**: 300ms entre pressionamentos

**Como funciona:**
- Quando pausado, o sistema para de executar testes de velocidade
- O arquivo `oled_pause_state.txt` é criado com valor '1' (pausado) ou '0' (ativo)
- O `app.py` verifica este arquivo e respeita o estado de pausa

## Integração com o Sistema

### Sincronização de Estado

O display OLED comunica-se com `app.py` através do arquivo `oled_pause_state.txt`:

```python
# Quando PAUSE é pressionado:
# oled_display.py escreve:
'1'  # Pausado

# app.py lê e pausa os testes
if os.path.exists('oled_pause_state.txt'):
    with open('oled_pause_state.txt', 'r') as f:
        oled_paused = f.read().strip() == '1'
```

### Dados Exibidos

O display consulta diretamente o banco de dados SQLite (`internet.db`):

```sql
-- Query executada a cada 0.5 segundos
SELECT 
    AVG(ping_avg) as avg_ping,
    AVG(download_mbps) as avg_down,
    AVG(upload_mbps) as avg_up,
    AVG(jitter) as avg_jitter,
    COUNT(*) as count
FROM speedtest_log
WHERE timestamp >= datetime('now', '-4 hours')
```

## Troubleshooting

### Display não aparece nada

**Verificar I2C:**
```bash
sudo i2cdetect -y 1
```

**Saída esperada** (display no endereço 0x3C):
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
...
30: -- -- -- -- -- -- -- -- -- -- -- -- 3c -- -- -- 
...
```

**Se não aparecer:**
- Verificar conexões VCC, GND, SDA, SCL
- Confirmar que I2C está habilitado (`raspi-config`)
- Testar com outro endereço (0x3D)

**Verificar permissões:**
```bash
sudo usermod -aG i2c $USER
# Fazer logout e login novamente
```

### Erro de importação

```
ModuleNotFoundError: No module named 'adafruit_ssd1306'
```

**Solução:**
```bash
pip3 install --upgrade -r requirements_oled.txt

# Se persistir:
pip3 install adafruit-circuitpython-ssd1306 --force-reinstall
```

### Botão não responde

**Verificações:**
1. GPIO23 (pino físico 16) está conectado corretamente ao botão
2. Botão conecta ao GND quando pressionado
3. Usar `gpio readall` para verificar mapeamento de pinos

**Testar manualmente:**
```bash
# Verificar estado do GPIO23
gpio -g read 23
# Deve mostrar 1 (HIGH) quando não pressionado
# Deve mostrar 0 (LOW) quando pressionado
```

**Aumentar debounce se necessário:**
Editar `oled_display.py`:
```python
self.debounce_time = 0.5  # 500ms ao invés de 300ms
```

### Display mostra "Sem dados"

**Causas:**
- Nenhum teste foi executado nas últimas 4 horas
- Banco de dados vazio
- Tabela `speedtest_log` não existe

**Verificar banco:**
```bash
sqlite3 internet.db "SELECT COUNT(*) FROM speedtest_log WHERE timestamp >= datetime('now', '-4 hours')"
```

**Se retornar 0:** Aguarde alguns testes serem executados ou reduza a janela de tempo.

### Permissão negada ao acessar I2C

```
PermissionError: [Errno 13] Permission denied: '/dev/i2c-1'
```

**Solução:**
```bash
sudo usermod -aG i2c $USER
# Fazer logout/login para aplicar
```

**Alternativa temporária** (não recomendado):
```bash
sudo ./start_oled.sh
```

## Customização

### Alterar Pino GPIO do Botão

Editar `oled_display.py`:
```python
# Trocar GPIO23 para outro pino
BUTTON_PAUSE = 23  # Ex: trocar para GPIO24
```

### Alterar Endereço I2C

Se seu display usa 0x3D ao invés de 0x3C, editar `oled_display.py`:
```python
self.display = SSD1306_I2C(DISPLAY_WIDTH, DISPLAY_HEIGHT, i2c, addr=0x3D)
```

### Alterar Intervalo de Atualização

Editar `oled_display.py` na função `run()`:
```python
# Padrão: 0.5s
time.sleep(0.5)

# Mais rápido (usa mais CPU):
time.sleep(0.2)

# Mais lento (economiza energia):
time.sleep(1.0)
```

### Alterar Janela de Tempo das Médias

Editar `oled_display.py` na função `get_avg_stats_4h()`:
```python
# Trocar 4 horas para outro período
four_hours_ago = (datetime.now() - timedelta(hours=4)).strftime(...)

# Exemplo: últimas 2 horas
two_hours_ago = (datetime.now() - timedelta(hours=2)).strftime(...)

# Exemplo: últimas 24 horas
one_day_ago = (datetime.now() - timedelta(hours=24)).strftime(...)
```

### Alterar Fontes

O código tenta usar DejaVu Sans. Para usar outra fonte:
```python
self.font_small = ImageFont.truetype('/caminho/para/fonte.ttf', 10)
self.font_medium = ImageFont.truetype('/caminho/para/fonte.ttf', 12)
self.font_large = ImageFont.truetype('/caminho/para/fonte.ttf', 16)
```

## Inicialização Automática (Opcional)

### Método 1: Crontab

```bash
crontab -e
```

Adicionar:
```
@reboot sleep 30 && /home/rubens/Internet_Monitor/start_oled.sh
```

### Método 2: Systemd Service

Criar `/etc/systemd/system/oled_monitor.service`:

```ini
[Unit]
Description=OLED Display Monitor
After=network.target internet_monitor.service

[Service]
ExecStart=/home/rubens/Internet_Monitor/start_oled.sh
WorkingDirectory=/home/rubens/Internet_Monitor
User=rubens
Group=rubens
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Habilitar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable oled_monitor.service
sudo systemctl start oled_monitor.service
```

Verificar status:
```bash
sudo systemctl status oled_monitor.service
```

## Arquivos Relacionados

| Arquivo | Descrição |
|---------|-----------|
| `oled_display.py` | Script principal do display OLED |
| `requirements_oled.txt` | Dependências Python para OLED |
| `start_oled.sh` | Script para iniciar o display |
| `stop_oled.sh` | Script para parar o display |
| `oled.log` | Log de execução do display |
| `oled.pid` | PID do processo do display |
| `oled_pause_state.txt` | Estado de pausa (0=ativo, 1=pausado) |
| `internet.db` | Banco SQLite com dados dos testes |

## Especificações Técnicas

- **Resolução**: 128x64 pixels monocromático
- **Interface**: I2C (endereço padrão 0x3C)
- **Controlador**: SSD1306
- **Tensão**: 3.3V
- **Taxa de atualização**: 2 Hz (a cada 0.5s)
- **Consumo**: ~20mA
- **Fontes**: DejaVu Sans (10px, 12px, 16px)

## Checklist de Instalação

- [ ] I2C habilitado no Raspberry Pi
- [ ] Display OLED conectado (VCC, GND, SDA, SCL)
- [ ] Display detectado com `i2cdetect` (0x3C ou 0x3D)
- [ ] Botão conectado (GPIO23 + GND)
- [ ] Dependências instaladas (`requirements_oled.txt`)
- [ ] Usuário no grupo i2c (`usermod -aG i2c`)
- [ ] Display testado com `./start_oled.sh`
- [ ] Botão PAUSE funcionando
- [ ] Dados sendo exibidos corretamente

---

**Versão**: Simplificada (única tela com médias)  
**Última atualização**: 18 de Novembro de 2025
