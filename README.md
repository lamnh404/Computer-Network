# Computer-Network

## P2P Chat (Socket-Based, No Central Server)

This repo now includes a minimal peer-to-peer (P2P) chat feature that creates ad-hoc channels over sockets without relying on the centralized web server. It uses UDP broadcast for peer discovery on the local network and TCP connections for message exchange between peers.

Notes:
- Intended for same-LAN usage; no NAT traversal.
- Gossip with de-duplication — messages are forwarded between peers and delivered once.

### Quick Start

Open two terminals on machines in the same LAN (or on the same machine). Run:

```
python p2p_chat.py --username alice --channel general
```

and in the other:

```
python p2p_chat.py --username bob --channel general
```

Type to send messages. Nodes auto-discover peers on the same channel and connect directly over TCP.

Options:
- `--host` listen address (default `0.0.0.0`)
- `--port` listen port (default `0`, which picks an ephemeral port)

### Embedding as a Library

```
from p2p import Node

def on_message(channel, user, text):
    print(f"[{channel}] {user}: {text}")

node = Node(username="alice", channel="general", on_message=on_message)
node.start()
node.send("hello, world")
# ... later
node.stop()
```

### Limitations
- Browsers cannot open raw TCP sockets; this P2P layer is separate from the existing AJAX web UI.
- Discovery uses UDP broadcast on port 54545, which must be allowed on the LAN.
