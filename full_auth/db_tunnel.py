from sshtunnel import SSHTunnelForwarder
from os import getenv, path
import atexit
import sys
import time


class DatabaseTunnel:
    def __init__(self):
        self.tunnel = None

    def create_tunnel(self):
        if self.tunnel is None:
            ssh_host = getenv('SSH_HOST', '3.7.22.83')
            ssh_port = int(getenv('SSH_PORT', '22'))
            ssh_username = getenv('SSH_USERNAME', 'root')
            ssh_password = getenv('SSH_PASSWORD')
            ssh_pkey_path = getenv('SSH_PRIVATE_KEY_PATH')
            
            print("🔍 SSH Configuration:")
            print(f"   Host: {ssh_host}")
            print(f"   Port: {ssh_port}")
            print(f"   Username: {ssh_username}")
            print(f"   Private Key Path: {ssh_pkey_path}")
            print(f"   Password: {'***' if ssh_password else 'Not set'}")
            
            # Check if we have authentication credentials
            if not ssh_password and not ssh_pkey_path:
                raise ValueError(
                    "SSH authentication required: Set either SSH_PASSWORD or SSH_PRIVATE_KEY_PATH environment variable"
                )
            
            # Check if private key file exists
            if ssh_pkey_path and not path.exists(ssh_pkey_path):
                raise FileNotFoundError(f"SSH private key file not found: {ssh_pkey_path}")
            
            try:
                # Prepare SSH tunnel arguments
                tunnel_args = {
                    'ssh_host': (ssh_host, ssh_port),
                    'ssh_username': ssh_username,
                    'remote_bind_address': (
                        getenv('MYSQL_HOST_DIRECT', 'emcure.cyfg4jtdu8bn.ap-south-1.rds.amazonaws.com'),
                        int(getenv('MYSQL_PORT_DIRECT', '3306')),
                    ),
                    'local_bind_address': ('127.0.0.1', int(getenv('MYSQL_PORT', '3307'))),
                    'set_keepalive': 30,
                }
                
                # Add authentication method
                if ssh_pkey_path and path.exists(ssh_pkey_path):
                    tunnel_args['ssh_pkey'] = ssh_pkey_path
                    print(f"🔐 Using SSH private key: {ssh_pkey_path}")
                elif ssh_password:
                    tunnel_args['ssh_password'] = ssh_password
                    print("🔐 Using SSH password authentication")
                
                # Create and start tunnel
                print("🚀 Creating SSH tunnel...")
                self.tunnel = SSHTunnelForwarder(**tunnel_args)
                self.tunnel.start()
                
                time.sleep(2)
                
                if self.tunnel.is_alive:
                    print("✅ SSH tunnel created successfully!")
                    print(f"   Local: 127.0.0.1:{getenv('MYSQL_PORT', '3307')}")
                    print(f"   Remote: {getenv('MYSQL_HOST_DIRECT') or 'emcure.cyfg4jtdu8bn.ap-south-1.rds.amazonaws.com'}:{getenv('MYSQL_PORT_DIRECT', '3306')}")
                    atexit.register(self.close_tunnel)
                else:
                    raise Exception("SSH tunnel failed to start")
                    
            except Exception as e:
                print(f"❌ SSH tunnel creation failed: {str(e)}")
                if self.tunnel:
                    self.tunnel.stop()
                    self.tunnel = None
                raise e
                
        return self.tunnel

    def close_tunnel(self):
        if self.tunnel:
            print("🔒 Closing SSH tunnel...")
            try:
                self.tunnel.stop()
                print("✅ SSH tunnel closed successfully")
            except Exception as e:
                print(f"❌ Error closing tunnel: {e}")
            finally:
                self.tunnel = None

db_tunnel = DatabaseTunnel()