import subprocess
import sys
import os
import time
import re

# Add root directory to path for config loading
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from utils.config_loader import config
except ImportError:
    print("Error: Could not import config_loader. Ensure you are running from the project structure.")
    sys.exit(1)

def start_tunnel():
    enabled = config.get('tunnel.enabled', False)
    if not enabled:
        print("Tunnel is disabled in config.yaml. Set tunnel.enabled to true to use this script.")
        return

    local_addr = config.get('tunnel.local_address', 'http://localhost:5000')
    tunnel_type = config.get('tunnel.type', 'quick')
    tunnel_name = config.get('tunnel.name', '')
    creds_file = config.get('tunnel.credentials_file', '')

    print(f"Starting Cloudflare Tunnel ({tunnel_type})...")
    
    # Path to blank config to avoid conflicts with global ~/.cloudflared/config.yml
    blank_config = os.path.join(os.path.dirname(__file__), 'blank_config.yml')

    if tunnel_type == "named":
        if not tunnel_name:
            print("Error: 'tunnel.name' must be specified in config.yaml for named tunnels.")
            return
        # Basic command for named tunnel
        cmd = ["cloudflared", "tunnel", "run", tunnel_name]
        if creds_file:
            cmd.extend(["--credentials-file", creds_file])
    else:
        # Default to quick tunnel
        # We use 127.0.0.1 instead of localhost for better Windows reliability
        target_url = local_addr.replace('localhost', '127.0.0.1')
        print(f"Exposing {target_url} via quick tunnel...")
        # Force http2 protocol to avoid 1033 errors often caused by QUIC instability
        cmd = ["cloudflared", "tunnel", "--url", target_url, "--config", blank_config, "--protocol", "http2"]
    
    try:
        # Start the process
        # We use a context manager or just Popen to stream output
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            bufsize=1
        )

        print("\n--- WAITING FOR CLOUDFLARE URL ---")
        print("Hint: Look for a link ending in '.trycloudflare.com'\n")

        # Monitor output for the URL
        url_pattern = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
        
        found_url = False
        try:
            for line in process.stdout:
                print(line.strip())
                
                # Try to find the URL in the log lines
                if not found_url:
                    match = url_pattern.search(line)
                    if match:
                        found_url = True
                        public_url = match.group(0)
                        print("\n" + "="*50)
                        print(f"🚀 YOUR PUBLIC URL IS READY:")
                        print(f"👉 {public_url}")
                        print("="*50 + "\n")
                        print("Keep this window open to maintain the connection.")
        
        except KeyboardInterrupt:
            print("\nShutting down tunnel...")
            process.terminate()
            
    except FileNotFoundError:
        print("Error: 'cloudflared' command not found. Please ensure it is installed and in your PATH.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    start_tunnel()
