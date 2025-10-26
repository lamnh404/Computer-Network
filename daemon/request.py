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

"""
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist 
request settings (cookies, auth, proxies).
"""
from .dictionary import CaseInsensitiveDict
from urllib.parse import parse_qs, urlparse, unquote

class Request():
    """The fully mutable "class" `Request <Request>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a "class" `Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import deamon.request
      >>> req = request.Request()
      ## Incoming message obtain aka. incoming_msg
      >>> r = req.prepare(incoming_msg)
      >>> r
      <Request>
    """
    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "reason",
        "cookies",
        "body",
        "routes",
        "hook",
    ]

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = None
        #: HTTP path
        self.path = None        
        # The cookies set used to create Cookie header
        self.cookies = None
        #: request body to send to the server.
        self.body = None
        #: Routes
        self.routes = {}
        #: Hook point for routed mapped-path
        self.hook = None

    def extract_request_line(self, request):
        try:
            lines = request.splitlines()
            first_line = lines[0]
            method, path, version = first_line.split()

            if path == '/':
                path = '/index.html'
        except Exception:
            return None, None

        return method, path, version
             
    def prepare_headers(self, request):
        """Prepares the given HTTP headers."""
        lines = request.split('\r\n')
        headers = {}
        for line in lines[1:]:
            if ': ' in line:
                key, val = line.split(': ', 1)
                headers[key.lower()] = val
        return headers

    def prepare(self, request, routes=None):
        """Prepares the entire request with the given parameters."""

        # Prepare the request line from the request header
        self.method, self.path, self.version = self.extract_request_line(request)
        print("[Request] {} path {} version {}".format(self.method, self.path, self.version))

        #
        # @bksysnet Preapring the webapp hook with WeApRous instance
        # The default behaviour with HTTP server is empty routed
        #
        parsed_url = urlparse(self.path)
        clean_path = parsed_url.path
        self.query = parse_qs(parsed_url.query)
        self.hook = None
        
        if not routes == {}:
            self.routes = routes
            self.hook = routes.get((self.method, self.path))
            #
            # self.hook manipulation goes here
            # ...
            #

        self.headers = self.prepare_headers(request)
        cookies = self.headers.get('cookie', '')
        self.cookies = CaseInsensitiveDict()
        if cookies:
            for cookie_pair in cookies.split(';'):
                cookie_pair = cookie_pair.strip()
                if '=' in cookie_pair:
                    key, value = cookie_pair.split('=', 1)
                    self.cookies[key.strip()] = value.strip()
        return

    def prepare_body(self, data, files, json=None):
        body_to_set = None
        if json is not None:
            import json as json_module
            body_to_set = json_module.dumps(json)
            self.headers["Content-Type"] = "application/json"
        elif data is not None and not files:
            from urllib.parse import urlencode
            body_to_set = urlencode(data)
            self.headers["Content-Type"] = "application/x-www-form-urlencoded"
        self.body = body_to_set
        self.prepare_content_length(self.body)
        return


    def prepare_content_length(self, body):
        if body is not None:
            length = len(body.encode('utf-8')) if isinstance(body, str) else len(body)
            self.headers["Content-Length"] = str(length)
        else:
            self.headers["Content-Length"] = "0"
        return


    def prepare_auth(self, auth, url=""):
        if auth is None:
            return
        self.auth = auth
        if isinstance(auth, (tuple, list)) and len(auth) == 2:
            username, password = auth
            import base64
            auth_str = f"{username}:{password}"
            auth_bytes = base64.b64encode(auth_str.encode('utf-8'))
            auth_header = auth_bytes.decode('utf-8')
            self.headers["Authorization"] = f"Basic {auth_header}"
        return

    def prepare_cookies(self, cookies):
            self.headers["Cookie"] = cookies
