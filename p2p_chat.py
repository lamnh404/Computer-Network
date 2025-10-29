import argparse
import threading
import sys
from p2p import Node


def main():
    parser = argparse.ArgumentParser(
        prog="p2p_chat",
        description="Simple P2P chat over sockets (LAN discovery)",
    )
    parser.add_argument("--username", required=True, help="Your username")
    parser.add_argument("--channel", required=True, help="Channel (room) name")
    parser.add_argument("--host", default="0.0.0.0", help="Listen host (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=0, help="Listen port (0 = auto)")

    args = parser.parse_args()

    def on_message(channel: str, user: str, text: str):
        print(f"[{channel}] {user}: {text}")

    node = Node(
        username=args.username,
        channel=args.channel,
        listen_host=args.host,
        listen_port=args.port,
        on_message=on_message,
    )
    host, port = node.start()
    print(f"[P2P] Node started on {host}:{port} in channel '{args.channel}' as {args.username}")
    print("[P2P] Type messages and press Enter to send. Ctrl+C to quit.")

    try:
        for line in sys.stdin:
            text = line.strip()
            if not text:
                continue
            node.send(text)
    except KeyboardInterrupt:
        pass
    finally:
        print("\n[P2P] Shutting down...")
        node.stop()


if __name__ == "__main__":
    main()

