"""
msgproto.py - tiny message framing used by the socket assignments.
TCP is a byte stream, so every message = 4 byte length + JSON body.
"""
import json
import struct


def send_msg(sock, obj):
    body = json.dumps(obj).encode("utf-8")
    sock.sendall(struct.pack(">I", len(body)) + body)


def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None            # other side closed
        buf += chunk
    return buf


def recv_msg(sock):
    header = _recv_exact(sock, 4)
    if header is None:
        return None
    (length,) = struct.unpack(">I", header)
    body = _recv_exact(sock, length)
    return None if body is None else json.loads(body.decode("utf-8"))
