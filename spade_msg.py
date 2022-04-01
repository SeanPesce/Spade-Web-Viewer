#!/usr/bin/env python3
# Author: Sean Pesce

from ctypes import c_char, c_uint8, c_uint16, c_uint32, c_uint64

import ctypes_util


# There appear to be at least two message types, 0x9999 messages and SETCMD messages

class SpadeUdpMsg_0x9999(ctypes_util.StructLE):
    MAGIC = 0x9999
    
    MESSAGE_TYPE = {
        0x0001: 'ReadStream',
        0x0002: 'EndStream',  # Client sends this message and then closes the socket
        0x0003: 'StreamChunk',  # arg1 == XYZ coordinates from accelerometer
        0x1002: 'GetRemoteVersion',
        0x1010: 'SetApParams',  # length == 0x41
        0x1011: 'ClearApParams',
        # @TODO: What are 0x1012 and 0x1013? 0x1013 might be GetChannel
        0x1014: 'SetChannel',  # arg1 == channel
        0x1015: 'GetPWM',
        0x1016: 'SetPWM',  # arg1 == pwm
        0x1017: 'GetBattery',  # arg1 == encoded battery percentage
        0x1018: 'SetSwitchMode',  # arg1 == switch_mode
        0x1019: 'SetShutdown',
        0x101a: 'GetSsidList',
        0x101b: 'GetMac',
        0x2000: 'UpdateFirmware',
    }
    
    _fields_ = [
        ('magic', c_uint16),  # 0x9999
        ('type', c_uint16),   # Message type
        ('cmdSendIndex', c_uint32),  # Increments with every message (?)
        ('arg1', c_uint32),  # Sometimes used to pass a numeric value
        ('length', c_uint32),  # Length of data following message header
        ('unk1', c_uint64),
    ]

    
    def validate(self):
        # Initialize
        self.data = b''
        
        # Validate
        if self.magic != self.__class__.MAGIC:
            raise ValueError(f'Invalid magic bytes for {self.__class__.__name__}: {self.magic:#x}')
        return
    
    
    @property
    def type_name(self):
        return self.__class__.MESSAGE_TYPE[self.type]
    
    
    def get_bytes(self):
        return super().get_bytes() + self.data
    
    
    def __bytes__(self):
        return bytes(self.get_bytes())


class SpadeUdpMsg_0x9999_StreamChunk(ctypes_util.StructLE):
    _fields_ = [
        ('header', SpadeUdpMsg_0x9999),
        ('unk1', c_uint8),  # Playing?
        ('n_frame1', c_uint32),
        ('unk2', c_uint32),
        ('n_chunk', c_uint16),
        ('last_chunk', c_uint16),  # If non-zero, the next response will be a new frame
        ('length', c_uint16),  # Length of data after first 51 bytes (e.g., message headers)
        ('n_frame2', c_uint32),
        ('res_width', c_uint16),   # Video resolution (width)
        ('res_height', c_uint16),  # Video resolution (height)
        ('n_frame3', c_uint32),
    ]
    
    
    @property
    def coordinates(self):
        accel = self.header.arg1
        x = accel >> 20
        y = (0xffc00 & accel) >> 10
        z = 0x3ff & accel
        
        return x, y, z


class SpadeUdpMsg_SETCMD(ctypes_util.StructLE):
    MAGIC = [ b'SETCMD', b'RETCMD' ]
    
    MESSAGE_TYPE = {
        0x01: 'ChangeName',
        0x02: 'ChangePassword',
        0x03: 'ClearPassword',
        0x04: 'Reboot',
        0x08: 'ChangeResolution',
        0x09: 'GetResolution',
        0x90: 'GetRemoteKey',
    }
    
    _fields_ = [
        ('magic', c_char * 6),  # 'SETCMD'
        ('cmdSendIndex', c_uint32),  # Increments with every message (?)
        ('type', c_uint16),
        ('length', c_uint16),  # Length of data following message header
    ]

    
    def validate(self):
        # Initialize
        self.data = b''
        
        # Validate
        if self.magic not in self.__class__.MAGIC:
            raise ValueError(f'Invalid magic bytes for {self.__class__.__name__}: {self.magic}')
        return
    
    
    @property
    def type_name(self):
        return self.__class__.MESSAGE_TYPE[self.type]
    
    
    def get_bytes(self):
        return super().get_bytes() + self.data
    
    
    def __bytes__(self):
        return bytes(self.get_bytes())
