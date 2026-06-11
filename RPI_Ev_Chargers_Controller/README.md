# Shift2DC - Converter Monitoring System

Sistema de monitorização e envio de dados de conversores DC-DC para base de dados remota.

---

## Visão Geral

Este sistema:
- Lê dados de 5 conversores DC-DC via CAN bus (interface Kvaser)
- Agrega dados em períodos de 30 segundos
- Envia médias para endpoints remotos separados
- Fornece GUI para controlo e monitorização
- Executa automaticamente na Raspberry Pi


## Estrutura do Projeto

```
Shift2DC/
├── main.py                          # Programa principal (CAN + GUI + Forwarder)
├── run_forwarder.py                 # Forwarder standalone
├── setup_raspberry.sh               # 🔧 Setup automático para Raspberry Pi
├── install_service.sh               # 🔧 Instalar como serviço systemd
│
├── config/
│   ├── constants.py                 # Configurações CAN
│   ├── signals_config.py            # Sinais e comandos
│   ├── remote_db.py                 # ⚠️ Credenciais API (não commitar!)
│   └── remote_db.py.example         # Template de credenciais
│
├── core/
│   ├── can_interface.py             # Interface CAN bus
│   ├── message_sender.py            # Envio de comandos
│   ├── message_receiver.py          # Receção de telemetria
│   ├── zmq_publisher.py             # Pub/Sub interno
│   ├── data_forwarder.py            # Forwarder para API remota
│   ├── data_transformer.py          # Transformação flat → nested
│   ├── gui.py                       # Interface gráfica
│   └── fault_handler.py             # Gestão de falhas
│
├── test_mock_publisher.py           # 🧪 Simular dados (teste sem hardware)
├── test_view_output.py              # 🧪 Ver formato JSON enviado
│
├── *.dbc                            # Ficheiros DBC (configuração CAN)
│
└── Documentação/
    ├── README.md                   

```

---

## Modos de Operação

### 1. Sistema Completo (CAN + GUI + Forwarder)
```bash
python main.py --forward-data
```
- Lê CAN bus
- Mostra GUI de controlo
- Envia dados para API

### 2. Forwarder Standalone
```bash
python run_forwarder.py
```
- Só envia dados (sem GUI, sem controlo CAN)
- Útil para correr em background

### 2b. ZMQ Server Headless (CAN -> ZMQ, sem GUI)
```bash
python run_zmq_server.py
```
- Lê CAN bus
- Publica telemetria via ZMQ em `tcp://*:3333`
- Escuta comandos da HMI em `tcp://*:3334` e envia setpoints por CAN
- Não abre a GUI Tkinter

Escolher só alguns nós:
```bash
python run_zmq_server.py --nodes N01
python run_zmq_server.py --nodes N03,N04
```

Se só quiseres escutar/decodificar sem enviar a sequência inicial CAN:
```bash
python run_zmq_server.py --nodes N01 --no-startup-sequence
```

Para desligar o canal de comandos da HMI:
```bash
python run_zmq_server.py --nodes N01 --no-command-server
```

### 3. Teste Sem Hardware
```bash
python test_mock_publisher.py &    # Terminal 1
python test_view_output.py         # Terminal 2
```
- Simula dados dos conversores
- Testa integração API

---

## ⚙️ Configuração

### Credenciais API

As credenciais **já estão configuradas** em `config/remote_db.py`:

- **N01 - ConverterBAT**: Conversor de bateria
- **N02 - ConverterPV**: Conversor fotovoltaico
- **N03 - ConverterEV1**: Conversor veículo elétrico 1
- **N04 - ConverterEV2**: Conversor veículo elétrico 2
- **N05 - ConverterACDC**: Conversor AC-DC

⚠️ **IMPORTANTE**: Este ficheiro está no `.gitignore` e **nunca deve ser commitado**!

### Alterar Período de Agregação

Editar `config/remote_db.py`:
```python
AGGREGATION_PERIOD = 30.0  # segundos
```

### Configurar CAN Bus

Editar `config/constants.py`:
```python
BITRATE = 500000  # 500 kbps
CHANNEL = 0       # Canal Kvaser
```

---

## 📊 Formato dos Dados

### Estrutura Enviada (a cada 30s)

```json
{
  "timestamp": "2025-12-15T15:30:45+00:00",
  "node": "N01",
  "aggregation": {
    "sample_count": 287,
    "duration_seconds": 30.0
  },
  "L1": { "V": 230.5, "I": 15.2, "P": 1500.0, "Q": 200.0 },
  "L2": { "V": 231.2, "I": 14.8, "P": 1450.0, "Q": 180.0 },
  "L3": { "V": 230.8, "I": 15.5, "P": 1550.0, "Q": 220.0 },
  "grid": { "V": 230.2, "I": 45.5, "P": 4500.0, "Q": 600.0 },
  "battery": { "V": 1485.3, "I": 302.5, "P": 4490.0 },
  "status": { ... },
  "flags": { ... }
}
```

Detalhes completos: **[JSON_FORMAT_FOR_LUIS.md](JSON_FORMAT_FOR_LUIS.md)**

---

## 🔧 Dependências

### Sistema
- Python 3.7+
- Kvaser CAN drivers (para hardware real)

### Python (instaladas automaticamente)
- `python-can` - CAN bus
- `cantools` - Parsing DBC
- `pyzmq` - Pub/Sub interno
- `requests` - HTTP API

---

## 🧪 Testing

### Teste 1: Mock Data (Sem Hardware)
```bash
source venv/bin/activate
python test_mock_publisher.py &
python test_view_output.py
```

### Teste 2: API Connection
```bash
source venv/bin/activate
python run_forwarder.py --stats-interval 30
```

### Teste 3: Sistema Completo
```bash
source venv/bin/activate
python main.py --forward-data
```

---

## 📱 Comandos Úteis

### Serviço Systemd
```bash
sudo systemctl start shift2dc      # Iniciar
sudo systemctl stop shift2dc       # Parar
sudo systemctl status shift2dc     # Estado
sudo systemctl restart shift2dc    # Reiniciar
sudo journalctl -u shift2dc -f     # Logs em tempo real
```

### Manual
```bash
# Ativar ambiente virtual
source venv/bin/activate

# Executar
python main.py --forward-data

# Ver estatísticas
python run_forwarder.py --stats-interval 30
```

---

## 🔒 Segurança

- ✅ Credenciais em ficheiro separado (`.gitignore`)
- ✅ Template sem credenciais para partilha
- ✅ Serviço systemd com privilégios limitados
- ✅ HTTPS para comunicação com API


---

## 🐛 Troubleshooting

### Problema Comum #1: "No module named 'can'"
**Solução**: Ativar ambiente virtual
```bash
source venv/bin/activate
```

---

## EV Charger HMI local

Foi adicionada uma HMI local em `backend/` + `frontend/` para monitorizar e operar carregadores EV a partir do Raspberry Pi Touch Display 2. A HMI nao substitui o publisher ZMQ existente: o PlotJuggler pode continuar ligado em paralelo e o backend da HMI e apenas mais um subscriber do mesmo stream.

Arquitetura:

```text
Hardware / Charger interface
  -> script Python ZMQ existente
  -> ZMQ PUB
     -> PlotJuggler
     -> FastAPI backend da HMI
        -> REST API + WebSocket
        -> React frontend em Chromium kiosk
```

### Backend

```bash
cd backend
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Por defeito o backend arranca com mock data (`TELEMETRY_SOURCE=mock`) para testar o dashboard sem hardware. Para ligar ao publisher real existente, editar `backend/.env`:

```env
TELEMETRY_SOURCE=zmq
ZMQ_ENDPOINT=tcp://127.0.0.1:3333
ZMQ_TOPIC=
COMMAND_PUBLISHER=zmq
ZMQ_COMMAND_ENDPOINT=tcp://127.0.0.1:3334
```

Se o teu script passar a publicar noutro porto, por exemplo `tcp://127.0.0.1:5555`, basta alterar `ZMQ_ENDPOINT`.
Os comandos usam um canal separado: a telemetria continua em `3333`, e o setpoint de carga vai para o `run_zmq_server.py` pelo endpoint `3334`.

### Frontend

Para producao no Raspberry Pi, usar o build estatico servido pelo FastAPI:

```bash
cd frontend
npm install
npm run build
cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Abrir `http://127.0.0.1:8000`. Assim nao e preciso correr o Vite no Pi.

Para desenvolvimento, com hot reload:

```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

Abrir `http://127.0.0.1:5173`. O Vite faz proxy de `/api` e `/ws` para o backend em `127.0.0.1:8000`.

### Debug ZMQ

```bash
cd backend
source .venv/bin/activate
python tools/zmq_sniffer.py --endpoint tcp://127.0.0.1:3333
```

O sniffer imprime se cada mensagem parece JSON, texto ou binario, ajudando a adaptar `backend/app/telemetry/parsers.py` ao formato real.

### Limite de potencia

O backend e a autoridade final para setpoints. Configurar limites globais e por carregador em `backend/.env`:

```env
CHARGER_MAX_POWER_KW=6.6
CHARGER_POWER_LIMITS=charger_1=6.6,charger_2=6.6,N03=11.04,N04=11.04
```

Se alguem pedir acima do limite, o backend devolve HTTP 400, nao publica comando e regista evento. Exemplo: `Potência pedida 8.0 kW excede o máximo permitido de 6.6 kW`.

Na pagina de parametros, a potencia em kW e convertida para watts e enviada no mesmo sinal da GUI antiga: `Nxx_itfc_active_power_setpoint_W` no `RPDO1`. Exemplo: `3.5 kW` envia `3500 W`.
Os limites de corrente tambem sao configuraveis e seguem no mesmo `RPDO1`: `Nxx_itfc_i_charge_limit` e `Nxx_itfc_i_discharge_limit`.

### Servico systemd do backend

```bash
sudo cp backend/ev-charger-hmi.service.example /etc/systemd/system/ev-charger-hmi.service
sudo systemctl daemon-reload
sudo systemctl enable ev-charger-hmi
sudo systemctl start ev-charger-hmi
sudo journalctl -u ev-charger-hmi -f
```

### Chromium kiosk

Exemplo simples para testar:

```bash
chromium-browser --kiosk --noerrdialogs --disable-infobars http://127.0.0.1:8000
```

Para arranque automatico, adicionar esse comando ao autostart do ambiente grafico do Raspberry Pi ou criar um servico user systemd depois de o frontend estar disponivel.

### Ecran em landscape

No Raspberry Pi OS atual, usar o painel grafico de configuracao de ecran quando disponivel. Em instalacoes headless/Wayland, a rotacao normalmente e feita com `wlr-randr`; em instalacoes legacy pode ser necessario ajustar `/boot/firmware/config.txt`. Confirmar o nome real da saida (`DSI-1`, `HDMI-A-1`, etc.) antes de persistir a configuracao.

### Problema Comum #2: "Permission denied" no CAN
**Solução**: Adicionar user ao grupo
```bash
sudo usermod -a -G dialout $USER
# Logout e login novamente
```

### Problema Comum #3: "Connection refused"
**Solução**: Verificar internet
```bash
ping shift2dc.prsma.com
```

Mais detalhes: **[RASPBERRY_PI_DEPLOYMENT.md](RASPBERRY_PI_DEPLOYMENT.md#troubleshooting)**

---

## 🔄 Workflow Típico

### Development (no teu Mac)
```bash
# Fazer alterações ao código
git add .
git commit -m "Descrição"
git push
```

### Deployment (na Raspberry)
```bash
# Atualizar código
cd ~/Shift2DC
cp config/remote_db.py config/remote_db.py.backup
git pull
cp config/remote_db.py.backup config/remote_db.py

# Reiniciar serviço
sudo systemctl restart shift2dc

# Verificar
sudo journalctl -u shift2dc -f
```

---

## ✅ System Status Checklist

Sistema OK se:
- ✅ Serviço está "active (running)"
- ✅ Logs mostram "Enviados X registos" a cada 30s
- ✅ Dados aparecem na plataforma shift2dc.prsma.com
- ✅ Sem erros críticos nos logs


---

## 📝 Changelog

### v2.0 - Database Integration (Dez 2025)
- ✅ Agregação de 30 segundos
- ✅ Endpoints separados por conversor
- ✅ Transformação para estrutura nested
- ✅ Scripts de deployment Raspberry Pi
- ✅ Serviço systemd

### v1.0 - Initial System
- ✅ CAN bus communication
- ✅ GUI control panel
- ✅ ZMQ pub/sub
- ✅ DBC file support
