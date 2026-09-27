from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import urllib.request

BACKEND = "http://127.0.0.1:5000"


class ProxyHandler(SimpleHTTPRequestHandler):

    def do_POST(self):
        if self.path != "/analyzeContour":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        request = urllib.request.Request(
            BACKEND + self.path,
            data=body,
            method="POST",
            headers={
                "Content-Type": self.headers.get("Content-Type"),
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                result = response.read()

                self.send_response(response.status)
                self.send_header(
                    "Content-Type",
                    response.headers.get(
                        "Content-Type",
                        "application/json"
                    )
                )
                self.send_header("Content-Length", str(len(result)))
                self.end_headers()
                self.wfile.write(result)

        except Exception as error:
            self.send_error(502, str(error))


server = ThreadingHTTPServer(("0.0.0.0", 3000), ProxyHandler)

print("Frontend + API proxy running on port 3000")

server.serve_forever()
