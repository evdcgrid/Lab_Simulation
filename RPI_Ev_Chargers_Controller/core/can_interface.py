# core/can_interface.py
import can
import cantools
import time 
import struct
from config.constants import (
    BITRATE,
    CHANNEL,
    VOLTAGE_CNTRL,
    STAND_BY,
    POWER_ON,
    CHARGING,
    FAULT_ACK,
)
from config.signals_config import signals


BLOCKED_SDO_WRITES = {
    (0x4200, 0x01),  # Protection mask/configuration, managed by official GUI.
    (0x5000, 0x01),  # Critical fault mask configuration, managed by official GUI.
}


class CANInterface:
    def __init__(self, dbc_file, node_id):
        self.node_id = node_id
        self.db = cantools.database.load_file(dbc_file)
        self.bus = can.interface.Bus(
            interface="socketcan",
            channel="can0",
            receive_own_messages=True,
        )
        # guardar tasks periódicas por nome de mensagem
        self._periodic_tasks = {}
        self.latest_system_state = None
        self.latest_system_state_at = 0.0
        print(f"✅ Conectado ao Kvaser (canal={CHANNEL}, bitrate={BITRATE}) para Node {node_id}")

    def send_message(self, name, signals, period=None):
        """
        name: nome da mensagem no DBC (ex: 'N01_RPDO0')
        signals: dict {nome_sinal: valor}
        period: se None, envia 1x; se float, envia periodicamente em segundos
        """
        msg = self.db.get_message_by_name(name)
        try:
            data = msg.encode(signals)
        except Exception as e:
            required = [s.name for s in msg.signals]
            have = list(signals.keys())
            print(f"❌ EncodeError em '{name}': {e}")
            print(f"   Sinais requeridos pelo DBC: {required}")
            print(f"   Sinais fornecidos: {have}")
            raise

        message = can.Message(
            arbitration_id=msg.frame_id,    # Node ID excuido
            data=data,
            is_extended_id=False,
        )

        if period:
            # se já houver uma task periódica com este nome, pára-a
            previous_task = self._periodic_tasks.pop(name, None)
            if previous_task is not None:
                try:
                    previous_task.stop()
                except Exception as e:
                    print(f"⚠️ Erro a parar task periódica '{name}': {e}")

            task = self.bus.send_periodic(message, period)
            self._periodic_tasks[name] = task
            return task
        else:
            self.bus.send(message)
    """
    def send_message(self, name, signals, period=None):
        msg = self.db.get_message_by_name(name)
        try:
            data = msg.encode(signals)
        except Exception as e:
            required = [s.name for s in msg.signals]
            have = list(signals.keys())
            print(f"❌ EncodeError em '{name}': {e}")
            print(f"   Sinais requeridos pelo DBC: {required}")
            print(f"   Sinais fornecidos: {have}")
            raise

        # Usa o ID exatamente como está no DBC (já vem com N01/N02 embutido)
        message = can.Message(
            arbitration_id=msg.frame_id,
            data=data,
            is_extended_id=False,
        )

        if period:
            return self.bus.send_periodic(message, period)
        else:
            self.bus.send(message)
    """
    def receive_message(self):
        """
        Lê uma mensagem CAN e tenta fazer decode com o DBC.
        Devolve um dicionário pronto para ser enviado por ZMQ.
        """
        msg = self.bus.recv(timeout=0.01)
        if msg is None:
            return None

        try:
            message_def = self.db.get_message_by_frame_id(msg.arbitration_id)
        except Exception:
            return None

        # Publish real telemetry plus RPDO command frames seen on the CAN bus
        # so PlotJuggler can inspect commanded setpoints. The HMI parser
        # ignores RPDO-only frames as telemetry.
        is_tpdo = "_TPDO" in message_def.name
        is_rpdo0 = message_def.name.endswith("_RPDO0") or message_def.name == "RPDO0"
        is_rpdo1 = message_def.name.endswith("_RPDO1") or message_def.name == "RPDO1"
        if not (is_tpdo or is_rpdo0 or is_rpdo1):
            return None

        try:
            # tenta decodificar com o arbitration_id recebido
            decoded = self.db.decode_message(msg.arbitration_id, msg.data)
        except Exception:
            # se não conseguir decodificar, ignora a mensagem
            return None

        decoded["_message_name"] = message_def.name
        decoded["_arbitration_id"] = msg.arbitration_id
        for key, value in decoded.items():
            if key.endswith("_SystemState"):
                try:
                    self.latest_system_state = int(value)
                    self.latest_system_state_at = time.monotonic()
                except (TypeError, ValueError):
                    pass
        return decoded
    
    """
    def receive_message(self):
        
        msg = self.bus.recv(timeout=0.05)
        if msg is None:
            return None

        # OPCIONAL: só tentar decodificar se este DBC conhecer este ID
        try:
            self.db.get_message_by_frame_id(msg.arbitration_id)
        except KeyError:
            # este DBC não tem nenhuma mensagem com este ID -> ignora
            return None

        try:
            # ✅ usar argumentos POSICIONAIS (ou 'frame_id=', não 'arbitration_id=')
            decoded = self.db.decode_message(msg.arbitration_id, msg.data)
        except Exception as e:
            print(f"❌ DecodeError no Node {self.node_id}, ID={msg.arbitration_id}: {e}")
            return None

        # Mantemos as chaves tal e qual (N01_itfc_..., N02_itfc_...)
        # Só acrescentamos metadados úteis
        decoded["arbitration_id"] = msg.arbitration_id
        decoded["node_id"] = self.node_id
        decoded["timestamp"] = time.time()

        print(f"[CAN RX node {self.node_id}] ID={msg.arbitration_id} decoded={decoded}")

        return decoded
    """

    def sdo_download(self, canopen_node_id, index, subindex, value, dtype):
        """
        Envia um SDO expedited download:
        - canopen_node_id: node ID da BMPU (1..127, ex: 0x50)
        - index: ex. 0x5300
        - subindex: ex. 0x0C
        - value: valor Python
        - dtype: "f32", "u32", "u16", "u8"
        """
        if (index, subindex) in BLOCKED_SDO_WRITES:
            raise ValueError(
                f"Blocked SDO write to 0x{index:04X}:{subindex:02X}; "
                "protection masks are managed by the official converter GUI"
            )

        if dtype == "f32":
            data = struct.pack("<f", float(value))
        elif dtype == "u32":
            data = struct.pack("<I", int(value))
        elif dtype == "u16":
            data = struct.pack("<H", int(value))
        elif dtype == "u8":
            data = struct.pack("<B", int(value))
        else:
            raise ValueError(f"Tipo de dados não suportado: {dtype}")

        n = len(data)
        if n == 4:
            cs = 0x23  # expedited, 4 bytes
        elif n == 2:
            cs = 0x2B  # expedited, 2 bytes
        elif n == 1:
            cs = 0x2F  # expedited, 1 byte
        else:
            raise ValueError("Tamanho inválido para expedited SDO")

        payload = bytearray(8)
        payload[0] = cs
        payload[1] = index & 0xFF
        payload[2] = (index >> 8) & 0xFF
        payload[3] = subindex & 0xFF
        payload[4:4+n] = data

        cob_id = 0x600 + canopen_node_id  # client->server SDO

        msg = can.Message(
            arbitration_id=cob_id,
            data=bytes(payload),
            is_extended_id=False,
        )
        self.bus.send(msg)



def build_rpdo0_payload(node: str, base: dict) -> dict:
    """
    Constrói o payload de RPDO0 respeitando os valores definidos em config.signals_config.

    - 'node' é "N01" ou "N02"
    - 'base' deve conter pelo menos {f"{node}_itfc_pfc_state_request": <valor>}
      (STAND_BY, POWER_ON, CHARGING ou FAULT_ACK)
    """

    state_key = f"{node}_itfc_pfc_state_request"
    state_val = base.get(state_key)

    node_cfg = signals.get(node, {})
    rpdo0_cfg = node_cfg.get("RPDO0", {})

    # Escolher o template certo com base no estado
    if state_val == POWER_ON:
        template = rpdo0_cfg.get("power_on", {})
    elif state_val == CHARGING:
        template = rpdo0_cfg.get("charging", {})
    elif state_val == STAND_BY or state_val is None:
        template = rpdo0_cfg.get("standby", {})
    elif state_val == FAULT_ACK:
        # Não tens um perfil "fault_ack" em signals_config,
        # por isso usamos o de standby e trocamos só o state_request.
        template = rpdo0_cfg.get("standby", {})
    else:
        # fallback seguro: standby
        template = rpdo0_cfg.get("standby", {})

    # Começa no template oficial e aplica por cima o que vier no base
    payload = template.copy()
    payload.update(base)

    return payload
