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
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist 
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict


class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.

    The `HttpAdapter` class encapsulates the logic for receiving HTTP requests,
    dispatching them to appropriate route handlers, and constructing responses.
    It supports RESTful routing via hooks and integrates with :class:`Request <Request>`
    and :class:`Response <Response>` objects for full request lifecycle management.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket): Active socket connection.
        connaddr (tuple): Address of the connected client.
        routes (dict): Mapping of route paths to handler functions.
        request (Request): Request object for parsing incoming data.
        response (Response): Response object for building and sending replies.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.

        :param ip (str): IP address of the client.
        :param port (int): Port number of the client.
        :param conn (socket): Active socket connection.
        :param connaddr (tuple): Address of the connected client.
        :param routes (dict): Mapping of route paths to handler functions.
        """

        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Conndection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes
        #: Request
        self.request = Request()
        #: Response
        self.response = Response()

    def handle_client(self, conn, addr, routes):
        """
        Handle an incoming client connection.

        This method reads the request from the socket, prepares the request object,
        invokes the appropriate route handler if available, builds the response,
        and sends it back to the client.

        :param conn (socket): The client socket connection.
        :param addr (tuple): The client's address.
        :param routes (dict): The route mapping for dispatching requests.
        """
        self.conn = conn
        self.connaddr = addr
        req = self.request
        resp = self.response

        try:
            # Receive and decode the request
            msg = conn.recv(4096).decode('utf-8')
            print(f"[HttpAdapter] Received request from {addr}")

            # Prepare the request object
            req.prepare(msg, routes)

            # Debug: Show what was parsed
            print(f"[HttpAdapter] Method: {getattr(req, 'method', 'UNKNOWN')}, Path: {getattr(req, 'path', 'UNKNOWN')}")

            if req.hook:
                print(f"[HttpAdapter] Hook found - METHOD {req.hook._route_methods} PATH {req.hook._route_path}")

                try:
                    # Call the route handler with the request object
                    hook_result = req.hook(req)

                    # Handle different return types
                    if isinstance(hook_result, tuple) and len(hook_result) == 3:
                        # Handler returned (status_code, headers, body)
                        status_code, custom_headers, body = hook_result
                        resp.status_code = status_code

                        # Set body attribute (this tells response.py to use dynamic content)
                        resp.body = body

                        # Add custom headers if provided
                        if custom_headers:
                            for key, value in custom_headers.items():
                                resp.headers[key] = value

                    elif isinstance(hook_result, dict):
                        # Handler returned a dictionary (JSON response)
                        import json
                        resp.body = json.dumps(hook_result)
                        resp.status_code = 200
                        resp.headers['Content-Type'] = 'application/json'

                    elif isinstance(hook_result, str):
                        # Handler returned a string
                        resp.body = hook_result
                        resp.status_code = 200
                        resp.headers['Content-Type'] = 'text/plain'

                    else:
                        # Default case
                        resp.body = str(hook_result) if hook_result else ""
                        resp.status_code = 200

                except Exception as e:
                    print(f"[HttpAdapter] Error in hook processing: {e}")
                    import traceback
                    traceback.print_exc()
                    resp.body = "Internal Server Error"
                    resp.status_code = 500
                    resp.headers['Content-Type'] = 'text/plain'

            else:
                # No route found - 404 Not Found
                print(f"[HttpAdapter] No hook found for this request")
                resp.body = """<!DOCTYPE html>
<html>
<head><title>404 Not Found</title></head>
<body>
    <h1>404 Not Found</h1>
    <p>The requested URL was not found on this server.</p>
</body>
</html>"""
                resp.status_code = 404
                resp.headers['Content-Type'] = 'text/html'

            # Build and send the response using Response.build_response()
            # The body attribute tells it to use dynamic content instead of files
            response = resp.build_response(req)
            conn.sendall(response)

        except Exception as e:
            print(f"[HttpAdapter] Error handling client: {e}")
            import traceback
            traceback.print_exc()

            # Send a basic error response
            error_response = b"HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nInternal Server Error"
            try:
                conn.sendall(error_response)
            except:
                pass

        finally:
            conn.close()

    @property
    def extract_cookies(self, req, resp):
        """
        Build cookies from the :class:`Request <Request>` headers.

        :param req:(Request) The :class:`Request <Request>` object.
        :param resp: (Response) The res:class:`Response <Response>` object.
        :rtype: cookies - A dictionary of cookie key-value pairs.
        """
        headers = resp.raw.getheaders()
        cookies = {}
        for header in headers:
            if header.startswith("Cookie:"):
                cookie_str = header.split(":", 1)[1].strip()
                for pair in cookie_str.split(";"):
                    key, value = pair.strip().split("=")
                    cookies[key] = value
        return cookies

    def build_response(self, req, resp):
        """Builds a :class:`Response <Response>` object

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The  response object.
        :rtype: Response
        """
        response = Response()

        # Set encoding.
        response.encoding = self.get_encoding_from_headers(response.headers)
        response.raw = resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        response.cookies = self.extract_cookies(req)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    def add_headers(self, request):
        """
        Add headers to the request.

        This method is intended to be overridden by subclasses to inject
        custom headers. It does nothing by default.


        :param request: :class:`Request <Request>` to add headers to.
        """
        pass

    def build_proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. 

        :class:`HttpAdapter <HttpAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        #
        # TODO: build your authentication here
        #       username, password =...
        # we provide dummy auth here
        #
        username, password = ("admin", "password")

        if username:
            headers["Proxy-Authorization"] = (username, password)

        return headers