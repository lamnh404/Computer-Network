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
from .utils import get_auth_from_url


class Request():
    """The fully mutable "class" `Request <Request>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a "class" `Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import daemon.request
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
        "routes",
        "hook",
        "path",
        "version",
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
        #: HTTP version
        self.version = None
        # The cookies set used to create Cookie header
        self.cookies = None
        #: request body to send to the server.
        self.body = None
        #: Routes
        self.routes = {}
        #: Hook point for routed mapped-path
        self.hook = None

    def extract_request_line(self, request):
        """
        Extract the HTTP method, path, and version from the request line.

        :param request: Raw HTTP request string
        :return: Tuple of (method, path, version)
        """
        try:
            lines = request.splitlines()
            if not lines:
                return None, None, None

            first_line = lines[0]
            parts = first_line.split()

            if len(parts) != 3:
                return None, None, None

            method, path, version = parts

            # Don't modify the path - let the router handle it
            return method, path, version

        except Exception as e:
            print(f"[Request] Error parsing request line: {e}")
            return None, None, None

    def prepare_headers(self, request):
        """
        Prepares the given HTTP headers.

        :param request: Raw HTTP request string
        :return: Dictionary of headers
        """
        lines = request.split('\r\n')
        headers = {}
        for line in lines[1:]:
            if ': ' in line:
                key, val = line.split(': ', 1)
                headers[key.lower()] = val
        return headers

    def prepare_body(self, request):
        """
        Extract the body from the HTTP request.

        :param request: Raw HTTP request string
        :return: Request body as string
        """
        try:
            # Split request into headers and body
            parts = request.split('\r\n\r\n', 1)
            if len(parts) == 2:
                body = parts[1]
                return body
            return ""
        except Exception as e:
            print(f"[Request] Error extracting body: {e}")
            return ""

    def prepare(self, request, routes=None):
        """
        Prepares the entire request with the given parameters.

        :param request: Raw HTTP request string
        :param routes: Dictionary of registered routes
        """
        # Prepare the request line from the request header
        self.method, self.path, self.version = self.extract_request_line(request)

        if not self.method or not self.path:
            print("[Request] Failed to parse request line")
            return

        print(f"[Request] {self.method} path {self.path} version {self.version}")

        # Prepare headers
        self.headers = self.prepare_headers(request)

        # Extract body for POST/PUT requests
        if self.method in ['POST', 'PUT', 'PATCH']:
            self.body = self.prepare_body(request)
            print(f"[Request] Body extracted ({len(self.body)} bytes): {self.body[:100]}")
        else:
            self.body = ""

        # Extract cookies
        cookies = self.headers.get('cookie', '')
        if cookies:
            print(f"[Request] Cookies found: {cookies}")
            self.cookies = self.parse_cookies(cookies)
        else:
            self.cookies = {}

        # Set up routing
        if routes and routes != {}:
            self.routes = routes
            route_key = (self.method, self.path)
            self.hook = routes.get(route_key)


            if self.hook:
                print(f"[Request] Route matched: {route_key} -> {self.hook.__name__}")
            else:
                print(f"[Request] No route found for: {route_key}")
                print(f"[Request] Available routes: {list(routes.keys())}")

    def parse_cookies(self, cookie_string):
        """
        Parse cookie string into a dictionary.

        :param cookie_string: Cookie header value
        :return: Dictionary of cookie key-value pairs
        """
        cookies = {}
        if not cookie_string:
            return cookies

        for pair in cookie_string.split(';'):
            pair = pair.strip()
            if '=' in pair:
                key, value = pair.split('=', 1)
                cookies[key.strip()] = value.strip()

        return cookies

    def prepare_content_length(self, body):
        """
        Set the Content-Length header based on body size.

        :param body: Request body
        """
        if body is not None:
            length = len(body.encode('utf-8')) if isinstance(body, str) else len(body)
            if length:
                self.headers["Content-Length"] = str(length)
        elif (self.method not in ['GET', 'HEAD']) and ("Content-Length" not in self.headers):
            self.headers["Content-Length"] = "0"

    def prepare_auth(self, auth, url=""):
        """
        Prepare authentication for the request.

        :param auth: Authentication handler
        :param url: URL for authentication
        """
        if auth is None:
            url_auth = get_auth_from_url(url)
            print(url_auth)
            auth = url_auth if url_auth else None
        if auth:
            r = auth(self)
            self.__dict__.update(r.__dict__)
            self.prepare_content_length(self.body)

    def prepare_cookies_header(self, cookies):
        """
        Prepare the Cookie header from cookies dictionary.

        :param cookies: Dictionary of cookies
        """
        self.headers["Cookie"] = cookies