from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
import json
from api.sms_handler import SMSHandler
from lib.error_handler import ErrorHandler
from lib.config import get_settings

settings = get_settings()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Get content length
            content_length = int(self.headers['Content-Length'])
            # Get POST data
            post_data = self.rfile.read(content_length).decode('utf-8')
            # Parse POST data
            parsed_data = parse_qs(post_data)
            
            # Initialize SMS handler
            sms_handler = SMSHandler()
            response = sms_handler.handle_incoming_message(parsed_data)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/xml')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            error_handler = ErrorHandler()
            error_message = error_handler.handle_sms_error(e)
            
            self.send_response(500)
            self.send_header('Content-type', 'application/xml')
            self.end_headers()
            # Return TwiML response with error message
            error_response = f"""<?xml version="1.0" encoding="UTF-8"?>
                               <Response>
                                   <Message>{error_message}</Message>
                               </Response>"""
            self.wfile.write(error_response.encode('utf-8'))