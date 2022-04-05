#!/usr/bin/env python3
# Author: Sean Pesce

import os
import platform
import socket
import sys


def ping(host, timeout=1):
    """
    Returns True if the target host sent an ICMP response within the specified timeout interval
    """
    # Protect against command injection
    if type(host) != str:
        raise TypeError(f'Non-string type for "host" argument: {type(host)}')
    # Alphabet for IP addresses and host names
    safe_alphabet = '.:0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_'
    for c in host:
        if c not in safe_alphabet:
            raise ValueError(f'Invalid character in "host" argument: "{c}"')
    # Determine argument syntax (Linux vs Windows)
    count_flag = 'c'
    dev_null = '/dev/null'
    quote_char = '\''
    if 'windows' in platform.system().lower():
        count_flag = 'n'
        dev_null = 'NUL'
        quote_char = '"'
    cmd = f'ping -{count_flag} 1 -w {int(timeout)} {quote_char}{host}{quote_char} 2>&1 > {dev_null}'
    retcode = os.system(cmd)
    return retcode == 0


def udp_send(host, port, data, response_len=4096):
    try:
        #print(f'[Sending data to {host}:{int(port)}]\n{data}\n')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_address = (host, port)
        sent = sock.sendto(data, server_address)
        response, server = sock.recvfrom(response_len)
        #print(f'[Response from {server[0]}:{server[1]}]\n{response}\n')
        if server[0] != host:
            raise ValueError(f'Expected UDP response from {host} but received response from {server[0]}')
    finally:
        sock.close()
    return response


def decode_battery_percentage(val):
    """
    Parses a battery charge percentage from the value returned in GetBattery UDP messages.

    Might not actually work correctly.
    """
    val = 0xffff & int(val)
    if val >= 4080:  # ML_DEVICE_TYPE_B2 || ML_DEVICE_TYPE_M9 || ML_DEVICE_TYPE_X7
    #if val >= 4000:  # !(ML_DEVICE_TYPE_B2 || ML_DEVICE_TYPE_M9 || ML_DEVICE_TYPE_X7)
        percent = 100
    else:
        modifiers = [
            # ML_DEVICE_TYPE_B2 || ML_DEVICE_TYPE_M9 || ML_DEVICE_TYPE_X7
            [ 3750, 3750, 0.15,  50.0 ],
            [ 3520, 3530, 0.135, 20.0 ],  # Difference between first two values here might have been a typo by the app developer
            [ 3450, 3450, 0.14,  10.0 ],
            [ 3390, 3390, 0.15,  1.0  ],
            ## !(ML_DEVICE_TYPE_B2 || ML_DEVICE_TYPE_M9 || ML_DEVICE_TYPE_X7)
            #[ 3700, 3700, 0.1,   70.0 ],
            #[ 3430, 3430, 0.222, 10.0 ],
            #[ 3395, 3395, 0.22,  2.0  ]
        ]
        for m in modifiers:
            if val >= m[0]:
                percent = int((float(val - m[1]) * m[2]) + m[3])
                break
            if m == modifiers[-1]:
                percent = 1
            continue
    if percent > 100:
        percent = 100
    return percent
    
    





