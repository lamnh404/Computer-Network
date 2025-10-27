#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
"""
start_sampleapp
~~~~~~~~~~~~~~~~~

This module provides a sample RESTful web application using the WeApRous framework.

It defines basic route handlers and launches a TCP-based backend server to serve
HTTP requests. The application includes authentication, login endpoints, and
can be configured via command-line arguments.
"""

import json
import socket
import threading
import argparse
from datetime import datetime

from daemon.weaprous import WeApRous
from daemon.utils import load_html_file, parse_form_data, render_routes_page

PORT = 9000  # Default port

VALID_USERNAME = "admin"
VALID_PASSWORD = "password"

app = WeApRous()

# Thread-safe peer tracking
peer_lock = threading.Lock()
active_peers = {}  # {peer_id: {'ip': ..., 'port': ..., 'last_seen': ...}}

# Message storage per channel
messages_lock = threading.Lock()
channel_messages = {'general': []}  # {channel_name: [messages]}

# Try to load index.html from file, fallback to hardcoded version
INDEX_PAGE = load_html_file('www/index.html')
UNAUTHORIZED_PAGE = load_html_file('www/unauthorized.html')
LOGIN_FORM_PAGE = load_html_file('www/login.html')


def get_local_ip():
    """Get local IP address of the machine"""
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"


def render_html_with_data(peer_id, peer_ip, peer_port, server_url, status_class='', status_text='Not Connected',
                          extra_message=''):
    """Helper function to render HTML with current state"""
    with peer_lock:
        # Build peer list HTML
        peer_list_html = ""
        peer_count = len(active_peers) - 1  # Exclude self

        if peer_count <= 0:
            peer_list_html = '<li class="peer-item"><span style="color: #95a5a6;">No peers connected</span></li>'
        else:
            for pid, info in active_peers.items():
                if pid != peer_id:
                    peer_list_html += f'''<li class="peer-item">
                        <span class="peer-status"></span>
                        <div>
                            <div>{pid}</div>
                            <span class="peer-details">{info['ip']}:{info['port']}</span>
                        </div>
                    </li>'''

    # Build messages HTML
    with messages_lock:
        messages_html = ""
        if 'general' in channel_messages and channel_messages['general']:
            for msg in channel_messages['general'][-50:]:  # Show last 50 messages
                is_own = msg['peer_id'] == peer_id
                own_class = ' own' if is_own else ''
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')
                messages_html += f'''<div class="message{own_class}">
                    <div class="message-header">
                        <span class="message-sender">{msg['peer_id']}</span>
                        <span class="message-time">{timestamp}</span>
                    </div>
                    <div class="message-content">{msg['message']}</div>
                </div>'''

        if extra_message:
            messages_html += f'<div class="system-message">{extra_message}</div>'

        if not messages_html:
            messages_html = '<div class="system-message">Welcome to P2P Chat! Connect to start chatting.</div>'

    # Load and render HTML
    html = load_html_file('www/index.html')
    html = html.replace('{{peer_id}}', peer_id)
    html = html.replace('{{peer_ip}}', peer_ip)
    html = html.replace('{{peer_port}}', str(peer_port))
    html = html.replace('{{server_url}}', server_url)
    html = html.replace('{{peer_count}}', str(max(0, peer_count)))
    html = html.replace('{{peer_list}}', peer_list_html)
    html = html.replace('{{status_class}}', status_class)
    html = html.replace('{{status_text}}', status_text)
    html = html.replace('{{messages}}', messages_html)

    return html


@app.route('/submit-info', methods=['POST'])
def submit_info(req):
    """
    Handle peer registration and network connection
    """
    body = req.body if hasattr(req, 'body') else {}
    print(f"[SampleApp] Received peer registration: {body}")

    data = parse_form_data(body)
    peer_id = data.get('peer_id')
    peer_ip = data.get('peer_ip')
    peer_port = data.get('peer_port')
    server_url = data.get('server_url', '192.168.1.9:8080')

    with peer_lock:
        active_peers[peer_id] = {
            'ip': peer_ip,
            'port': peer_port,
            'last_seen': datetime.now().isoformat()
        }

    print(f"[SampleApp] Peer registered: {peer_id} at {peer_ip}:{peer_port}")
    print(f"[SampleApp] Total active peers: {len(active_peers)}")

    html = render_html_with_data(
        peer_id, peer_ip, peer_port, server_url,
        status_class='connected',
        status_text='Connected to Network',
        extra_message=f'✓ Successfully connected to network as {peer_id}'
    )

    response_headers = {'Content-Type': 'text/html; charset=utf-8'}
    return (200, response_headers, html)


@app.route('/get-list', methods=['POST'])
def get_list(req):
    """Get list of peers and return updated HTML"""
    body = req.body if hasattr(req, 'body') else {}
    data = parse_form_data(body)

    peer_id = data.get('peer_id')
    peer_ip = data.get('peer_ip')
    peer_port = data.get('peer_port')
    server_url = data.get('server_url', '192.168.1.9:8080')

    peer_count = len(active_peers) - 1

    html = render_html_with_data(
        peer_id, peer_ip, peer_port, server_url,
        status_class='connected',
        status_text='Connected',
        extra_message=f'🔄 Refreshed! Found {max(0, peer_count)} peer(s) in network'
    )

    return (200, {'Content-Type': 'text/html; charset=utf-8'}, html)


@app.route('/send-message', methods=['POST'])
def send_message(req):
    """Handle message sending"""
    body = req.body if hasattr(req, 'body') else {}
    data = parse_form_data(body)

    peer_id = data.get('peer_id')
    peer_ip = data.get('peer_ip')
    peer_port = data.get('peer_port')
    message = data.get('message')
    channel = data.get('channel', 'general')
    server_url = '192.168.1.9:8080'  # Default

    # Store message
    with messages_lock:
        if channel not in channel_messages:
            channel_messages[channel] = []

        channel_messages[channel].append({
            'peer_id': peer_id,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })

    print(f"[SampleApp] Message from {peer_id}: {message}")

    html = render_html_with_data(
        peer_id, peer_ip, peer_port, server_url,
        status_class='connected',
        status_text='Connected',
        extra_message=''
    )

    return (200, {'Content-Type': 'text/html; charset=utf-8'}, html)


@app.route('/login', methods=['GET'])
def login_form(req):
    """Display the login form page."""
    response_headers = {'Content-Type': 'text/html; charset=utf-8'}
    return (200, response_headers, LOGIN_FORM_PAGE)


@app.route('/login', methods=['POST'])
def login(req):
    """Handle user login via POST request with authentication validation."""
    body = req.body if hasattr(req, 'body') else ""
    print(f"[SampleApp] Login attempt with body: {body}")

    form_data = parse_form_data(body)
    username = form_data.get('username', '')
    password = form_data.get('password', '')

    print(f"[SampleApp] Credentials - Username: {username}, Password: {'*' * len(password)}")

    if username == VALID_USERNAME and password == VALID_PASSWORD:
        print("[SampleApp] ✓ Authentication successful")
        response_headers = {
            'Content-Type': 'text/html; charset=utf-8',
            'Set-Cookie': 'auth=true',
            'Location': '/'
        }
        return (302, response_headers, INDEX_PAGE)
    else:
        print("[SampleApp] ✗ Authentication failed - Invalid credentials")
        response_headers = {
            'Content-Type': 'text/html; charset=utf-8',
            'Location': '/'
        }
        return (302, response_headers, UNAUTHORIZED_PAGE)


@app.route('/', methods=['GET'])
def index(req):
    """Root endpoint - shows chat interface"""
    cookies = req.cookies if hasattr(req, 'cookies') else {}
    auth_cookie = cookies.get('auth', '')

    print(f"[SampleApp] GET / - Checking authentication cookie: auth={auth_cookie}")

    if auth_cookie == 'true':
        print("[SampleApp] ✓ Valid auth cookie - serving index page")

        # Generate initial values
        import random
        peer_id = 'peer_' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=9))
        local_ip = get_local_ip()
        peer_port = str(8000 + random.randint(0, 999))
        server_url = '192.168.1.9:8080'

        html = render_html_with_data(
            peer_id, local_ip, peer_port, server_url,
            status_class='',
            status_text='Not Connected',
            extra_message='Welcome to P2P Chat! Enter server details and click Connect.'
        )

        response_headers = {'Content-Type': 'text/html; charset=utf-8'}
        return (200, response_headers, html)
    else:
        print(f"[SampleApp] ✗ Invalid or missing auth cookie - returning 401")
        response_headers = {'Content-Type': 'text/html; charset=utf-8'}
        return (401, response_headers, UNAUTHORIZED_PAGE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Backend',
        description='WeApRous P2P Chat Application Server',
        epilog='P2P Chat Network Server'
    )
    parser.add_argument('--server-ip', default='0.0.0.0', help='Server bind address (use 0.0.0.0 for all interfaces)')
    parser.add_argument('--server-port', type=int, default=PORT, help='Server port')

    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    try:
        app.prepare_address(ip, port)
        local_ip = get_local_ip()
        print(f"[SampleApp] Starting P2P Chat Server")
        print(f"[SampleApp] Listening on {ip}:{port}")
        print(f"[SampleApp] Local IP: {local_ip}")
        print(f"[SampleApp] Access via: http://{local_ip}:{port}")
        print(f"[SampleApp] Valid credentials: username={VALID_USERNAME}, password={VALID_PASSWORD}")
        app.run()
    except Exception as e:
        print(f"[SampleApp] Error starting server: {e}")
        import traceback

        traceback.print_exc()
        exit(1)