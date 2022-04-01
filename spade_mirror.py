#!/usr/bin/env python3
# Author: Sean Pesce

# The following project was used as a reference implementation for the HTTP-based MPJEG stream:
# https://github.com/damiencorpataux/pymjpeg


import datetime
import http.server
import queue
import socket
import ssl
import sys
import time

from io import BytesIO

import spade_msg
from spade_util import ping, udp_send, decode_battery_percentage


SERVER_IP = '192.168.10.123'


class HttpHandler(http.server.BaseHTTPRequestHandler):
    BOUNDARY = b'--SP-LaputanMachine--'
    SPADE_CLIENT = None
    RENDER_RATE = 0  # One frame is rendered locally (with MatPlotLib) for every RENDER_RATE frames sent to the HTTP client (Set to <1 to never render locally)
    PROTOCOL = 'http'
    PORT = 45100
    
    
    @classmethod
    def HEADERS_BASE(cls):
        headers = {
            'Cache-Control': 'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0',
            'Content-Type': f'multipart/x-mixed-replace;boundary={cls.BOUNDARY.decode("ascii")}',
            #'Connection': 'close',
            'Pragma': 'no-cache',
            'Access-Control-Allow-Origin': '*',  # CORS
        }
        return headers
    
    
    @classmethod
    def HEADERS_IMAGE(cls, length):
        headers = {
            'X-Timestamp': time.time(),
            'Content-Length': str(int(length)),
            'Content-Type': 'image/jpeg',
        }
        return headers
    
    
    def do_GET(self):
        print(self.headers['Host'])
        spade_client = self.__class__.SPADE_CLIENT
        
        if self.path not in ('/', '/stream', '/battery', '/model', '/pwm'):
            self.send_response(404)
            self.send_header('Connection', 'close')
            self.end_headers()
            return
        
        if spade_client is None:
            self.send_response(503)  # Service Unavailable
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(b'Error: Spade client unavailable')
            return
            
        
        self.send_response(200)
        self.send_header('X-Battery', str(spade_client.battery))
        self.send_header('Connection', 'close')
        
        if self.path == '/battery':
            data = str(spade_client.battery).encode('ascii')
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)
            return
        
        elif self.path == '/model':
            data = str(spade_client.version).encode('ascii')
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)
            return
        
        elif self.path == '/pwm':
            data = str(spade_client.pwm).encode('ascii')
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)
            return
        
        elif self.path == '/':
            # @TODO: Insert model and battery percentage in DOM
            html_data = f'<html><head></head><body><img src="{self.__class__.PROTOCOL.lower()}://{self.headers["Host"]}/stream" >\n</body></html>'
            print(f'Serving page:\n{html_data}')
            self.send_header('Content-Length', len(html_data))
            self.end_headers()
            self.wfile.write(html_data.encode('ascii'))
            return
        
        elif self.path == '/stream':
            for k, v in self.__class__.HEADERS_BASE().items():
                self.send_header(k, v)
            spade_client.connect()
            spade_client.streaming = True
            spade_client.stream_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server_address = (spade_client.server, spade_client.__class__.STREAM_PORT)
            data = spade_client.__class__.READ_STREAM_REQUEST
            sent = spade_client.stream_sock.sendto(data, server_address)
            assert sent == len(data), f'UDP message was {len(data)} bytes but only {sent} were sent'
            while spade_client.streaming:
                frame = spade_client.get_frame()
                if frame is None:
                    continue
                
                self.end_headers()
                self.wfile.write(self.__class__.BOUNDARY)
                self.end_headers()
                img_headers = self.__class__.HEADERS_IMAGE(len(frame.data))
                for k, v in img_headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(frame.data)
                if self.__class__.RENDER_RATE > 0 and frame.index % self.__class__.RENDER_RATE == 0:
                    frame.render()#f'{spade_client.version}  |  Frame {frame.index}  |  Battery: {spade_client.battery}%')
                
                #print(f'Reconstructed frame: {frame.index}')
                #time.sleep(0.016)  # ~60FPS
            
            spade_client.streaming = False
            if spade_client.stream_sock is not None and not spade_client.stream_sock._closed:
                # @TODO: Send EndStream message
                spade_client.stream_sock.close()
            spade_client.stream_sock = None
        return


class JpgFrame:
    BUF_SZ = 131072
    
    def __init__(self, index=None, width=None, height=None, coords=None):
        self._buf = bytearray(self.__class__.BUF_SZ)
        if None not in (index, width, height):
            self.init(index, width, height, coords)
        return
    
    
    def init(self, index, width, height, coords=None):
        self.index = int(index)
        self.width = int(width)
        self.height = int(height)
        self.x = None
        self.y = None
        self.z = None
        if coords is not None and type(coords) == tuple and len(coords) == 3:
            self.x = int(coords[0])
            self.y = int(coords[1])
            self.z = int(coords[2])
        self.total = None
        self.complete = False  # True when all chunks have been acquired
        self.chunk_sz = None   # All but the final chunk have the same size
        self.acquired_sz = 0   # Total number of bytes acquired
        self._data = memoryview(self._buf)
    
    
    def add_chunk(self, idx, data, final=0):
        assert not self.complete, 'Attempt to add a chunk to a completed frame'
        if not final:
            if self.chunk_sz is not None:
                assert self.chunk_sz == len(data), f'Chunk size mismatch:  {self.chunk_sz=}  {len(data)=}'
            self.chunk_sz = len(data)
        elif self.chunk_sz is None:
            # Received last chunk before any other chunk... just allow the bad data?
            self.chunk_sz = len(data)
        start = self.chunk_sz * (idx - 1)  # Message indices start at 1
        self._data[start:start+len(data)] = data
        self.acquired_sz += len(data)
        if final:
            self.total = int(final)
        if self.total and self.acquired_sz > self.chunk_sz * (self.total-1):
            self.complete = True
        return
    
    
    @property
    def data(self):
        assert self.complete, 'Attempt to reassemble incomplete frame'
        return self._data[:self.acquired_sz]
    
    
    @property
    def position(self):
        coords = (self.x, self.y, self.z)
        if None not in coords:
            return coords
        return None
    
    
    def render(self, title=None):
        import matplotlib.pyplot
        img = matplotlib.pyplot.imread(BytesIO(self.data), format='jpeg')
        if title is None:
            title = f'Frame {self.index}'
        matplotlib.pyplot.title(title)
        matplotlib.pyplot.imshow(img)
        matplotlib.pyplot.show(block=False)
        matplotlib.pyplot.pause(0.001)



class SpadeClient:
    DEFAULT_SERVER = '192.168.10.123'
    COMMAND_PORT = 50000  # UDP
    STREAM_PORT = 8030    # UDP
    SERVER_TYPE = {
        70: 'X7',
        71: 'M9|X7',
        72: 'B2',
        73: 'T5',
    }
    READ_STREAM_REQUEST = b'\x99\x99\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    UDP_READ_SZ = 8192
    FRAME_QUEUE_MAX = 8
    
    def __init__(self, server=DEFAULT_SERVER, cmd_send_index=1234):
        self.server = str(server)  # Server host name or IP address
        self.cmd_send_index = int(cmd_send_index) & 0xffffffff  # Incremented with each message sent to the server (max 4 bytes)
        self._connected = False
        self.command_sock = None
        self.stream_sock = None
        self.stream_buf = memoryview(bytearray(self.__class__.UDP_READ_SZ))
        self.streaming = False
        self.frame_queue = queue.Queue()
        self.frame_dict = {}
        self.frame_reserve = []
        self.frame_reserve_idx = 0
        for i in range(self.__class__.FRAME_QUEUE_MAX):
            self.frame_reserve.append(JpgFrame())
        return
    
    
    def connect(self):
        if self._connected and self.command_sock is not None:
            return
        print(f'Connecting to {self.server}')
        if not ping(self.server):
            raise IOError(f'[ERROR] No ICMP response from {self.server}')
        self.command_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = b'SETCMD\xff\xff\x00\x00\x90\x00\x04\x00\x00\x00\x00\x00'
        msg = spade_msg.SpadeUdpMsg_SETCMD.from_bytes(msg)
        msg.data = b'\x00' * msg.length
        response = self.send_command(msg, True)
        self._connected = True
    
    
    def disconnect(self):
        self.streaming = False
        if self.command_sock is not None:
            if not self.command_sock._closed:
                self.command_sock.close()
            self.command_sock = None
        if self.stream_sock is not None:
            if not self.stream_sock._closed:
                # @TODO: Send EndStream message
                self.stream_sock.close()
            self.stream_sock = None
        self._connected = False
    
    
    def stream_to_matplotlib(self):
        # Don't use this function
        self.connect()
        self.streaming = True
        self.stream_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_address = (self.server, self.__class__.STREAM_PORT)
        data = self.__class__.READ_STREAM_REQUEST
        sent = self.stream_sock.sendto(data, server_address)
        assert sent == len(data), f'UDP message was {len(data)} bytes but only {sent} were sent'
        while self.streaming:
            frame = self.get_frame()
            if frame is None:
                continue
            
            frame.render()
            print(f'Reconstructed frame: {frame.index}')
            #time.sleep(0.016)  # ~60FPS
        
        self.streaming = False
        if self.stream_sock is not None and not self.stream_sock._closed:
            # @TODO: Send EndStream message
            self.stream_sock.close()
        self.stream_sock = None
        return


    def get_frame(self):
        if not self.streaming:
            return None
        
        frame = None
        
        server_address = (self.server, self.__class__.STREAM_PORT)
        
        while self.stream_sock is not None and not self.stream_sock._closed:
            nread = self.stream_sock.recv_into(self.stream_buf)
            buf = self.stream_buf[:nread]
            offs = 0
        
            # Parse response for multiple messages
            while True:
                read_sz = spade_msg.SpadeUdpMsg_0x9999_StreamChunk.sizeof()
                data = buf[offs:offs+read_sz]
                offs += read_sz
                #if len(data) == 0:
                #    continue
                
                if len(data) < read_sz:
                    if len(data) > 0:
                        print(f'len(data) < spade_msg.SpadeUdpMsg_0x9999_StreamChunk.sizeof()')
                        print(data)
                    return frame
                
                msg = spade_msg.SpadeUdpMsg_0x9999_StreamChunk.from_bytes(data)
                read_sz = msg.length
                data = buf[offs:offs+read_sz]
                offs += read_sz
                if len(data) < read_sz:
                    print(f'len(data) < read_sz')
                    print(data)
                    return frame
                
                if msg.n_frame1 in self.frame_dict:
                    parse_frame = self.frame_dict[msg.n_frame1]
                else:
                    while len(self.frame_dict) >= len(self.frame_reserve):
                        # Discard unfinished frames if no free frame slots are available
                        print('Discarding frame')
                        self.frame_dict.pop(self.frame_queue.get().index, None)
                    parse_frame = self.frame_reserve[self.frame_reserve_idx]
                    self.frame_reserve_idx += 1
                    if self.frame_reserve_idx >= len(self.frame_reserve):
                        self.frame_reserve_idx = 0
                    parse_frame.init(msg.n_frame1, msg.res_width, msg.res_height)
                    self.frame_dict[msg.n_frame1] = parse_frame
                    self.frame_queue.put(parse_frame)
                
                #print(f'Adding chunk:\n{msg}\n{msg.coordinates=}\n')
                assert (msg.n_frame1 == msg.n_frame2) and (msg.n_frame1 == msg.n_frame3), f'Unequal n_frame values'
                assert msg.unk1 == 1, f'{msg.unk1=}'
                parse_frame.add_chunk(msg.n_chunk, data, msg.last_chunk)
                
                # If a frame enters the "complete" state, pop frames from the queue (and delete them from
                # the dict) until the popped frame is the completed frame
                if parse_frame.complete:
                    while True:
                        tmp_frame = self.frame_queue.get()
                        self.frame_dict.pop(tmp_frame.index, None)
                        if parse_frame.index == tmp_frame.index:  
                            break
                    frame = parse_frame
            
            return frame
    
    
    def mirror_http(self, cert_fpath=None, privkey_fpath=None):
        port = 45100
        HttpHandler.SPADE_CLIENT = self
        HttpHandler.PORT = port
        server_address = ('0.0.0.0', port)
        httpd = http.server.ThreadingHTTPServer(server_address, HttpHandler)
        if None not in (cert_fpath, privkey_fpath):
            HttpHandler.PROTOCOL = 'https'
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            context.load_cert_chain(certfile=cert_fpath, keyfile=privkey_fpath, password='')
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        print(f'Serving {HttpHandler.PROTOCOL.upper()} on {HttpHandler.PROTOCOL.lower()}://{server_address[0]}:{server_address[1]}')
        httpd.serve_forever()
    
    
    @property
    def connected(self):
        return self._connected
    
    
    def increment(self):
        """
        Increment and return the command-send-index while restricting it to four bytes
        """
        self.cmd_send_index = int(self.cmd_send_index + 1) & 0xffffffff
        return self.cmd_send_index

    
    def send_command(self, msg, connecting=False):
        if type(msg) not in (bytes, spade_msg.SpadeUdpMsg_0x9999, spade_msg.SpadeUdpMsg_SETCMD):
            raise TypeError(f'Bad request message type: {type(msg)}')
        
        if type(msg) == bytes:
            data = b''
            if msg.startswith(b'\x99\x99'):
                data = msg[spade_msg.SpadeUdpMsg_0x9999.sizeof():]
                msg = spade_msg.SpadeUdpMsg_0x9999.from_bytes(msg)
                if msg.type in (1, 2, 3):
                    raise ValueError(f'Stream control messages should be delivered to port {self.__class__.STREAM_PORT}')
            elif msg.startswith(b'SETCMD'):
                data = msg[spade_msg.SpadeUdpMsg_SETCMD.sizeof():]
                msg = spade_msg.SpadeUdpMsg_SETCMD.from_bytes(msg)
            else:
                raise ValueError(f'Invalid UDP message magic bytes: {msg[:100]}')
            
            msg.data = data
            msg.length = len(data)
        
        if not (connecting or self.connected):
            self.connect()
        
        msg.cmdSendIndex = self.increment()
        port = self.__class__.COMMAND_PORT
        #print(f'\n[Client -> {self.server}:{port}]\n{msg.type_name} {msg}\n{msg.data}')
        
        server_address = (self.server, port)
        self.command_sock.sendto(bytes(msg), server_address)
        response, server = self.command_sock.recvfrom(msg.sizeof())
        assert server[0] == self.server, f'Response from unknown host {server[0]}'
        response = msg.__class__.from_bytes(response)
        if response.length > 0:
            response.data, server = self.command_sock.recvfrom(response.length)
            assert server[0] == self.server, f'Response from unknown host {server[0]}'
        #print(f'[{self.server}:{port} -> Client]\n{response.type_name} {response}\n{response.data}\n')
        return response
    
    
    @property
    def battery(self):
        msg = b'\x99\x99\x17\x10\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        response = self.send_command(msg)
        battery_percentage = decode_battery_percentage(response.arg1)
        #print(f'Server battery at {battery_percentage}%')
        return battery_percentage
    
    
    @property
    def version(self):
        msg = b'\x99\x99\x02\x10\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        response = self.send_command(msg)
        server_type = 'Unknown'
        type_val = int(str(response.arg1)[:2])
        if type_val in self.__class__.SERVER_TYPE:
            server_type = self.__class__.SERVER_TYPE[type_val]
        #print(f'Server: {server_type}')
        return server_type
    
    
    @property
    def pwm(self):
        msg = b'\x99\x99\x15\x10\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        response = self.send_command(msg)
        pwm = response.arg1
        #print(f'PWM: {pwm}')
        return pwm
    
    
    def get_mac(self):
        raise NotImplementedError()
        msg = b'\x99\x99\x1b\x10\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        response = self.send_command(msg)
    
    
    def get_ssid_list(self):
        raise NotImplementedError()
        msg = b'\x99\x99\x1a\x10\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        response = self.send_command(msg)
        
        
        
if __name__ == '__main__':
    client = SpadeClient()
    print(f'Server battery at {client.battery}%')
    print(f'Server: {client.version}')
    print(f'PWM: {client.pwm}')
    #client.stream_to_matplotlib()  # Not recommended; slows to unusable rate very quickly due to repeated rendering with matplotlib
    client.mirror_http()
