import zmq
from config.constants import PUB_BIND
from config.constants import SUB_CONNECT

def create_publisher():
    ctx = zmq.Context()
    socket = ctx.socket(zmq.PUB)
    socket.bind(PUB_BIND)
    print(f"✅ ZMQ publisher ativo em {PUB_BIND}")
    return socket