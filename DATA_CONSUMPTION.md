# Documentação: Cálculo de Consumo de Dados

Este documento explica detalhadamente como o sistema calcula o volume de dados consumido por cada teste de velocidade.

---

## 📊 Visão Geral

O sistema implementa **dois métodos complementares** para medir o consumo de dados e usa **o maior valor** entre eles para garantir precisão.

```
┌─────────────────────────────────────────────────────────┐
│              TESTE DE VELOCIDADE                        │
│                                                         │
│  Antes do Teste          Durante          Depois       │
│  ┌──────────┐         ┌─────────┐      ┌──────────┐   │
│  │ Captura  │         │Speedtest│      │ Captura  │   │
│  │ RX/TX    │────────→│  CLI    │─────→│ RX/TX    │   │
│  │ bytes    │         │         │      │ bytes    │   │
│  └──────────┘         └─────────┘      └──────────┘   │
│       │                    │                  │        │
│       ▼                    ▼                  ▼        │
│  ┌─────────┐         ┌──────────┐      ┌─────────┐   │
│  │rx_before│         │bytes_sent│      │rx_after │   │
│  │tx_before│         │bytes_recv│      │tx_after │   │
│  └─────────┘         └──────────┘      └─────────┘   │
│       │                    │                  │        │
│       └────────────┬───────┴──────────────────┘        │
│                    ▼                                   │
│         ┌──────────────────────┐                      │
│         │  CÁLCULO HÍBRIDO     │                      │
│         │  max(método1,        │                      │
│         │      método2)        │                      │
│         └──────────┬───────────┘                      │
│                    ▼                                   │
│         ┌──────────────────────┐                      │
│         │ Salvar no Banco      │                      │
│         │ data_consumed_mb     │                      │
│         └──────────────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

---

## 🔍 Método 1: Monitoramento da Interface de Rede

### Como Funciona

O sistema lê contadores de bytes diretamente do kernel Linux através do sistema de arquivos `/sys`:

```python
def get_network_stats(interface=None):
    """Obtém bytes transmitidos e recebidos da interface de rede."""
    
    # 1. Auto-detectar interface ativa
    if interface is None:
        result = subprocess.run(["ip", "route", "get", "8.8.8.8"], 
                              capture_output=True, text=True)
        # Parse output para extrair interface (ex: "eth0", "wlan0")
        interface = extract_interface_from_output(result.stdout)
    
    # 2. Ler contadores do kernel
    rx_bytes = int(open(f"/sys/class/net/{interface}/statistics/rx_bytes").read())
    tx_bytes = int(open(f"/sys/class/net/{interface}/statistics/tx_bytes").read())
    
    return rx_bytes, tx_bytes, interface
```

### Processo de Medição

```python
# ANTES do teste
rx_before, tx_before, interface = get_network_stats()

# EXECUTAR speedtest
subprocess.run(["speedtest-cli", "--json", ...])

# DEPOIS do teste
rx_after, tx_after, _ = get_network_stats(interface)

# CALCULAR diferença
rx_diff = rx_after - rx_before  # Bytes recebidos durante o teste
tx_diff = tx_after - tx_before  # Bytes enviados durante o teste

# TOTAL em MB
data_consumed_mb = (rx_diff + tx_diff) / (1024 * 1024)
```

### O que é Capturado

```
┌─────────────────────────────────────────────────┐
│        CAMADAS DE REDE CAPTURADAS               │
├─────────────────────────────────────────────────┤
│ 7. Aplicação       │ HTTP, DNS, TLS             │
│ 6. Apresentação    │ SSL/TLS Encryption         │
│ 5. Sessão          │ Session Management         │
│ 4. Transporte      │ TCP Headers, ACKs          │
│ 3. Rede            │ IP Headers, Routing        │
│ 2. Enlace          │ Ethernet Headers           │
│ 1. Física          │ Bits no cabo               │
└─────────────────────────────────────────────────┘
          ▲
          │
    TUDO É CONTADO pelos contadores rx_bytes/tx_bytes
```

**Inclui**:
- ✅ Dados da aplicação (arquivo baixado/enviado)
- ✅ Headers TCP/IP (~3-5% de overhead)
- ✅ Headers Ethernet (~1-2%)
- ✅ Retransmissões de pacotes perdidos
- ✅ TCP ACKs (acknowledgments)
- ✅ TLS/SSL handshake e overhead
- ✅ DNS queries
- ✅ Tráfego de keep-alive
- ✅ **Todo tráfego que passa pela interface durante o teste**

**Vantagens**:
- 📊 Reflete o consumo **real** da banda de internet
- 🎯 Preciso do ponto de vista do sistema operacional
- 🔄 Funciona com qualquer ferramenta (não depende do speedtest)

**Limitações**:
- ⚠️ Captura tráfego de **outros processos** que estejam rodando simultaneamente
- ⚠️ Se houver updates, downloads, ou outros serviços ativos, o valor será inflado

---

## 🔍 Método 2: Dados do Speedtest-CLI

### Como Funciona

O `speedtest-cli` retorna no JSON a quantidade exata de bytes transferidos:

```json
{
  "download": 0,                    // Velocidade (bits/s)
  "upload": 118669546.85514227,     // Velocidade (bits/s)
  "bytes_sent": 148389888,          // ← Bytes ENVIADOS
  "bytes_received": 0,              // ← Bytes RECEBIDOS
  "ping": 7.994,
  "timestamp": "2025-11-17T14:32:00.123456Z",
  ...
}
```

### Cálculo

```python
# Extrair do JSON
bytes_sent = data.get("bytes_sent", 0)         # Upload
bytes_received = data.get("bytes_received", 0) # Download

# Converter para MB
speedtest_consumed_mb = (bytes_sent + bytes_received) / (1024 * 1024)
```

### O que é Capturado

```
┌─────────────────────────────────────────┐
│  APENAS PAYLOAD DO TESTE                │
├─────────────────────────────────────────┤
│  • Dados enviados ao servidor           │
│  • Dados recebidos do servidor          │
│  • Medição interna do speedtest-cli     │
└─────────────────────────────────────────┘
```

**Inclui**:
- ✅ Payload exato dos dados de teste
- ✅ Valor reportado pela ferramenta oficial

**NÃO Inclui**:
- ❌ Headers TCP/IP
- ❌ Headers Ethernet
- ❌ Overhead de TLS/SSL
- ❌ Retransmissões
- ❌ TCP ACKs
- ❌ DNS queries

**Vantagens**:
- 🎯 Valor "puro" do teste
- 📏 Consistente entre diferentes execuções

**Limitações**:
- ⚠️ Subestima o consumo real da banda
- ⚠️ Não reflete o que o ISP contabiliza

---

## 🔀 Método Híbrido (Implementado)

### Por Que Usar Ambos?

O sistema combina os dois métodos para obter o **valor mais preciso**:

```python
# Calcular por ambos os métodos
interface_mb = (rx_diff + tx_diff) / (1024 * 1024)      # Método 1
speedtest_mb = (bytes_sent + bytes_received) / (1024 * 1024)  # Método 2

# Usar o MAIOR valor
data_consumed_mb = max(interface_mb, speedtest_mb)
```

### Razão

```
┌────────────────────────────────────────────────────────┐
│                   COMPARAÇÃO                           │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Método Interface: ████████████████████ 160.93 MB     │
│                    └─ Real consumo da rede            │
│                                                        │
│  Método Speedtest: ██████████████      141.47 MB     │
│                    └─ Payload puro                    │
│                                                        │
│  Diferença (overhead): ████ ~20 MB (~14%)             │
│                                                        │
│  ✅ Registrado: 160.93 MB (maior valor)               │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**Benefícios**:
1. **Segurança**: Sempre registra o consumo real ou superior
2. **Precisão**: Se houver discrepância, usa o valor do kernel
3. **Confiabilidade**: Se um método falhar, usa o outro
4. **Realismo**: Reflete o que realmente sai da sua cota de internet

---

## 📈 Exemplo Prático

### Cenário: Teste com `--no-download` (apenas upload)

#### Configuração
```python
config = {
    "skip_download": True,   # Download desabilitado
    "skip_upload": False     # Upload habilitado
}
```

#### Execução

```python
# 1. ANTES do teste
rx_before = 1234567890  # bytes recebidos acumulados
tx_before = 9876543210  # bytes enviados acumulados
interface = "eth0"

# 2. EXECUTAR speedtest
speedtest-cli --json --no-download

# 3. JSON retornado
{
  "download": 0,
  "upload": 196870000,      # ~197 Mbps
  "bytes_sent": 148389888,   # ~141.47 MB
  "bytes_received": 5242880  # ~5 MB (overhead de controle)
}

# 4. DEPOIS do teste
rx_after = 1240335770  # Diferença: +5,767,880 bytes (~5.5 MB)
tx_after = 10045421310 # Diferença: +168,878,100 bytes (~161 MB)

# 5. MÉTODO 1: Interface
rx_diff = 5767880
tx_diff = 168878100
interface_mb = (5767880 + 168878100) / (1024*1024) = 166.48 MB

# 6. MÉTODO 2: Speedtest
speedtest_mb = (148389888 + 5242880) / (1024*1024) = 146.47 MB

# 7. HÍBRIDO
data_consumed_mb = max(166.48, 146.47) = 166.48 MB

# 8. SALVAR no banco de dados
INSERT INTO metrics (..., data_consumed_mb) VALUES (..., 166.48)
```

#### Análise do Overhead

```
Total consumido (interface): 166.48 MB
Payload (speedtest):         146.47 MB
─────────────────────────────────────
Overhead de rede:             20.01 MB  (12.02%)
```

**Composição do overhead (~20 MB)**:
- TCP Headers (20 bytes por pacote): ~2-3 MB
- IP Headers (20 bytes por pacote): ~2-3 MB
- Ethernet Headers (14 bytes por frame): ~1-2 MB
- TLS/SSL overhead (~5-10%): ~7-15 MB
- Retransmissões (~1-3%): ~1-4 MB
- TCP ACKs: ~1-2 MB
- DNS/Handshakes: ~0.5 MB

---

## 🎯 Caso de Uso: Economizar Dados

### Desabilitar Download

```bash
# Via interface web
http://localhost:8080 → Configurações → "Desabilitar Download" → ON

# Via OLED
Menu → Skip Download → DOWN para alternar → ON
```

**Resultado**:
- Consumo reduzido de ~300 MB para ~160 MB por teste
- Economia de ~47%
- Apenas upload é testado (útil para monitorar qualidade de envio)

### Desabilitar Upload

```bash
# Via interface web
http://localhost:8080 → Configurações → "Desabilitar Upload" → ON
```

**Resultado**:
- Consumo reduzido de ~300 MB para ~200 MB por teste
- Economia de ~33%
- Apenas download é testado

### Desabilitar Ambos (Apenas Ping)

```bash
Skip Download: ON
Skip Upload: ON
```

**Resultado**:
- Consumo mínimo: ~1-5 MB por teste
- Apenas latência é medida
- Útil para monitorar conectividade sem consumir banda

---

## 📊 Dados no Banco

### Estrutura da Tabela

```sql
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    ping_avg REAL,
    download_mbps REAL,
    upload_mbps REAL,
    jitter REAL,
    packet_loss REAL,
    provider TEXT,
    data_consumed_mb REAL  ← Consumo armazenado aqui
);
```

### Exemplo de Registro

```sql
INSERT INTO metrics VALUES (
    302,                              -- id
    '2025-11-17 16:46:00',           -- timestamp
    6.88,                             -- ping_avg (ms)
    0.00,                             -- download_mbps (desabilitado)
    196.87,                           -- upload_mbps
    0.00,                             -- jitter (speedtest-cli não fornece)
    0.00,                             -- packet_loss (speedtest-cli não fornece)
    'NipTelecom Telecomunicacoes',   -- provider
    160.93                            -- data_consumed_mb ← AQUI
);
```

### Consulta de Consumo Total

```sql
-- Consumo total acumulado
SELECT SUM(data_consumed_mb) as total_mb,
       SUM(data_consumed_mb) / 1024 as total_gb
FROM metrics;

-- Consumo das últimas 24 horas
SELECT SUM(data_consumed_mb) as last_24h_mb
FROM metrics
WHERE timestamp >= datetime('now', '-1 day');

-- Consumo médio por teste
SELECT AVG(data_consumed_mb) as avg_mb_per_test
FROM metrics;
```

---

## 🔧 Verificação e Debugging

### Verificar Interface Ativa

```bash
# Ver rotas
ip route get 8.8.8.8

# Saída:
# 8.8.8.8 via 192.168.0.1 dev eth0 src 192.168.0.206

# Ver estatísticas em tempo real
cat /sys/class/net/eth0/statistics/rx_bytes
cat /sys/class/net/eth0/statistics/tx_bytes

# Monitorar em tempo real
watch -n 1 'cat /sys/class/net/eth0/statistics/*x_bytes'
```

### Ver Logs de Consumo

```bash
# Ver últimos logs
tail -f monitor.log | grep "Consumo"

# Saída:
# [INFO] Consumo do teste: 160.93 MB (interface: eth0)
```

### Analisar Discrepâncias

Se a diferença entre os métodos for muito grande (>30%):

```python
# Causas possíveis:
# 1. Tráfego de background (updates, downloads paralelos)
# 2. Retransmissões excessivas (conexão ruim)
# 3. Overhead de SSL/TLS alto
# 4. Muitos pacotes pequenos (aumenta overhead de headers)
```

**Solução**: Pausar outros serviços durante o teste:
```bash
sudo systemctl stop unattended-upgrades
sudo systemctl stop apt-daily.timer
```

---

## 📚 Referências

- **Linux Network Statistics**: `/sys/class/net/*/statistics/`
- **Speedtest-CLI**: https://github.com/sivel/speedtest-cli
- **TCP/IP Overhead**: ~5-10% em transferências típicas
- **TLS Overhead**: ~2-5% adicional

---

## ✅ Resumo

| Aspecto | Método Interface | Método Speedtest | Híbrido |
|---------|-----------------|------------------|---------|
| **Precisão Real** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Overhead Incluído** | ✅ Sim | ❌ Não | ✅ Sim |
| **Captura Background** | ⚠️ Sim | ✅ Não | ⚠️ Sim |
| **Confiabilidade** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Valor Típico (teste completo)** | ~300 MB | ~250 MB | ~300 MB |

**Recomendação**: O método híbrido implementado oferece o melhor equilíbrio entre precisão e confiabilidade.

---

**Última atualização**: 17 de Novembro de 2025
