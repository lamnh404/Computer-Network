import socket
import threading
import json
import time
import uuid
from typing import Callable, Dict, Optional, Set, Tuple


class Node:
    """
    Minimal peer-to-peer chat node using sockets.

    - UDP broadcast for peer discovery on LAN per channel
    - TCP connections for message exchange between peers
    - Flood-with-dedup gossip to propagate messages across peers

    This is intended for same-LAN demos and does not attempt NAT traversal.
    """

    DISCOVERY_PORT = 54545
    DISCOVERY_INTERVAL = 3.0
    RECONNECT_INTERVAL = 5.0

    def __init__(
        self,
        username: str,
        channel: str,
        listen_host: str = "0.0.0.0",
        listen_port: int = 0,
        on_message: Optional[Callable[[str, str, str], None]] = None,
        on_control: Optional[Callable[[str, str, dict], None]] = None,
        on_direct: Optional[Callable[[str, str, str], None]] = None,
    ) -> None:
        self.username = username
        self.channel = channel
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.on_message = on_message
        self.on_control = on_control
        self.on_direct = on_direct

        self.peer_id = f"{username}-{uuid.uuid4().hex[:8]}"
        self._stop = threading.Event()

        self._tcp_server_sock: Optional[socket.socket] = None
        self._tcp_server_thread: Optional[threading.Thread] = None

        # peer_id -> (sock, addr)
        self._peers: Dict[str, Tuple[socket.socket, Tuple[str, int]]] = {}
        # peer_id -> username and reverse
        self._peer_usernames: Dict[str, str] = {}
        self._user_to_peer: Dict[str, str] = {}
        self._peers_lock = threading.Lock()

        # Track in-progress or recent connection attempts by (ip,port)
        self._connecting: Set[Tuple[str, int]] = set()

        # Message deduplication
        self._seen_messages: Set[str] = set()
        self._seen_lock = threading.Lock()

        # Discovery
        self._udp_rx_thread: Optional[threading.Thread] = None
        self._udp_tx_thread: Optional[threading.Thread] = None

    # ---------- Public API ----------
    def start(self) -> Tuple[str, int]:
        """Start TCP listener and UDP discovery threads.

        Returns the bound address for the TCP listener.
        """
        # TCP server
        self._tcp_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._tcp_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._tcp_server_sock.bind((self.listen_host, self.listen_port))
        self._tcp_server_sock.listen(32)

        bound = self._tcp_server_sock.getsockname()
        self.listen_host, self.listen_port = bound[0], bound[1]

        self._tcp_server_thread = threading.Thread(
            target=self._accept_loop, name="p2p-tcp-accept", daemon=True
        )
        self._tcp_server_thread.start()

        # UDP discovery threads
        self._udp_rx_thread = threading.Thread(
            target=self._discovery_rx_loop, name="p2p-udp-rx", daemon=True
        )
        self._udp_rx_thread.start()

        self._udp_tx_thread = threading.Thread(
            target=self._discovery_tx_loop, name="p2p-udp-tx", daemon=True
        )
        self._udp_tx_thread.start()

        return bound

    def stop(self) -> None:
        """Stop all threads and close sockets."""
        self._stop.set()
        try:
            if self._tcp_server_sock:
                self._tcp_server_sock.close()
        except Exception:
            pass
        with self._peers_lock:
            for pid, (s, _) in list(self._peers.items()):
                try:
                    s.close()
                except Exception:
                    pass
            self._peers.clear()

    def send(self, text: str) -> None:
        """Broadcast a chat message to all connected peers in the channel."""
        msg = {
            "type": "chat",
            "id": uuid.uuid4().hex,
            "channel": self.channel,
            "from": self.username,
            "peer_id": self.peer_id,
            "text": text,
            "ts": time.time(),
            "hops": 0,
        }
        self._mark_seen(msg["id"])  # mark before send to avoid echo
        self._fanout(msg)
        # deliver locally
        if self.on_message:
            try:
                self.on_message(self.channel, self.username, text)
            except Exception:
                pass

    def status(self) -> dict:
        """Return basic runtime status for diagnostics."""
        with self._peers_lock:
            peer_count = len(self._peers)
        return {
            "username": self.username,
            "channel": self.channel,
            "listen_host": self.listen_host,
            "listen_port": self.listen_port,
            "peer_id": self.peer_id,
            "peers": peer_count,
        }

    def send_control(self, to_username: str, ctrl: str, data: Optional[dict] = None) -> bool:
        """Send a control message to a specific peer by username.

        Returns True if a direct socket was found and message queued.
        """
        pid = self._user_to_peer.get(to_username)
        if not pid:
            return False
        with self._peers_lock:
            entry = self._peers.get(pid)
        if not entry:
            return False
        s, _ = entry
        msg = {
            "type": "control",
            "ctrl": ctrl,
            "from": self.username,
            "to": to_username,
            "channel": self.channel,
            "data": data or {},
            "ts": time.time(),
        }
        try:
            s.sendall((json.dumps(msg) + "\n").encode("utf-8"))
            return True
        except Exception:
            return False

    def send_direct(self, to_username: str, text: str) -> bool:
        """Send a direct chat message to a specific peer over its socket."""
        pid = self._user_to_peer.get(to_username)
        if not pid:
            return False
        with self._peers_lock:
            entry = self._peers.get(pid)
        if not entry:
            return False
        s, _ = entry
        msg = {
            "type": "direct_chat",
            "from": self.username,
            "to": to_username,
            "channel": self.channel,
            "text": text,
            "ts": time.time(),
        }
        try:
            s.sendall((json.dumps(msg) + "\n").encode("utf-8"))
            return True
        except Exception:
            return False

    # ---------- Internals ----------
    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                conn, addr = self._tcp_server_sock.accept()
                t = threading.Thread(
                    target=self._peer_conn_loop,
                    args=(conn, addr, None),
                    name=f"p2p-peer-{addr[0]}:{addr[1]}",
                    daemon=True,
                )
                t.start()
            except OSError:
                break
            except Exception:
                continue

    def _peer_conn_loop(self, conn: socket.socket, addr, init_hello: Optional[dict]) -> None:
        # Accept short timeout for initial hello, then switch to blocking
        conn.settimeout(10.0)
        f = conn.makefile("rwb")
        try:
            # Send hello if outbound
            if init_hello is not None:
                f.write((json.dumps(init_hello) + "\n").encode("utf-8"))
                f.flush()

            peer_id = None
            peer_username = None
            # Expect hello
            line = f.readline()
            if not line:
                return
            hello = json.loads(line.decode("utf-8"))
            if hello.get("type") != "hello" or hello.get("channel") != self.channel:
                return
            peer_id = hello.get("peer_id")
            peer_username = hello.get("username")

            # If we initiated, we already sent hello; else reply
            if init_hello is None:
                my_hello = {
                    "type": "hello",
                    "channel": self.channel,
                    "peer_id": self.peer_id,
                    "username": self.username,
                }
                f.write((json.dumps(my_hello) + "\n").encode("utf-8"))
                f.flush()

            # Register peer
            with self._peers_lock:
                self._peers[peer_id] = (conn, addr)
                if peer_username:
                    self._peer_usernames[peer_id] = peer_username
                    self._user_to_peer[peer_username] = peer_id

            # Switch to blocking mode for long-lived message loop
            try:
                conn.settimeout(None)
            except Exception:
                pass

            # Loop messages
            while not self._stop.is_set():
                line = f.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line.decode("utf-8"))
                except Exception:
                    continue
                self._handle_message(msg, from_peer=peer_id)
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
            if peer_id:
                with self._peers_lock:
                    self._peers.pop(peer_id, None)
                    if peer_id in self._peer_usernames:
                        uname = self._peer_usernames.pop(peer_id, None)
                        if uname and self._user_to_peer.get(uname) == peer_id:
                            self._user_to_peer.pop(uname, None)

    def _connect_to_peer(self, host: str, port: int) -> None:
        key = (host, port)
        if key in self._connecting:
            return
        self._connecting.add(key)
        try:
            s = socket.create_connection((host, port), timeout=5.0)
            hello = {
                "type": "hello",
                "channel": self.channel,
                "peer_id": self.peer_id,
                "username": self.username,
            }
            t = threading.Thread(
                target=self._peer_conn_loop, args=(s, (host, port), hello), daemon=True
            )
            t.start()
        except Exception:
            # will retry on future discovery
            pass
        finally:
            self._connecting.discard(key)

    def _handle_message(self, msg: dict, from_peer: Optional[str]) -> None:
        mtype = msg.get("type")
        if mtype == "chat":
            # Deduplicate
            mid = msg.get("id")
            if not mid or self._is_seen(mid):
                return
            self._mark_seen(mid)

            # Deliver locally
            if self.on_message and msg.get("channel") == self.channel:
                try:
                    self.on_message(msg.get("channel"), msg.get("from"), msg.get("text"))
                except Exception:
                    pass

            # Gossip forward to other peers, bump hops
            msg["hops"] = (msg.get("hops") or 0) + 1
            self._fanout(msg, exclude_peer=from_peer)
        elif mtype == "control":
            if msg.get("to") == self.username:
                if self.on_control:
                    try:
                        self.on_control(msg.get("from"), msg.get("ctrl"), msg.get("data") or {})
                    except Exception:
                        pass
        elif mtype == "direct_chat":
            if msg.get("to") == self.username:
                if self.on_direct:
                    try:
                        self.on_direct(msg.get("from"), self.username, msg.get("text"))
                    except Exception:
                        pass

    def _fanout(self, msg: dict, exclude_peer: Optional[str] = None) -> None:
        payload = (json.dumps(msg) + "\n").encode("utf-8")
        with self._peers_lock:
            items = list(self._peers.items())
        for pid, (s, _) in items:
            if exclude_peer and pid == exclude_peer:
                continue
            try:
                s.sendall(payload)
            except Exception:
                # Drop dead peers
                with self._peers_lock:
                    try:
                        s.close()
                    except Exception:
                        pass
                    self._peers.pop(pid, None)

    # ---------- Discovery ----------
    def _discovery_tx_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(1.0)
        payload = {
            "type": "discover",
            "channel": self.channel,
            "peer_id": self.peer_id,
            "username": self.username,
        }
        while not self._stop.is_set():
            payload["tcp_port"] = self.listen_port
            try:
                sock.sendto(
                    json.dumps(payload).encode("utf-8"),
                    ("255.255.255.255", self.DISCOVERY_PORT),
                )
            except Exception:
                pass
            time.sleep(self.DISCOVERY_INTERVAL)

    def _discovery_rx_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", self.DISCOVERY_PORT))
        except Exception:
            # If bind fails, discovery won't work; continue without
            return
        sock.settimeout(1.0)
        while not self._stop.is_set():
            try:
                data, (host, _) = sock.recvfrom(4096)
            except socket.timeout:
                continue
            except Exception:
                break
            try:
                msg = json.loads(data.decode("utf-8"))
            except Exception:
                continue
            if (
                msg.get("type") == "discover"
                and msg.get("channel") == self.channel
                and msg.get("peer_id") != self.peer_id
            ):
                tcp_port = msg.get("tcp_port")
                if isinstance(tcp_port, int) and tcp_port > 0:
                    # attempt connection (idempotent guard is in _connect_to_peer)
                    self._connect_to_peer(host, int(tcp_port))

    # ---------- Dedup helpers ----------
    def _is_seen(self, mid: str) -> bool:
        with self._seen_lock:
            return mid in self._seen_messages

    def _mark_seen(self, mid: str) -> None:
        with self._seen_lock:
            self._seen_messages.add(mid)
