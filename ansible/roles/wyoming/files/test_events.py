import socket
import json
import time

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_event(evt):
    sock.sendto(json.dumps(evt).encode("utf-8"), ("127.0.0.1", 10701))
    print(f"Sent: {evt}")
    time.sleep(1)

send_event({"event": "awake"})
time.sleep(1)
send_event({"event": "transcript", "text": "打开灯"})
time.sleep(1)
send_event({"event": "done"})
