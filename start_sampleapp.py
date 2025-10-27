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
import argparse

from daemon.weaprous import WeApRous

PORT = 9000  # Default port

VALID_USERNAME = "admin"
VALID_PASSWORD = "password"

app = WeApRous()


# Helper function to load HTML files
def load_html_file(filepath):
    """
    Load HTML content from a file.

    :param filepath: Path to the HTML file
    :return: HTML content as string
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"[SampleApp] Warning: {filepath} not found, using default HTML")
        return None
    except Exception as e:
        print(f"[SampleApp] Error loading {filepath}: {e}")
        return None


# Try to load index.html from file, fallback to hardcoded version
INDEX_PAGE_FILE = load_html_file('www/index.html')
if INDEX_PAGE_FILE:
    INDEX_PAGE = INDEX_PAGE_FILE
    print("[SampleApp] Loaded index page from www/index.html")
else:
    # Fallback to hardcoded HTML if file doesn't exist
    INDEX_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome - Authenticated</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #28a745; }
        .info { 
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            padding: 15px;
            border-radius: 4px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>✓ Login Successful</h1>
        <p>Welcome! You have successfully authenticated.</p>
        <div class="info">
            <strong>Authentication Status:</strong> Logged in<br>
            <strong>Session:</strong> Active
        </div>
    </div>
</body>
</html>
"""
    print("[SampleApp] Using fallback index page HTML")

UNAUTHORIZED_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>401 Unauthorized</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #dc3545; }
        .error { 
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            padding: 15px;
            border-radius: 4px;
            margin-top: 20px;
        }
        a {
            color: #007bff;
            text-decoration: none;
        }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>401 Unauthorized</h1>
        <p>Invalid username or password. Access denied.</p>
        <div class="error">
            <strong>Error:</strong> Authentication failed<br>
            <strong>Reason:</strong> Invalid credentials provided
        </div>
        <p style="margin-top: 20px;">
            <a href="/login">← Back to login</a>
        </p>
    </div>
</body>
</html>
"""

LOGIN_FORM_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 400px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { text-align: center; color: #333; }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
            font-size: 14px;
        }
        button {
            width: 100%;
            padding: 12px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
        button:hover {
            background-color: #0056b3;
        }
        .hint {
            font-size: 12px;
            color: #666;
            margin-top: 15px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Login</h1>
        <form method="POST" action="/login">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Login</button>
        </form>
        <div class="hint">
            <strong>Hint:</strong> username=admin, password=password
        </div>
    </div>
</body>
</html>
"""


def parse_form_data(body):
    """
    Parse URL-encoded form data from request body.

    :param body: The request body containing form data
    :type body: str
    :return: Dictionary of form fields
    :rtype: dict
    """
    if not body:
        return {}

    params = {}
    try:
        for pair in body.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                # Basic URL decoding for common cases
                value = value.replace('+', ' ')
                params[key] = value
    except Exception as e:
        print(f"[SampleApp] Error parsing form data: {e}")

    return params


@app.route('/login', methods=['GET'])
def login_form(req):
    """
    Display the login form page.

    :param req: The Request object
    :return: HTTP response tuple (status_code, headers_dict, html_content)
    :rtype: tuple
    """
    response_headers = {
        'Content-Type': 'text/html; charset=utf-8'
    }
    return (200, response_headers, LOGIN_FORM_PAGE)


@app.route('/login', methods=['POST'])
def login(req):
    """
    Handle user login via POST request with authentication validation.

    Task 1A Implementation:
    - Validates submitted credentials (username=admin, password=password)
    - Returns index page with Set-Cookie: auth=true if valid
    - Returns 401 Unauthorized page if invalid

    :param req: The Request object containing headers and body
    :return: HTTP response tuple (status_code, headers_dict, html_content)
    :rtype: tuple
    """
    # Extract body from request object
    body = req.body if hasattr(req, 'body') else ""

    print(f"[SampleApp] Login attempt with body: {body}")

    # Parse form data from request body
    form_data = parse_form_data(body)
    username = form_data.get('username', '')
    password = form_data.get('password', '')

    print(f"[SampleApp] Credentials - Username: {username}, Password: {'*' * len(password)}")

    # Validate credentials
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        print("[SampleApp] ✓ Authentication successful")

        # Successful login - return index page with auth cookie
        response_headers = {
            'Content-Type': 'text/html; charset=utf-8',
            'Set-Cookie': 'auth=true'
        }
        return (200, response_headers, INDEX_PAGE)
    else:
        print("[SampleApp] ✗ Authentication failed - Invalid credentials")

        # Failed login - return 401 Unauthorized page
        response_headers = {
            'Content-Type': 'text/html; charset=utf-8'
        }
        return (401, response_headers, UNAUTHORIZED_PAGE)


@app.route('/test', methods=['GET'])
def test(headers=None, body=None):
    """
    Simple test endpoint to verify routing works.
    Returns plain string instead of tuple.
    """
    return "TEST ENDPOINT WORKING"


def hello(headers, body):
    """
    Handle greeting via PUT request.

    This route prints a greeting message to the console using the provided headers
    and body.

    :param headers: The request headers or user identifier
    :type headers: str
    :param body: The request body or message payload
    :type body: str
    :return: JSON response with greeting message
    :rtype: dict
    """
    print(f"[SampleApp] ['PUT'] Hello in {headers} to {body}")
    return {"message": "Hello received", "headers": headers, "body": body}


@app.route('/status', methods=['GET'])
def status(headers=None, body=None):
    """
    Simple health check endpoint.

    :return: Server status information
    :rtype: dict
    """
    return {"status": "running", "message": "Server is healthy"}


@app.route('/', methods=['GET'])
def index(headers=None, body=None):
    """
    Root endpoint - shows available routes.

    :return: HTML page with route listing
    :rtype: tuple
    """
    routes_html = ""
    for (method, path), func in sorted(app.routes.items()):
        routes_html += f"<li><strong>{method}</strong> {path} → {func.__name__}()</li>\n"

    page = f"""<!DOCTYPE html>
<html>
<head>
    <title>WeApRous Server</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
        h1 {{ color: #007bff; }}
        ul {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        li {{ margin: 10px 0; }}
        a {{ color: #007bff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>WeApRous Server - Running</h1>
    <h2>Available Routes:</h2>
    <ul>
        {routes_html}
    </ul>
    <h2>Quick Links:</h2>
    <ul>
        <li><a href="/login">Login Page</a></li>
        <li><a href="/status">Status Check</a></li>
    </ul>
</body>
</html>"""

    response_headers = {
        'Content-Type': 'text/html; charset=utf-8'
    }
    return (200, response_headers, page)


if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(
        prog='Backend',
        description='WeApRous RESTful Application Server with Authentication',
        epilog='Backend daemon for sample application - Task 1A'
    )
    parser.add_argument('--server-ip', default='127.0.0.1', help='Server bind address')
    parser.add_argument('--server-port', type=int, default=PORT, help='Server port')

    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port
    # Prepare and launch the RESTful application
    try:
        app.prepare_address(ip, port)
        print(f"[SampleApp] Starting server on {ip}:{port}")
        print(f"[SampleApp] Valid credentials: username={VALID_USERNAME}, password={VALID_PASSWORD}")
        app.run()
    except Exception as e:
        print(f"[SampleApp] Error starting server: {e}")
        import traceback

        traceback.print_exc()
        exit(1)