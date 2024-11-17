 from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        form_data = parse_qs(post_data)
        
        message_body = form_data.get('Body', [''])[0]
        from_number = form_data.get('From', [''])[0]
        
        print(f"Received message: {message_body} from {from_number}")
        
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
                  <Response>
                      <Message>Message received!</Message>
                  </Response>"""
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/xml')
        self.end_headers()
        self.wfile.write(twiml.encode('utf-8'))
        
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write('{"status": "healthy"}'.encode('utf-8'))