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
from daemon.utils import load_html_file, parse_form_data, render_routes_page

PORT = 9000  # Default port

VALID_USERNAME = "admin"
VALID_PASSWORD = "password"

app = WeApRous()



# Try to load index.html from file, fallback to hardcoded version
INDEX_PAGE= render_routes_page(app, 'www')

UNAUTHORIZED_PAGE = load_html_file('www/unauthorized.html')

LOGIN_FORM_PAGE = load_html_file('www/login.html')


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
            'Set-Cookie': 'auth=true',
            'Location': '/'
        }
        return (302, response_headers, INDEX_PAGE)
    else:
        print("[SampleApp] ✗ Authentication failed - Invalid credentials")

        # Failed login - return 401 Unauthorized page
        response_headers = {
            'Content-Type': 'text/html; charset=utf-8',
            'Location': '/'
        }
        return (302, response_headers, UNAUTHORIZED_PAGE)


@app.route('/hello', methods=['PUT'])
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

@app.route('/', methods=['GET'])
def index(req):
    """
    Root endpoint - shows available routes.

    :return: HTML page with route listing
    :rtype: tuple
    """
    cookies = req.cookies if hasattr(req, 'cookies') else {}
    auth_cookie = cookies.get('auth', '')

    print(f"[SampleApp] GET / - Checking authentication cookie: auth={auth_cookie}")

    # Validate cookie
    if auth_cookie == 'true':
        print("[SampleApp] ✓ Valid auth cookie - serving index page")

        # Cookie is valid - serve index page
        response_headers = {
            'Content-Type': 'text/html; charset=utf-8',
            'Location': '/'
        }
        return ('/', response_headers, INDEX_PAGE)
    else:
        # Task 1B: No valid cookie - return 401 Unauthorized
        print(f"[SampleApp] ✗ Invalid or missing auth cookie - returning 401")

        response_headers = {
            'Content-Type': 'text/html; charset=utf-8'
        }
        return (401, response_headers, UNAUTHORIZED_PAGE)


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