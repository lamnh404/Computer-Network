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
daemon.weaprous
~~~~~~~~~~~~~~~~~

This module provides a WeApRous object to deploy RESTful url web app with routing
"""

from .backend import create_backend


class WeApRous:
    """The fully mutable :class:`WeApRous <WeApRous>` object, which is a lightweight,
    mutable web application router for deploying RESTful URL endpoints.

    The `WeApRous` class provides a decorator-based routing system for building simple
    RESTful web applications. The class allows developers to register route handlers
    using decorators and launch a TCP-based backend server to serve RESTful requests.
    Each route is mapped to a handler function based on HTTP method and path. It mappings
    supports tracking the combined HTTP methods and path route mappings internally.

    Usage::
      >>> import daemon.weaprous
      >>> app = WeApRous()
      >>> @app.route('/login', methods=['POST'])
      >>> def login(headers="guest", body="anonymous"):
      >>>     return {'message': 'Logged in'}

      >>> @app.route('/hello', methods=['GET'])
      >>> def hello(headers, body):
      >>>     return {'message': 'Hello, world!'}

      >>> app.prepare_address('0.0.0.0', 9000)
      >>> app.run()
    """

    def __init__(self):
        """
        Initialize a new WeApRous instance.

        Sets up an empty route registry and prepares placeholders for IP and port.
        """
        self.routes = {}
        self.ip = None
        self.port = None

    def prepare_address(self, ip, port):
        """
        Configure the IP address and port for the backend server.

        :param ip: The IP address to bind the server.
        :type ip: str
        :param port: The port number to listen on.
        :type port: int
        """
        self.ip = ip
        self.port = port

    def route(self, path, methods=['GET']):
        """
        Decorator to register a route handler for a specific path and HTTP methods.

        :param path: The URL path to route.
        :type path: str
        :param methods: A list of HTTP methods (e.g., ['GET', 'POST']) to bind.
        :type methods: list
        :return: A decorator that registers the handler function.
        :rtype: function
        """

        def decorator(func):
            for method in methods:
                self.routes[(method.upper(), path)] = func

            # Optional attach route metadata to the function
            func._route_path = path
            func._route_methods = methods

            return func

        return decorator

    def run(self):
        """
        Start the backend server and begin handling requests.

        This method launches the TCP server using the configured IP and port,
        and dispatches incoming requests to the registered route handlers.

        :raises ValueError: If IP or port has not been configured.
        """
        if not self.ip or not self.port:
            raise ValueError(
                "Server address not configured. "
                "Call app.prepare_address(ip, port) before run()"
            )

        print(f"[WeApRous] Starting server on {self.ip}:{self.port}")

        create_backend(self.ip, self.port, self.routes)

    def list_routes(self):
        """
        Print all registered routes in a formatted table.

        Useful for debugging and seeing what endpoints are available.
        """
        if not self.routes:
            print("  No routes registered")
            return

        for (method, path), func in sorted(self.routes.items()):
            print(f"  {method:6} {path:30} -> {func.__name__}()")

    def add_route(self, path, methods, handler):
        """
        Programmatically add a route without using decorator syntax.

        :param path: The URL path to route.
        :type path: str
        :param methods: A list of HTTP methods (e.g., ['GET', 'POST']).
        :type methods: list
        :param handler: The function to handle requests to this route.
        :type handler: function
        """
        for method in methods:
            self.routes[(method.upper(), path)] = handler

    def remove_route(self, path, method):
        """
        Remove a registered route.

        :param path: The URL path of the route to remove.
        :type path: str
        :param method: The HTTP method of the route to remove.
        :type method: str
        :return: True if route was removed, False if not found.
        :rtype: bool
        """
        key = (method.upper(), path)
        if key in self.routes:
            del self.routes[key]
            return True
        return False

    def get_handler(self, method, path):
        """
        Get the handler function for a specific method and path.

        :param method: The HTTP method.
        :type method: str
        :param path: The URL path.
        :type path: str
        :return: The handler function if found, None otherwise.
        :rtype: function or None
        """
        return self.routes.get((method.upper(), path))

    def has_route(self, method, path):
        """
        Check if a route exists for the given method and path.

        :param method: The HTTP method.
        :type method: str
        :param path: The URL path.
        :type path: str
        :return: True if the route exists, False otherwise.
        :rtype: bool
        """
        return (method.upper(), path) in self.routes

    def route_count(self):
        """
        Get the total number of registered routes.

        :return: Number of registered routes.
        :rtype: int
        """
        return len(self.routes)