import socket


def get_lan_ip():
    """获取本机局域网 IP 地址（用于移动设备扫码访问）。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip.startswith('127.'):
                for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                    addr = info[4][0]
                    if not addr.startswith('127.'):
                        return addr
            return ip
        except Exception:
            return '127.0.0.1'
