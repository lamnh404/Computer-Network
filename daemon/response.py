"""
daemon.response - Response class methods
"""
import datetime
import os
import mimetypes


class Response():
    """The :class:`Response <Response>` object, which contains a
    server's response to an HTTP request.
    """

    def __init__(self, request=None):
        """
        Initializes a new :class:`Response <Response>` object.
        """
        self._content = b""
        self._content_consumed = False
        self._next = None
        self.status_code = None
        self.headers = {}
        self.url = None
        self.encoding = None
        self.history = []
        self.reason = None
        self.cookies = {}
        self.elapsed = datetime.timedelta(0)
        self.request = None

    def get_mime_type(self, path):
        """
        Determines the MIME type of a file based on its path.
        """
        try:
            mime_type, _ = mimetypes.guess_type(path)
        except Exception:
            return 'application/octet-stream'
        return mime_type or 'application/octet-stream'

    def prepare_content_type(self, mime_type='text/html'):
        """
        Prepares the Content-Type header and determines the base directory.
        """
        BASE_DIR = ""
        base_dir = ""

        main_type, sub_type = mime_type.split('/', 1)
        print("[Response] processing MIME main_type={} sub_type={}".format(main_type, sub_type))

        if main_type == 'text':
            self.headers['Content-Type'] = 'text/{}'.format(sub_type)
            if sub_type == 'plain' or sub_type == 'css':
                base_dir = BASE_DIR + "static/"
            elif sub_type == 'html':
                base_dir = BASE_DIR + "www/"
            else:
                raise ValueError("Invalid text MIME sub_type: {}".format(sub_type))
        elif main_type == 'image':
            base_dir = BASE_DIR + "static/"
            self.headers['Content-Type'] = 'image/{}'.format(sub_type)
        elif main_type == 'application':
            base_dir = BASE_DIR + "apps/"
            self.headers['Content-Type'] = 'application/{}'.format(sub_type)
        else:
            raise ValueError("Invalid MIME type: main_type={} sub_type={}".format(main_type, sub_type))

        return base_dir

    def build_content(self, path, base_dir):
        """
        Loads the file from storage space.
        """
        filepath = os.path.join(base_dir, path.lstrip('/'))

        print("[Response] serving the object at location {}".format(filepath))
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
        except FileNotFoundError:
            return 404, b"404 Not Found"
        return len(content), content

    def build_response_header(self, request):
        """
        Constructs the HTTP response headers.
        """
        reqhdr = request.headers
        rsphdr = self.headers

        # Determine status code and reason
        status_code = self.status_code or 200
        reason = self.reason or "OK"

        # Build status line
        status_line = "HTTP/1.1 {} {}\r\n".format(status_code, reason)

        # Build dynamic headers
        headers = {
            "Date": datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "Server": "WeApRous/1.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Content-Type": rsphdr.get("Content-Type", "text/html; charset=utf-8"),
            "Content-Length": str(len(self._content)),
            "Connection": "close",
        }

        # Build formatted header text
        header_text = status_line
        for key, value in headers.items():
            header_text += "{}: {}\r\n".format(key, value)
        header_text += "\r\n"  # End of headers

        return header_text.encode("utf-8")

    def build_notfound(self):
        """
        Constructs a standard 404 Not Found HTTP response.
        """
        return (
            "HTTP/1.1 404 Not Found\r\n"
            "Accept-Ranges: bytes\r\n"
            "Content-Type: text/html\r\n"
            "Content-Length: 13\r\n"
            "Cache-Control: max-age=86000\r\n"
            "Connection: close\r\n"
            "\r\n"
            "404 Not Found"
        ).encode('utf-8')

    def build_response(self, request):
        """
        Builds a full HTTP response including headers and content.
        """
        path = request.path
        print("[Response] Building response for path: {}".format(path))
        mime_type = self.get_mime_type(path)
        print("[Response] {} path {} mime_type {}".format(request.method, request.path, mime_type))

        base_dir = ""
        # Determine base directory based on file type
        if path.endswith('.html') or mime_type == 'text/html':
            base_dir = self.prepare_content_type(mime_type='text/html')
        elif mime_type == 'text/css':
            base_dir = self.prepare_content_type(mime_type='text/css')
        elif mime_type.startswith('image/') or mime_type.startswith('application/'):
            base_dir = self.prepare_content_type(mime_type=mime_type)
        else:
            return self.build_notfound()

        c_len, self._content = self.build_content(path, base_dir)

        # Check if file was found
        if c_len == 404:
            return self.build_notfound()

        # Set status code for successful response
        self.status_code = 200
        self.reason = "OK"

        self._header = self.build_response_header(request)

        return self._header + self._content