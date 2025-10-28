#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

from urllib.parse import urlparse, unquote
import os
import json


def get_auth_from_url(url):
    """Given a url with authentication components, extract them into a tuple of
    username,password.

    :rtype: (str,str)
    """
    parsed = urlparse(url)

    try:
        auth = (unquote(parsed.username), unquote(parsed.password))
    except (AttributeError, TypeError):
        auth = ("", "")

    return auth

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



def render_routes_page(app, base_dir):
    routes_html = ""
    for (method, path), func in sorted(app.routes.items()):
        routes_html += f"<li><strong>{method}</strong> {path} → {func.__name__}()</li>\n"

    path= os.path.join(base_dir, 'P2P_chat.html')

    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("{{routes}}", routes_html)
    return html

def build_success_response(data):
    """Build a success response."""
    return {"status": "success", "data": data}

def build_error_response(message, status_code=400):
    """Build an error response."""
    return {"status": "error", "message": message, "code": status_code}

def parse_json_body(body):
    """Helper function to parse JSON body."""
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None
    elif isinstance(body, dict):
        return body
    else:
        return None
