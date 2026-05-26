# core/data_forwarder.py
"""
Data Forwarder Service
Subscribes to ZMQ telemetry stream and forwards aggregated data to remote database.

Each converter gets its own endpoint. Data is averaged over 30-second intervals
before being sent to the respective endpoint.
"""

import json
import threading
import time
from datetime import datetime, timezone
from collections import defaultdict
from typing import Optional
import requests
import zmq

from config.constants import SUB_CONNECT
from config.remote_db import (
    ENDPOINTS,
    AGGREGATION_PERIOD,
    RETRY_ATTEMPTS,
    RETRY_DELAY,
    REQUEST_TIMEOUT,
)
from core.data_transformer import transform_to_db_format


class NodeAggregator:
    """Aggregates telemetry data for a single node over time."""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.reset()
    
    def reset(self):
        """Reset aggregation state for a new period."""
        self.samples = defaultdict(list)  # field_name -> [values]
        self.sample_count = 0
        self.period_start = time.time()
    
    def add_sample(self, data: dict):
        """Add a data sample to the aggregator."""
        for key, value in data.items():
            # Only aggregate numeric values
            if isinstance(value, (int, float)):
                self.samples[key].append(value)
        self.sample_count += 1
    
    def get_averages(self) -> Optional[dict]:
        """Calculate and return average values for all fields."""
        if self.sample_count == 0:
            return None
        
        averages = {}
        for key, values in self.samples.items():
            if values:
                averages[key] = sum(values) / len(values)
        
        return averages
    
    def get_period_info(self) -> dict:
        """Get metadata about this aggregation period."""
        return {
            "period_start": datetime.fromtimestamp(self.period_start, tz=timezone.utc).isoformat(),
            "period_end": datetime.now(timezone.utc).isoformat(),
            "sample_count": self.sample_count,
            "duration_seconds": time.time() - self.period_start,
        }


class DataForwarder(threading.Thread):
    """
    Subscribes to ZMQ telemetry and forwards averaged data to remote APIs.
    Each node (converter) gets its data sent to a separate endpoint.
    """

    def __init__(self, zmq_address: str = SUB_CONNECT):
        super().__init__(daemon=True)
        self.zmq_address = zmq_address
        self._stop_event = threading.Event()
        
        # Create aggregators for each node
        self.aggregators = {
            node_id: NodeAggregator(node_id) 
            for node_id in ENDPOINTS.keys()
        }
        
        # Stats
        self.messages_received = 0
        self.messages_sent = 0
        self.send_failures = 0
        
        # Track last send time
        self.last_send_time = time.time()

    def stop(self):
        """Signal the forwarder to stop gracefully."""
        self._stop_event.set()

    def run(self):
        """Main loop: subscribe to ZMQ, aggregate, and forward data."""
        ctx = zmq.Context.instance()
        sub = ctx.socket(zmq.SUB)
        sub.connect(self.zmq_address)
        sub.setsockopt(zmq.SUBSCRIBE, b"")
        sub.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout for recv

        print(f"📡 DataForwarder conectado a {self.zmq_address}")
        print(f"⏱️  Período de agregação: {AGGREGATION_PERIOD}s")
        print(f"🎯 Endpoints configurados para {len(ENDPOINTS)} conversores")

        while not self._stop_event.is_set():
            try:
                # Receive message with timeout (blocking, uses RCVTIMEO)
                raw = sub.recv()
                data = json.loads(raw.decode("utf-8"))
                self._process_message(data)
                
            except zmq.Again:
                # Timeout reached, no message available - this is normal
                pass
            except json.JSONDecodeError as e:
                print(f"⚠️ Erro ao decodificar JSON: {e}")
            except Exception as e:
                print(f"❌ Erro no DataForwarder: {e}")

            # Check if aggregation period has elapsed
            if time.time() - self.last_send_time >= AGGREGATION_PERIOD:
                self._send_aggregated_data()

        # Final send on shutdown
        self._send_aggregated_data(force=True)
        sub.close()
        print("🛑 DataForwarder encerrado.")

    def _process_message(self, data: dict):
        """Process an incoming message and route it to the correct aggregator."""
        self.messages_received += 1
        
        # Determine which node this message belongs to
        # Strategy: Look for node-specific prefixes in the keys (N01_, N02_)
        # or use a heuristic if no prefix is found
        node_id = self._identify_node(data)
        
        if node_id and node_id in self.aggregators:
            self.aggregators[node_id].add_sample(data)

    def _identify_node(self, data: dict) -> Optional[str]:
        """
        Identify which node a message belongs to based on signal names.
        Returns 'N01', 'N02', 'N03', 'N04', 'N05', or None if unknown.
        """
        # Check for node-specific prefixes in keys
        for key in data.keys():
            if key.startswith("N01_"):
                return "N01"
            elif key.startswith("N02_"):
                return "N02"
            elif key.startswith("N03_"):
                return "N03"
            elif key.startswith("N04_"):
                return "N04"
            elif key.startswith("N05_"):
                return "N05"
        
        # If no prefix found, could be a generic message (itfc_v_grid, etc.)
        # In this case, we might need to track which node sent it based on
        # message sequence or other context. For now, return None to skip.
        # 
        # Alternative: If your system sends generic signals, you might want to
        # duplicate them to both nodes or use additional context to identify.
        return None

    def _send_aggregated_data(self, force: bool = False):
        """Send averaged data for each node to its respective endpoint."""
        for node_id, aggregator in self.aggregators.items():
            averages = aggregator.get_averages()
            
            if averages is None and not force:
                continue  # No data to send for this node
            
            if averages:
                period_info = aggregator.get_period_info()
                timestamp = datetime.now(timezone.utc).isoformat()
                
                # Transform flat data to nested database format
                payload = transform_to_db_format(
                    node_id=node_id,
                    timestamp=timestamp,
                    aggregation_info=period_info,
                    averages=averages
                )
                
                # Send to the node's specific endpoint
                endpoint = ENDPOINTS.get(node_id)
                if endpoint:
                    success = self._send_to_api(endpoint, payload, node_id)
                    
                    if success:
                        self.messages_sent += 1
                        print(f"✅ [{node_id}] Enviado: {period_info['sample_count']} amostras agregadas")
                    else:
                        self.send_failures += 1
                        print(f"❌ [{node_id}] Falha no envio")
            
            # Reset aggregator for next period
            aggregator.reset()
        
        # Update last send time
        self.last_send_time = time.time()

    def _send_to_api(self, endpoint: str, payload: dict, node_id: str) -> bool:
        """
        Send payload to remote API with retry logic.
        Returns True on success, False on failure.
        """
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                response = requests.post(
                    endpoint,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Shift2DC-DataForwarder/2.0",
                    },
                )

                if response.status_code in (200, 201, 202):
                    return True
                elif response.status_code == 401:
                    print(f"🔒 [{node_id}] Erro de autenticação (401) - verificar credenciais")
                    return False  # No point in retrying auth errors
                elif response.status_code >= 500:
                    print(f"⚠️ [{node_id}] Erro do servidor ({response.status_code}), tentativa {attempt}/{RETRY_ATTEMPTS}")
                else:
                    print(f"⚠️ [{node_id}] Resposta inesperada: {response.status_code} - {response.text[:200]}")
                    
            except requests.exceptions.Timeout:
                print(f"⏱️ [{node_id}] Timeout na tentativa {attempt}/{RETRY_ATTEMPTS}")
            except requests.exceptions.ConnectionError as e:
                print(f"🔌 [{node_id}] Erro de conexão na tentativa {attempt}/{RETRY_ATTEMPTS}: {e}")
            except Exception as e:
                print(f"❌ [{node_id}] Erro inesperado na tentativa {attempt}/{RETRY_ATTEMPTS}: {e}")

            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)

        return False

    def get_stats(self) -> dict:
        """Return current statistics."""
        aggregator_stats = {
            node_id: {
                "sample_count": agg.sample_count,
                "period_elapsed": time.time() - agg.period_start,
            }
            for node_id, agg in self.aggregators.items()
        }
        
        return {
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent,
            "send_failures": self.send_failures,
            "time_until_next_send": max(0, AGGREGATION_PERIOD - (time.time() - self.last_send_time)),
            "aggregators": aggregator_stats,
        }


def create_forwarder(zmq_address: Optional[str] = None) -> DataForwarder:
    """Factory function to create and return a DataForwarder instance."""
    addr = zmq_address or SUB_CONNECT
    return DataForwarder(zmq_address=addr)
