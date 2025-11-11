# Internet_Monitor
Application to monitor internet through a raspberry pi running Raspberry OS

## Instruction
Clone this repository

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
