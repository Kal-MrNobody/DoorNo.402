import subprocess
import os
import time
import sys

def main():
    servers = [
        ("demo/servers/cryptoinsider", "server.js", 3001),
        ("demo/servers/chainpulse", "server.js", 3002),
        ("demo/servers/blockbrief", "server.js", 3003),
        ("demo/servers/nodetimes", "server.js", 3004),
        ("demo/servers/web3daily", "server.js", 3005),
        ("demo/servers/combo", "server.js", 3006),
    ]

    processes = []
    print("Starting all DoorNo.402 Demo Servers...")

    for folder, script, port in servers:
        path = os.path.join(os.getcwd(), folder, script)
        if not os.path.exists(path):
            print(f"Error: {path} not found")
            continue
            
        print(f"Starting {folder} on port {port}...")
        
        # Start the node server in the background
        p = subprocess.Popen(["node", script], cwd=os.path.join(os.getcwd(), folder), 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append((folder, p))

    print("\nAll servers started! Press Ctrl+C to shut them down.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down all servers...")
        for folder, p in processes:
            p.terminate()
        print("Done.")

if __name__ == "__main__":
    main()
