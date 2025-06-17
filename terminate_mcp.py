import subprocess
import os
import sys
import signal

# Read PIDs from the file
pids_to_kill = []
try:
    with open("mcps.txt", "r") as f:
        pids_to_kill = [int(line.strip()) for line in f if line.strip()]
except FileNotFoundError:
    print("Error: mcps.txt not found.")
    sys.exit(1) # Exit if the file doesn't exist

for pid in pids_to_kill:
    try:
        if sys.platform == "win32":
            subprocess.run(f'taskkill /F /PID {pid}', shell=True)
            print(f"Sent termination signal to process with PID: {pid}")
        else:
            os.kill(pid, signal.SIGTERM)  # Send a graceful termination signal
            # or os.kill(pid, signal.SIGKILL) # Forceful termination signal
            print(f"Sent termination signal to process with PID: {pid}")

    except ProcessLookupError:
        print(f"Process with PID {pid} not found.")
    except Exception as e:
        print(f"Error terminating process with PID {pid}: {e}")

# Optionally, delete the pids.txt file after successful termination
# os.remove("pids.txt")

print("Termination process completed.")