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

P2P Chat application using the WeApRous framework with AJAX (no page refresh).
"""

import json
import socket
import threading
import argparse
from datetime import datetime
import random
import string

from daemon.weaprous import WeApRous
from daemon.utils import load_html_file, parse_form_data

import db.P2p_chat_db as db



PORT = 9000  # Default port

app = WeApRous()

# Initialize database
print("[P2PChat] Initializing database...")
db.init_db()


# Thread-safe peer tracking
peer_lock = threading.Lock()
active_peers = {}  # {peer_id: {'ip': ..., 'port': ..., 'last_seen': ...}}

# Message storage per channel
messages_lock = threading.Lock()
channel_messages = {'general': []}  # {channel_name: [messages]}

# Try to load P2P_chat.html from file

HOMEPAGE = load_html_file('www/homepage.html')

P2P_CHAT__PAGE = load_html_file('www/P2P_chat.html')

UNAUTHORIZED_PAGE = load_html_file('www/unauthorized.html')

LOGIN_FORM_PAGE = load_html_file('www/login.html')

REGISTER_FORM_PAGE = load_html_file('www/register.html')

NOT_FOUND_PAGE = load_html_file('www/404.html')

def get_local_ip():
    """Get local IP address of the machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"


def generate_peer_id():
    """Generate random peer ID"""
    return 'peer_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=9))


@app.route('/login', methods=['GET'])
def login_form(req):
    """Display the login form page."""
    response_headers = {'Content-Type': 'text/html; charset=utf-8'}
    return (200, response_headers, LOGIN_FORM_PAGE)


@app.route('/login', methods=['POST'])
def login(req):
    """Handle user login via POST request with authentication validation."""
    try:
        body = req.body if hasattr(req, 'body') else ""
        print(f"[P2PChat] Login attempt")

        form_data = parse_form_data(body)
        username = form_data.get('username', '')
        password = form_data.get('password', '')

        if db.verify_user(username, password):
            print(f"[P2PChat] ✓ Successful login for user: {username}")
            cookie= "auth=true; Path=/\r\nSet-Cookie: username={}; Path=/".format(username)
            response_headers = {
                'Content-Type': 'application/json',
                'Set-Cookie': cookie
            }
            return (200, response_headers, json.dumps({
                "status": "success",
                "message": "Login successful",
                "redirect": "/"
            }))
        else:
            print(f"[P2PChat] ✗ Invalid credentials for user: {username}")
            response_headers = {'Content-Type': 'application/json'}
            return (401, response_headers, json.dumps({
                "status": "error",
                "message": "Invalid username or password"
            }))
    except Exception  as e:
        print(f"[P2PChat] ✗ Exception during login: {e}")
        response_headers = {'Content-Type': 'application/json'}
        return (500, response_headers, json.dumps({
            "status": "error",
            "message": "Internal server error"
        }))

@app.route('/register', methods=['GET'])
def register_form(req):
    """Display the registration form page."""
    try:
        response_headers = {'Content-Type': 'text/html; charset=utf-8'}
        return 200, response_headers, REGISTER_FORM_PAGE
    except Exception as e:
        print(f"[P2PChat] ✗ Exception displaying registration form: {e}")
        response_headers = {'Content-Type': 'text/html; charset=utf-8'}
        return 500, response_headers, NOT_FOUND_PAGE

@app.route('/register', methods=['POST'])
def register(req):
    """Handle user registration."""
    try:
        body = req.body if hasattr(req, 'body') else ""
        print(f"[P2PChat] Registration attempt")

        form_data = parse_form_data(body)
        username = form_data.get('username', '')
        password = form_data.get('password', '')

        if not username or not password:
            print(f"[P2PChat] ✗ Missing username or password")
            return (400, {'Content-Type': 'application/json'}, json.dumps({
                "status": "error",
                "message": "Missing username or password"
            }))

        if db.save_user_with_password(username, password):
            print(f"[P2PChat] ✓ Successful registration for user: {username}")
            return (200, {'Content-Type': 'application/json'}, json.dumps({
                "status": "success",
                "message": "User registered successfully",
                "redirect": "/login"
            }))
        else:
            print(f"[P2PChat] ✗ Registration failed - user may already exist: {username}")
            return (409, {'Content-Type': 'application/json'}, json.dumps({
                "status": "error",
                "message": "User already exists"
            }))

    except Exception as e:
        print(f"[P2PChat] ✗ Exception during registration: {e}")
        return (500, {'Content-Type': 'application/json'}, json.dumps({
            "status": "error",
            "message": "Internal server error"
        }))


@app.route('/', methods=['GET'])
def index(req):
    """Display the homepage."""
    reponse_header = {'Content-Type': 'text/html; charset=utf-8'}
    return 200, reponse_header, HOMEPAGE


@app.route('/chat', methods=['GET'])
def get_messages(req):
    """Get messages for a specific channel."""
    cookies = req.cookies if hasattr(req, 'cookies') else {}
    auth_cookie = cookies.get('auth', '')
    response_headers = {'Content-Type': 'text/html; charset=utf-8'}
    if auth_cookie != 'true':
        print(f"[P2PChat] ✗ Unauthorized access to /chat")
        return 401, response_headers, UNAUTHORIZED_PAGE

    return 200, response_headers, P2P_CHAT__PAGE

@app.route('/chat/register', methods=['POST'])
def chat_register(req):
    """Register a user as active in the chat."""
    try:
        body= req.body if hasattr(req, 'body') else ""
        data = json.loads(body)
        if not data or 'username' not in data:
            return (400, {'Content-Type': 'application/json'}, json.dumps({
                "status": "error",
                "message": "Missing username"
            }))
        username = data.get('username')

        if db.save_user(username):
            response= {"status": "success", "message": "User registered"}
            return 200, {'Content-Type': 'application/json'}, json.dumps(response)
    except Exception as e:
        print(f"[P2PChat] ✗ Exception during chat registration: {e}")
        return 500, {'Content-Type': 'application/json'}, json.dumps({
            "status": "error",
            "message": "Internal server error"
        })


@app.route('/chat/heartbeat', methods=['POST'])
def chat_heartbeat(req):
    """Update status of users"""
    try:
        body = req.body if hasattr(req, 'body') else ""
        data = json.loads(body)
        if not data or 'username' not in data:
            return (400, {'Content-Type': 'application/json'}, json.dumps({
                "status": "error",
                "message": "Missing username"
            }))

        username = data.get('username')

        # Mark user as active
        if db.mark_user_active(username):
            print(f"[P2PChat] ✓ Heartbeat received from user: {username}")
            response= {"status": "success", "message": "Heartbeat received"}
            return 200, {'Content-Type': 'application/json'}, json.dumps(response)
    except Exception as e:
        print(f"[P2PChat] ✗ Exception during heartbeat: {e}")
        return 500, {'Content-Type': 'application/json'}, json.dumps({
            "status": "error",
            "message": "Internal server error"
        })

@app.route('/chat/active-users', methods=['GET'])
def get_active_users(req):
    """Get list of active users."""
    try:
        db.cleanup_inactive_users(timeout_seconds= 60)

        active_users = db.get_active_users(timeout_seconds=60)

        response = {
            "status": "success",
            "active_users": active_users
        }
        return 200, {'Content-Type': 'application/json'}, json.dumps(response)

    except Exception as e:

        print(f"[P2PChat] ✗ Exception getting active users: {e}")
        return 500, {'Content-Type': 'application/json'}, json.dumps({
            "status": "error",
            "message": "Internal server error"
        })

@app.route('/chat/send-message', methods=['POST'])
def send_message(req):
    """Handle sending a message to a channel."""
    try:
        body = req.body if hasattr(req, 'body') else ""
        data = json.loads(body)
        print(f"[P2PChat] Message send attempt")
        if not data or 'username' not in data or 'message' not in data :
            return (400, {'Content-Type': 'application/json'}, json.dumps({
                "status": "error",
                "message": "Missing username or message"
            }))
        username = data.get('username')
        content = data.get('message')
        channel = data.get('channel', 'general')
        if db.save_message(username, content, channel):
            print(f"[P2PChat] ✓ Message saved from user: {username} in channel: {channel}")
            response= {"status": "success", "message": "Message sent"}
            return 200, {'Content-Type': 'application/json'}, json.dumps(response)
        else:
            print(f"[P2PChat] ✗ Failed to save message from user: {username}")
            return 500, {'Content-Type': 'application/json'}, json.dumps({
                "status": "error",
                "message": "Failed to save message"
            })
    except Exception as e:
        print(f"[P2PChat] ✗ Exception during send message: {e}")
        return 500, {'Content-Type': 'application/json'}, json.dumps({
            "status": "error",
            "message": "Internal server error"
        })

@app.route('/chat/load-messages', methods=['GET'])
def load_messages(req):
    """Load messages for a specific channel."""
    try:
        channel = req.query_params.get('channel', 'general') if hasattr(req, 'query_params') else 'general'

        messages = db.load_messages()

        response = {
            "status": "success",
            "messages": messages
        }
        return 200, {'Content-Type': 'application/json'}, json.dumps(response)

    except Exception as e:
        print(f"[P2PChat] ✗ Exception loading messages: {e}")
        return 500, {'Content-Type': 'application/json'}, json.dumps({
            "status": "error",
            "message": "Internal server error"
        })



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='P2PChat',
        description='WeApRous P2P Chat Application Server (AJAX version)',
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
        print(f"[P2PChat] Starting P2P Chat Server (AJAX version)")
        print(f"[P2PChat] Listening on {ip}:{port}")
        print(f"[P2PChat] Local IP: {local_ip}")
        print(f"[P2PChat] Access via: http://{local_ip}:{port}")
        app.run()
    except Exception as e:
        print(f"[P2PChat] Error starting server: {e}")
        import traceback

        traceback.print_exc()
        exit(1)