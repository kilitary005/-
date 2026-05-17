#!/usr/bin/env python3
"""
端口转发客户端
运行在内网本机上，连接公网服务器
"""

import socket
import threading
import sys
import time

class PortForwardClient:
    def __init__(self, server_host, server_port=8888, local_host='127.0.0.1', local_port=8000):
        self.server_host = server_host
        self.server_port = server_port
        self.local_host = local_host
        self.local_port = local_port
        self.running = True
        self.server_socket = None
        
    def forward_to_local(self, server_conn, local_conn):
        """将服务器数据转发到本地服务"""
        try:
            while self.running:
                data = server_conn.recv(4096)
                if not data:
                    break
                print(f"[→] 转发到本地: {len(data)} 字节")
                local_conn.sendall(data)
        except Exception as e:
            print(f"[-] 转发到本地时出错: {e}")
        finally:
            local_conn.close()
    
    def forward_to_server(self, local_conn, server_conn):
        """将本地数据转发到服务器"""
        try:
            while self.running:
                data = local_conn.recv(4096)
                if not data:
                    break
                print(f"[←] 转发到服务器: {len(data)} 字节")
                server_conn.sendall(data)
        except Exception as e:
            print(f"[-] 转发到服务器时出错: {e}")
        finally:
            server_conn.close()
    
    def handle_connection(self, server_conn):
        """处理与服务器的连接"""
        try:
            # 连接到本地服务
            local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local_socket.connect((self.local_host, self.local_port))
            print(f"[+] 连接到本地服务 {self.local_host}:{self.local_port}")
            
            # 启动双向转发线程
            to_local_thread = threading.Thread(
                target=self.forward_to_local, 
                args=(server_conn, local_socket)
            )
            to_server_thread = threading.Thread(
                target=self.forward_to_server, 
                args=(local_socket, server_conn)
            )
            
            to_local_thread.daemon = True
            to_server_thread.daemon = True
            
            to_local_thread.start()
            to_server_thread.start()
            
            # 等待线程结束
            to_local_thread.join()
            to_server_thread.join()
            
        except Exception as e:
            print(f"[-] 处理连接时出错: {e}")
        finally:
            server_conn.close()
    
    def start(self):
        """启动客户端"""
        while self.running:
            try:
                print(f"[*] 尝试连接到服务器 {self.server_host}:{self.server_port}...")
                
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.connect((self.server_host, self.server_port))
                
                print(f"[+] 成功连接到服务器")
                print(f"[*] 开始端口转发: 服务器端口 {self.server_port} ↔ 本地 {self.local_host}:{self.local_port}")
                
                # 处理这个连接
                self.handle_connection(self.server_socket)
                
            except Exception as e:
                print(f"[-] 连接失败: {e}")
                print("[*] 5秒后重试...")
                time.sleep(5)
    
    def stop(self):
        """停止客户端"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[*] 客户端已停止")

def main():
    server_host = input("输入ip: ")
    server_port = int(input("输入端口: "))  # 转换为整数
    local_port = int(input("输入本地端口: "))  # 转换为整数
    
    client = PortForwardClient(server_host, server_port, local_port=local_port)
    
    try:
        client.start()
    except KeyboardInterrupt:
        print("\n[*] 收到中断信号，正在关闭客户端...")
        client.stop()

if __name__ == "__main__":
    main()