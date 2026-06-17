#!/usr/bin/env python3
from __future__ import annotations

import argparse
import errno
import signal
import time

from config.constants import COMMAND_BIND, NODES, SUB_CONNECT
from core.can_interface import CANInterface
from core.data_forwarder import create_forwarder
from core.message_receiver import MessageReceiver
from core.message_sender import MessageSender
from core.zmq_command_server import ZmqCommandServer
from core.zmq_publisher import create_publisher


def parse_nodes(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    nodes = {item.strip() for item in raw.split(",") if item.strip()}
    return nodes or None


def selected_node_configs(nodes: set[str] | None):
    if nodes is None:
        return NODES

    known = {node_name for node_name, *_ in NODES}
    unknown = sorted(nodes - known)
    if unknown:
        raise SystemExit(f"Unknown node(s): {', '.join(unknown)}. Known nodes: {', '.join(sorted(known))}")

    return [config for config in NODES if config[0] in nodes]


def is_missing_can_device(exc: OSError) -> bool:
    return exc.errno == errno.ENODEV or "No such device" in str(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Shift2DC CAN -> ZMQ publisher without GUI.")
    parser.add_argument(
        "--nodes",
        help="Comma-separated nodes to open, for example N01 or N03,N04. Defaults to all configured nodes.",
    )
    parser.add_argument(
        "--no-startup-sequence",
        action="store_true",
        help="Do not send the CAN startup heartbeat/sync/RPDO sequence.",
    )
    parser.add_argument(
        "--forward-data",
        action="store_true",
        help="Also start the existing remote database forwarder.",
    )
    parser.add_argument(
        "--no-command-server",
        action="store_true",
        help="Do not listen for HMI commands/setpoints.",
    )
    parser.add_argument(
        "--command-endpoint",
        default=COMMAND_BIND,
        help=f"ZMQ REP endpoint for HMI commands. Defaults to {COMMAND_BIND}.",
    )
    args = parser.parse_args()

    node_configs = selected_node_configs(parse_nodes(args.nodes))
    socket = create_publisher()

    iface_map = {}
    unavailable_nodes = []
    for node_name, dbc_file, node_id, _canopen_node_id in node_configs:
        try:
            iface_map[node_name] = CANInterface(dbc_file, node_id)
        except OSError as exc:
            if not is_missing_can_device(exc):
                raise
            unavailable_nodes.append(node_name)
            print(
                f"⚠️ CAN indisponível para {node_name}: {exc}. "
                "A HMI/backend continuam ativos, mas este nó ficará sem telemetria."
            )

    receiver = None
    if iface_map:
        receiver = MessageReceiver(list(iface_map.values()), socket)
        receiver.start()
    else:
        print("⚠️ Nenhuma interface CAN disponível. ZMQ fica ativo para o backend/HMI, mas não haverá telemetria CAN.")

    command_server = None
    if not args.no_command_server and iface_map:
        command_server = ZmqCommandServer(iface_map, args.command_endpoint)
        command_server.start()
    elif not args.no_command_server:
        print("⚠️ Command server não iniciado porque não há nós CAN disponíveis.")

    if not args.no_startup_sequence and iface_map:
        if "N01" not in iface_map:
            print("⚠️ Startup sequence skipped because N01 is not selected.")
        else:
            MessageSender(iface_map).startup_sequence()
    elif not args.no_startup_sequence:
        print("⚠️ Sequência de arranque CAN ignorada porque não há nós CAN disponíveis.")

    forwarder = None
    if args.forward_data:
        forwarder = create_forwarder()
        forwarder.start()
        print("📡 Data forwarder ativo.")

    print("✅ ZMQ server/headless publisher running.")
    if unavailable_nodes:
        print(f"⚠️ Nós sem CAN: {', '.join(unavailable_nodes)}")
    print(f"📡 Subscribers should connect to {SUB_CONNECT}")
    if command_server:
        print(f"🎛️ HMI commands should connect to {args.command_endpoint.replace('*', '127.0.0.1')}")
    print("   Press Ctrl+C to stop.")

    stopped = False

    def handle_stop(_signum, _frame):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    try:
        while not stopped:
            time.sleep(0.5)
    finally:
        if forwarder:
            forwarder.stop()
            forwarder.join(timeout=5)
            print("📊 Forwarder stats:", forwarder.get_stats())
        if command_server:
            command_server.stop()
        socket.close(linger=0)
        print("🛑 ZMQ server stopped.")


if __name__ == "__main__":
    main()
