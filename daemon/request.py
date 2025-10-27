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
                path = '/login.html'
                # auth_cookie = ??
                #     path = '/index.html'
                # else:
                #     path = '/login.html'
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

        if self.method == 'POST' and self.path == '/login':
            auth_line = request.splitlines()[-1]

        if not routes == {}:
            self.routes = routes
            self.hook = routes.get((self.method, self.path))
            # print("[Request] hook point {}".format(self.hook))

        self.headers = self.prepare_headers(request)
        cookies = self.headers.get('cookie', '')
        if cookies is not None:
            print("[Request] cookies found: {}".format(cookies))
        return

    def prepare_body(self, data, files, json=None):
        if json is not None:
            import json as jsonlib

            self.body = jsonlib.dumps(json)
            self.headers["Content-Type"] = "application/json"

        return


    def prepare_content_length(self, body):
        if body is not None:
            length = body.encode('utf-8') if isinstance(body, str) else len(body)
            if length:
                self.headers["Content-Length"] = str(length)
        elif ( self.method not in ['GET', 'HEAD'] ) and ( "Content-Length" not in self.headers ):
            self.headers["Content-Length"] = "0"


    def prepare_auth(self, auth, url=""):
        if auth is None:
            url_auth = get_auth_from_url(url)
            print(url_auth)
            auth = url_auth if url_auth else None
        if auth:
            r = auth(self)
            self.__dict__.update(r.__dict__)
            self.prepare_content_length(self.body)
        return

    def prepare_cookies(self, cookies):
            self.headers["Cookie"] = cookies
