import subprocess
import os
import sys

rootLocation = "D:\\repos\\corporateactions\\"

# Determine the correct Python executable
python_executable = sys.executable  # Use the same Python interpreter

# List of commands to run and their corresponding process objects
processes = []
commands = [
    f'cd "{rootLocation}\\mcp-rag" && "{python_executable}" main.py --port 8000',
    f'cd "{rootLocation}\\mcp-websearch" && "{python_executable}" main.py --port 8001',
    f'cd "{rootLocation}\\clients\\streamlit-ui" && "{python_executable}" -m streamlit run app_mcp.py',
]

for cmd in commands:
    try:
        if sys.platform == "win32":
            process = subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            process = subprocess.Popen(['gnome-terminal', '-e', f'bash -c "{cmd}; read -p \'Press Enter to close\'"'], shell=False)

        processes.append(process)
        print(f"Launched process with PID: {process.pid}") # Print PID for reference

    except Exception as e:
        print(f"Error launching command: {cmd}\n{e}")

# Store process objects for later use (e.g., to terminate them)
# You might save the PIDs or the process objects themselves in a file or other persistent storage
# For a simple example, let's keep them in the 'processes' list for a bit
# You could write the PIDs to a file, for instance:
with open("mcps.txt", "w") as f:
    for p in processes:
        f.write(str(p.pid) + "\n")

print("All services launched.")

# Keep the main script running (optional, depending on your needs)
# for p in processes:
#     p.wait()