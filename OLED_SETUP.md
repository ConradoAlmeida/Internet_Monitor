# Guia de Configuração do Display OLED 0.96"

Documentação completa para implementação do display OLED simplificado com o Monitor de Internet.

**Versão**: Simplificada - Tela única com médias das últimas 4 horas

---

## 📋 Requisitos de Hardware

### Display OLED
- **Modelo**: Display OLED 0.96" (128x64 pixels)
- **Controlador**: SSD1306
- **Interface**: I2C
- **Tensão**: 3.3V ou 5V (usar 3.3V no Raspberry Pi)

### Botão
- **Quantidade**: 1 botão push-button (normalmente aberto)
- **Tipo**: Tátil ou momentâneo
- **Pull-up**: Interno do GPIO (não precisa resistor externo)

### Jumpers/Fios
- Fios dupont fêmea-fêmea para conexões
- Protoboard (opcional, para organização)

---

## 🔌 Diagrama de Conexões

### Display OLED (I2C)
```
Display OLED          Raspberry Pi
┌──────────┐         ┌──────────┐
│   VCC    │────────→│  3.3V    │
│   GND    │────────→│  GND     │
│   SCL    │────────→│  GPIO3   │ (SCL - Pino 5)
│   SDA    │────────→│  GPIO2   │ (SDA - Pino 3)
└──────────┘         └──────────┘
```

### Botão de Controle
```
Botão              GPIO          Função                    Pino Físico
┌─────────────┬──────────┬──────────────────────────┬────────────┐
│ PAUSE       │  GPIO23  │ Pausar/Retomar monitor   │   Pino 16  │
└─────────────┴──────────┴──────────────────────────┴────────────┘
```

**Conexão do Botão**: Conecta GPIO23 ao GND quando pressionado.

```
     GPIO Pin
        │
        │
     ┌──┴──┐
     │ BTN │  ←─ Push Button
     └──┬──┘
        │
       GND
```

> **Nota**: Os GPIOs estão configurados com pull-up interno, então quando o botão é pressionado (conecta ao GND), o GPIO lê LOW (0).

---

## ⚙️ Instalação e Configuração

### 1. Habilitar Interface I2C

O display OLED usa comunicação I2C, que precisa ser habilitada no Raspberry Pi:

```bash
# Abrir configuração
sudo raspi-config
```

Navegue para:
- `3 Interface Options`
- `I5 I2C`
- `Yes` para habilitar

Reinicie o Raspberry Pi:
```bash
sudo reboot
```

### 2. Verificar Detecção do Display

Após reiniciar, instale as ferramentas I2C:

```bash
sudo apt-get update
sudo apt-get install -y i2c-tools
```

Detectar dispositivos I2C:

```bash
sudo i2cdetect -y 1
```

**Saída esperada** (display no endereço 0x3C ou 0x3D):
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- 3c -- -- -- 
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
70: -- -- -- -- -- -- -- --
```

Se não aparecer nada:
- Verifique as conexões (VCC, GND, SDA, SCL)
- Confirme que o I2C está habilitado
- Teste com outro endereço I2C (0x3D)

### 3. Instalar Dependências Python

```bash
cd /home/rubens/Internet_Monitor

# Instalar bibliotecas necessárias
pip3 install -r requirements_oled.txt
```

As dependências incluem:
- `adafruit-circuitpython-ssd1306` - Driver do display
- `pillow` - Manipulação de imagens
- `RPi.GPIO` - Controle do botão GPIO
- `adafruit-blinka` - Camada de compatibilidade

### 4. Permissões de Usuário

Para usar I2C e GPIO sem `sudo`:

```bash
# Adicionar usuário aos grupos necessários
sudo usermod -aG i2c $USER
sudo usermod -aG gpio $USER

# Fazer logout e login novamente para aplicar
```

### 5. Testar o Display

```bash
# Iniciar o display OLED
./start_oled.sh
```

O display deve ligar e mostrar a tela principal com médias das últimas 4 horas.

Para ver os logs:
```bash
tail -f oled.log
```

Para parar:
```bash
./stop_oled.sh
```

---

## 🎮 Uso e Funcionalidades

### Tela Principal (única)

O display mostra **médias das últimas 4 horas** em uma única tela:

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

**Informações exibidas**:
- **IP**: Endereço IP local do servidor
- **D (Download)**: Velocidade média de download em Mbps
- **U (Upload)**: Velocidade média de upload em Mbps
- **L (Latência)**: Ping médio em milissegundos
- **J (Jitter)**: Variação média de latência em ms
- **Rodapé**: Quantidade de testes usados na média

**Quando pausado**:
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

---

### Controle do Botão PAUSE

| Botão | Estado | Ação |
|-------|--------|------|
| **SELECT** | Qualquer tela | Avança para próxima tela (Stats → Gráfico → Menu → Stats) |
| **UP** | Menu | Move cursor para cima |
| **UP** | Stats/Gráfico | Vai para o menu |
| **DOWN** | Menu | Ajusta valor do item selecionado OU move para baixo |
| **DOWN** | Stats/Gráfico | Volta para tela de estatísticas |
| **PAUSE** | Qualquer tela | **Pausa/Retoma o monitoramento** |

> **Debounce**: 300ms entre pressionamentos para evitar leituras duplicadas

---

## 🔄 Integração com o Sistema Principal

### Sincronização de Configurações

As configurações ajustadas no OLED são **salvas automaticamente** em `config.json` e aplicadas em tempo real ao `app.py`:

```python
# Quando DOWN é pressionado em "Intervalo":
self.config['measure_interval'] = novo_valor
self.save_config()  # Salva em config.json
```

O `app.py` detecta mudanças através de um evento (`config_changed.set()`).

### Estado de Pausa

Quando o botão `PAUSE` é pressionado, o estado é salvo em `oled_pause_state.txt`:

```
1  ← Pausado
0  ← Ativo
```

O `app.py` verifica este arquivo a cada iteração:

```python
if os.path.exists('oled_pause_state.txt'):
    with open('oled_pause_state.txt', 'r') as f:
        oled_paused = f.read().strip() == '1'
```

Se pausado, os testes de velocidade não são executados.

---

## 🐛 Troubleshooting

### Problema: Display não acende

**Possíveis causas**:
1. I2C não habilitado
   ```bash
   sudo raspi-config
   # Interface Options → I2C → Enable
   ```

2. Conexões erradas
   - Verificar VCC (3.3V), GND, SDA (GPIO2), SCL (GPIO3)

3. Display em endereço diferente
   ```bash
   sudo i2cdetect -y 1
   ```
   Se aparecer em 0x3D ao invés de 0x3C, editar `oled_display.py`:
   ```python
   self.display = SSD1306_I2C(DISPLAY_WIDTH, DISPLAY_HEIGHT, i2c, addr=0x3D)
   ```

---

### Problema: Botão não responde

**Possíveis causas**:
1. GPIO23 não conectado corretamente
   - Verificar se o pino físico 16 está conectado ao botão
   - Usar `gpio readall` para ver mapeamento de pinos

2. Botão não conectado ao GND
   - O botão deve conectar GPIO23 ao GND quando pressionado

3. Debounce muito curto
   - Aumentar tempo em `oled_display.py`:
   ```python
   self.debounce_time = 0.5  # 500ms
   ```

4. Testar manualmente o GPIO:
   ```bash
   gpio -g read 23
   # Deve retornar 1 (HIGH) quando não pressionado
   # Deve retornar 0 (LOW) quando pressionado
   ```

---

### Problema: Erro de importação

```
ModuleNotFoundError: No module named 'adafruit_ssd1306'
```

**Solução**:
```bash
pip3 install --upgrade -r requirements_oled.txt
```

Se persistir:
```bash
pip3 install adafruit-circuitpython-ssd1306 --force-reinstall
```

---

### Problema: Permissão negada ao acessar I2C

```
PermissionError: [Errno 13] Permission denied: '/dev/i2c-1'
```

**Solução**:
```bash
sudo usermod -aG i2c $USER
# Fazer logout/login
```

Ou executar com `sudo` (não recomendado):
```bash
sudo ./start_oled.sh
```

---

## 🚀 Inicialização Automática (Opcional)

Para iniciar o OLED automaticamente no boot do Raspberry Pi:

### Método 1: Adicionar ao crontab

```bash
crontab -e
```

Adicionar linha:
```
@reboot sleep 30 && /home/rubens/Internet_Monitor/start_oled.sh
```

### Método 2: Criar serviço systemd

Criar arquivo `/etc/systemd/system/oled_monitor.service`:

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

---

## 🎨 Customização

### Alterar Pino GPIO do Botão

Editar `oled_display.py`:

```python
# Configuração do botão GPIO
BUTTON_PAUSE = 23  # Trocar para outro GPIO se necessário
```

### Alterar Janela de Tempo das Médias

Editar `oled_display.py`, função `get_avg_stats_4h()`:

```python
# Trocar 4 horas para outro período
four_hours_ago = (datetime.now() - timedelta(hours=4)).strftime(...)

# Exemplo: últimas 2 horas
two_hours_ago = (datetime.now() - timedelta(hours=2)).strftime(...)

# Exemplo: últimas 24 horas
one_day_ago = (datetime.now() - timedelta(hours=24)).strftime(...)
```

### Alterar Intervalo de Atualização

Editar `oled_display.py`, função `run()`:

```python
# Padrão: 0.5s (2 Hz)
time.sleep(0.5)

# Mais rápido (usa mais CPU):
time.sleep(0.2)

# Mais lento (economiza energia):
time.sleep(1.0)
```

### Alterar Fontes

O código tenta usar DejaVu Sans. Para usar outra fonte:

```python
self.font_small = ImageFont.truetype('/caminho/para/sua/fonte.ttf', 9)
```

---

## 📊 Arquitetura do Sistema

```
┌─────────────────────────────────────────────────┐
│                Raspberry Pi                      │
│                                                  │
│  ┌────────────┐         ┌─────────────┐         │
│  │  app.py    │◄───────►│config.json  │         │
│  │ (Flask +   │         │             │         │
│  │ Speedtest) │         └─────────────┘         │
│  └──────┬─────┘                                  │
│         │                                        │
│         │ Lê/Escreve                            │
│         ▼                                        │
│  ┌─────────────────┐                            │
│  │oled_pause_state │                            │
│  │     .txt        │                            │
│  └────────▲────────┘                            │
│           │                                      │
│           │ Escreve                             │
│           │                                      │
│  ┌────────┴──────────┐    ┌──────────────┐     │
│  │ oled_display.py   │◄──►│ internet.db  │     │
│  │                   │    │ (SQLite)     │     │
│  └───────┬───────────┘    └──────────────┘     │
│          │                                       │
│          │ Controla                             │
│          ▼                                       │
│  ┌──────────────┐    ┌────────────┐            │
│  │Display OLED  │    │   Botão    │            │
│  │  (I2C SDA)   │    │   GPIO23   │            │
│  │  (I2C SCL)   │    │  (PAUSE)   │            │
│  └──────────────┘    └────────────┘            │
│                      └────────────┘             │
└─────────────────────────────────────────────────┘
```

---

## 📝 Arquivos Relacionados

| Arquivo | Descrição |
|---------|-----------|
| `oled_display.py` | Script principal do display OLED |
| `requirements_oled.txt` | Dependências Python para OLED |
| `start_oled.sh` | Script para iniciar o display |
| `stop_oled.sh` | Script para parar o display |
| `oled.log` | Log de execução do display |
| `oled.pid` | PID do processo do display |
| `oled_pause_state.txt` | Estado de pausa (0=ativo, 1=pausado) |
| `config.json` | Configuração compartilhada |

---

## ✅ Checklist de Instalação

- [ ] I2C habilitado no Raspberry Pi (`raspi-config`)
- [ ] Display OLED conectado (VCC, GND, SDA, SCL)
- [ ] Display detectado com `i2cdetect -y 1` (endereço 0x3C ou 0x3D)
- [ ] Botão conectado ao GPIO23
- [ ] Dependências instaladas (`pip3 install -r requirements_oled.txt`)
- [ ] Usuário adicionado aos grupos i2c e gpio
- [ ] Display testado com `./start_oled.sh`
- [ ] Botão PAUSE funcionando corretamente
- [ ] Dados sendo exibidos corretamente (médias das últimas 4h)

---

## 🆘 Suporte

Para problemas ou dúvidas:
1. Verificar logs: `tail -f oled.log`
2. Verificar status I2C: `sudo i2cdetect -y 1`
3. Testar GPIO23: `gpio -g read 23`
4. Verificar permissões de arquivo
5. Consultar a seção de Troubleshooting acima

---

**Versão**: Simplificada (tela única com médias)  
**Última atualização**: 18 de Novembro de 2025
