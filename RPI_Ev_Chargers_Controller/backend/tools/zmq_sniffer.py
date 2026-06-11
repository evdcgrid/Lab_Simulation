#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime

import zmq


def describe_payload(payload: bytes) -> str:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return f"binary ({len(payload)} bytes): {payload[:40]!r}"

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return f"text ({len(payload)} bytes): {text[:300]}"

    return f"json ({len(payload)} bytes): {json.dumps(parsed, indent=2, ensure_ascii=False)[:1200]}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect messages from the EV charger ZMQ stream.")
    parser.add_argument("--endpoint", default="tcp://127.0.0.1:3333")
    parser.add_argument("--topic", default="")
    parser.add_argument("--timeout-ms", type=int, default=1000)
    args = parser.parse_args()

    context = zmq.Context.instance()
    socket = context.socket(zmq.SUB)
    socket.connect(args.endpoint)
    socket.setsockopt(zmq.SUBSCRIBE, args.topic.encode("utf-8"))
    socket.setsockopt(zmq.RCVTIMEO, args.timeout_ms)

    print(f"Connected to {args.endpoint}")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            try:
                frames = socket.recv_multipart()
            except zmq.Again:
                print(f"{datetime.now().isoformat(timespec='seconds')} no message")
                continue

            payload = frames[-1] if len(frames) > 1 else frames[0]
            print("-" * 80)
            print(datetime.now().isoformat(timespec="milliseconds"))
            print(f"frames={len(frames)}")
            print(describe_payload(payload))
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        socket.close(linger=0)


if __name__ == "__main__":
    main()

