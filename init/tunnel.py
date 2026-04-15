import queue
import re
import subprocess
import sys
import threading


class TunnelProcess:
    def __init__(self, proc: subprocess.Popen):
        self.proc = proc

    def terminate(self):
        if self.proc.poll() is None:
            self.proc.terminate()

    def is_alive(self):
        return self.proc.poll() is None


def _read_output_and_get_rsd(pipe, result_queue: queue.Queue):
    address = None
    port = None

    addr_patterns = [
        re.compile(r"RSD Address:\s*(\S+)"),
        re.compile(r'"address"\s*:\s*"([^"]+)"'),
        re.compile(r'"host"\s*:\s*"([^"]+)"'),
    ]
    port_patterns = [
        re.compile(r"RSD Port:\s*(\d+)"),
        re.compile(r'"port"\s*:\s*(\d+)'),
    ]

    for line in iter(pipe.readline, ''):
        print(line, end='')

        for pat in addr_patterns:
            m = pat.search(line)
            if m:
                address = m.group(1)
                break

        for pat in port_patterns:
            m = pat.search(line)
            if m:
                port = int(m.group(1))
                break

        if address and port:
            result_queue.put((address, port))
            # 不 return，继续挂着，保证 tunnel 进程一直活着
            break

    # 继续把剩余输出读掉，避免缓冲区卡住
    for line in iter(pipe.readline, ''):
        print(line, end='')


def tunnel():
    cmd = [
        sys.executable,
        "-m",
        "pymobiledevice3",
        "lockdown",
        "start-tunnel",
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    q = queue.Queue()
    t = threading.Thread(target=_read_output_and_get_rsd, args=(proc.stdout, q), daemon=True)
    t.start()

    address, port = q.get(timeout=60)
    return TunnelProcess(proc), address, port
