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

def start_mcp_server(server_name: str, server_path: str, port: int = None, sse: bool = False):
    """Start an MCP server as HTTP endpoint or SSE endpoint"""
    try:
        print(f"🚀 Starting {server_name}...")
        
        # Change to server directory
        server_dir = Path(server_path).parent
        server_file = Path(server_path).name
        
        # Run the server directly with Python and appropriate arguments
        if port:
            if sse:
                cmd = [sys.executable, server_file, "--port", str(port), "--sse"]
            else:
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
    
    # Check for SSE mode
    import sys
    sse_mode = '--sse' in sys.argv
    mode_text = "SSE" if sse_mode else "MCP"
    
    print(f"Starting all servers in {mode_text} mode...\n")
    
    # Define servers to start with appropriate ports
    if sse_mode:
        # SSE servers use ports 8003-8005
        base_ports = [8003, 8004, 8005]
    else:
        # MCP servers use ports 8000-8002
        base_ports = [8000, 8001, 8002]
    
    servers = [
        {
            "name": f"Main RAG Server ({mode_text})",
            "path": "mcp-rag/main.py",
            "port": base_ports[0],
            "sse": sse_mode
        },
        {
            "name": f"Web Search Server ({mode_text})",
            "path": "mcp-websearch/main.py",
            "port": base_ports[1],
            "sse": sse_mode
        },
    ]
    
    # Start each server
    processes = []
    for server in servers:
        process = start_mcp_server(
            server["name"],
            server["path"],
            server.get("port"),
            server.get("sse", False)
        )
        if process:
            processes.append((server["name"], process, server["port"]))
        time.sleep(1)  # Small delay between starts
    
    if processes:
        print(f"\n🎉 Successfully started {len(processes)} servers!")
        print("\nServers running:")
        for name, process, port in processes:
            print(f"  • {name} (PID: {process.pid}) on port {port}")
        
        print(f"\n📋 {mode_text} Server endpoints:")
        if sse_mode:
            print("  • Main RAG Server (SSE): http://localhost:8003")
            print("    - Health: http://localhost:8003/health")
            print("    - RAG Query: http://localhost:8003/rag-query?query=<query>")
            print("    - Corporate Actions: http://localhost:8003/search-corporate-actions?query=<query>")
            print("  • Web Search Server (SSE): http://localhost:8004")
            print("    - Health: http://localhost:8004/health") 
            print("    - Web Search: http://localhost:8004/web-search?query=<query>")
            print("    - News Search: http://localhost:8004/news-search?query=<query>")
        else:
            print("  • Main RAG Server (MCP): http://localhost:8000/mcp")
            print("  • Web Search Server (MCP): http://localhost:8001/mcp") 
            
        print("\n⌨️ Press Ctrl+C to stop all servers")
        
        try:
            # Wait for user interrupt
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down servers...")
            for name, process, port in processes:
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
