#!/usr/bin/env python3
"""
Start All MCP Servers
Simple script to start all three MCP servers for the Corporate Actions platform
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def start_mcp_server(server_name: str, server_path: str, port: int = None):
    """Start an MCP server as HTTP endpoint"""
    try:
        print(f"🚀 Starting {server_name}...")
        
        # Change to server directory
        server_dir = Path(server_path).parent
        server_file = Path(server_path).name
        
        # Run the server directly with Python and --port argument
        if port:
            cmd = [sys.executable, server_file, "--port", str(port)]
        else:
            cmd = [sys.executable, server_file]
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            cwd=server_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give server time to start
        time.sleep(3)
        
        print(f"✅ {server_name} started with PID {process.pid} on port {port}")
        return process
        
    except Exception as e:
        print(f"❌ Failed to start {server_name}: {e}")
        return None

def main():
    """Start all MCP servers"""
    print("🎯 Corporate Actions MCP Platform")
    print("=" * 50)
    print("Starting all MCP servers...\n")
    
    # Define servers to start
    servers = [
        {
            "name": "Main RAG Server",
            "path": "mcp-server/main.py",
            "port": 8000
        },
        {
            "name": "Web Search Server", 
            "path": "mcp-websearch/main.py",
            "port": 8001
        },
        {
            "name": "Comments Server",
            "path": "mcp-comments/main.py", 
            "port": 8002
        }
    ]
    
    # Start each server
    processes = []
    for server in servers:
        process = start_mcp_server(
            server["name"],
            server["path"],
            server.get("port")
        )
        if process:
            processes.append((server["name"], process))
        time.sleep(1)  # Small delay between starts
    
    if processes:
        print(f"\n🎉 Successfully started {len(processes)} MCP servers!")
        print("\nServers running:")
        for name, process in processes:
            print(f"  • {name} (PID: {process.pid})")
            print("\n📋 Server endpoints:")
            print("  • Main RAG Server: http://localhost:8000/mcp")
            print("  • Web Search Server: http://localhost:8001/mcp") 
            print("  • Comments Server: http://localhost:8002/mcp")
            
            print("\n⌨️ Press Ctrl+C to stop all servers")
        
        try:
            # Wait for user interrupt
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down servers...")
            for name, process in processes:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    print(f"✅ {name} stopped")
                except subprocess.TimeoutExpired:
                    process.kill()
                    print(f"🔥 {name} force killed")
                except Exception as e:
                    print(f"⚠️ Error stopping {name}: {e}")
    else:
        print("❌ No servers started successfully")
        sys.exit(1)

if __name__ == "__main__":
    main()
