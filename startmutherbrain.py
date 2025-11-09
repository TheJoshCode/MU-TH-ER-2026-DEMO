# launch.py  –  COPY-PASTE THIS EXACTLY (NOW FULLY ROBUST FOR .EXE ON WINDOWS + GRACEFUL SHUTDOWN)
import subprocess
import sys
import os
import signal
import atexit
from pathlib import Path

# Store all launched processes
PROCESSES = []

# ------------------------------------------------------------------
# Clean-up: Kill all spawned processes on exit (Ctrl+C, window close, crash, etc.)
# ------------------------------------------------------------------
def kill_all_processes():
    print("[MU/TH/ER] Entering kill_all_processes function.")
    print("\nShutting down... Killing all child processes.")
    for p in PROCESSES:
        print(f"[MU/TH/ER] Checking process PID {p.pid} status.")
        if p.poll() is None:  # Still running
            print(f"[MU/TH/ER] Process PID {p.pid} is still running. Attempting graceful termination.")
            try:
                p.terminate()      # Graceful (sends CTRL_BREAK on Windows if possible)
                print(f"[MU/TH/ER] Waiting for process PID {p.pid} to terminate.")
                p.wait(timeout=5)  # Give it a few seconds to shut down cleanly
                print(f"[MU/TH/ER] Process PID {p.pid} terminated gracefully.")
            except subprocess.TimeoutExpired:
                print(f"Process {p.pid} didn't terminate gracefully – forcing kill.")
                print(f"[MU/TH/ER] Forcing kill on process PID {p.pid} due to timeout.")
                p.kill()
            except Exception as e:
                print(f"Error terminating {p.pid}: {e}")
                print(f"[MU/TH/ER] Exception during termination of PID {p.pid}: {e}. Attempting force kill.")
                try:
                    p.kill()
                except:
                    print(f"[MU/TH/ER] Failed to force kill PID {p.pid}.")
                    pass
    print("All child processes terminated. Bye!")
    print("[MU/TH/ER] Exiting kill_all_processes function.")

atexit.register(kill_all_processes)
print("[MU/TH/ER] Registered kill_all_processes with atexit.")

# ------------------------------------------------------------------
# Signal / Console Control Handlers (cross-platform + Windows window close)
# ------------------------------------------------------------------
def _exit_after_kill(sig=None, frame=None):
    print(f"[MU/TH/ER] Entering _exit_after_kill with signal {sig}.")
    kill_all_processes()
    print("[MU/TH/ER] Calling sys.exit(0) after killing processes.")
    sys.exit(0)

# Ctrl+C
signal.signal(signal.SIGINT, _exit_after_kill)
print("[MU/TH/ER] Set SIGINT handler to _exit_after_kill.")

# SIGTERM (e.g. kill command on Linux or taskkill on Windows)
signal.signal(signal.SIGTERM, _exit_after_kill)
print("[MU/TH/ER] Set SIGTERM handler to _exit_after_kill.")

# Windows-specific: proper console window close / Ctrl+Break / Ctrl+C handling
if os.name == 'nt':
    print("[MU/TH/ER] Detected Windows OS. Setting up Windows-specific console handler.")
    import ctypes
    from ctypes import c_uint
    PHANDLER_ROUTINE = ctypes.WINFUNCTYPE(c_uint, c_uint)

    def _windows_ctrl_handler(ctrl_type: int) -> int:
        print(f"[MU/TH/ER] Entering _windows_ctrl_handler with ctrl_type {ctrl_type}.")
        if ctrl_type in (0, 1, 2):  # CTRL_C_EVENT, CTRL_BREAK_EVENT, CTRL_CLOSE_EVENT
            print("\nWindows console event received – initiating shutdown.")
            print("[MU/TH/ER] Windows console event detected. Calling _exit_after_kill.")
            _exit_after_kill()
            print("[MU/TH/ER] Returning 1 from _windows_ctrl_handler (handled).")
            return 1  # Handled
        print("[MU/TH/ER] Returning 0 from _windows_ctrl_handler (not handled).")
        return 0  # Not handled – let other handlers / default run

    handler = PHANDLER_ROUTINE(_windows_ctrl_handler)
    ctypes.windll.kernel32.SetConsoleCtrlHandler(handler, 1)
    print("[MU/TH/ER] Set Windows console control handler.")

# ------------------------------------------------------------------
# 1. Find the folder where THIS .exe (or .py) is located
# ------------------------------------------------------------------
print("[MU/TH/ER] Determining executable directory.")
if getattr(sys, 'frozen', False):
    EXE_DIR = Path(sys.executable).parent
    print("[MU/TH/ER] Running as frozen executable. EXE_DIR set to parent of sys.executable.")
else:
    EXE_DIR = Path(__file__).parent
    print("[MU/TH/ER] Running as script. EXE_DIR set to parent of __file__.")

ROOT = EXE_DIR.resolve()
print(f"Launcher running from: {ROOT}")
print(f"[MU/TH/ER] ROOT directory resolved to: {ROOT}")

# ------------------------------------------------------------------
# 2. Build absolute paths
# ------------------------------------------------------------------
print("[MU/TH/ER] Building absolute paths for directories.")
SERVER_DIR = ROOT / '_internal' / 'mutherbrain'
print(f"[MU/TH/ER] SERVER_DIR set to: {SERVER_DIR}")
GAME_DIR   = ROOT / '_internal' / 'muthergame'
print(f"[MU/TH/ER] GAME_DIR set to: {GAME_DIR}")

# ------------------------------------------------------------------
# 3. Prepare Windows-specific startup info for hidden console (allows graceful terminate)
# ------------------------------------------------------------------
server_startupinfo = None
server_creationflags = 0
print("[MU/TH/ER] Initializing server_startupinfo and server_creationflags.")

if os.name == 'nt':
    print("[MU/TH/ER] Windows detected. Configuring STARTUPINFO for hidden console.")
    si = subprocess.STARTUPINFO()
    si.dwFlags = subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    server_startupinfo = si
    server_creationflags = subprocess.CREATE_NEW_CONSOLE  # Gives server its own hidden console → terminate() can send CTRL_BREAK
    print("[MU/TH/ER] Configured Windows-specific startup info and creation flags.")

# ------------------------------------------------------------------
# 4. Start the server
# ------------------------------------------------------------------
print("Starting llama-server...")
print("[MU/TH/ER] Preparing to start llama-server.")
server_cmd = 'llama-server.exe' if os.name == 'nt' else 'llama-server'
print(f"[MU/TH/ER] Server command set to: {server_cmd}")

server_path = SERVER_DIR / server_cmd
print(f"[MU/TH/ER] Checking if server executable exists at: {server_path}")
if not server_path.exists():
    print(f"[MU/TH/ER] Error: Server executable not found at {server_path}. Aborting launch.")
    sys.exit(1)
else:
    print(f"[MU/TH/ER] Server executable found. Listing contents of SERVER_DIR for debug:")
    try:
        print(os.listdir(SERVER_DIR))
    except Exception as e:
        print(f"[MU/TH/ER] Failed to list SERVER_DIR: {e}")

server = subprocess.Popen([
    str(server_path),
    '-m', 'Qwen3-1.7B-Q4_K_M.gguf',
    '--port', '5001',
    '--n-gpu-layers', '29'
], cwd=SERVER_DIR,
   startupinfo=server_startupinfo,
   creationflags=server_creationflags,
   # No stdio redirection – output goes to hidden console (or nowhere on Linux)
)
print(f"[MU/TH/ER] Launched server process with command: {server.args}")
PROCESSES.append(server)
print(f"llama-server PID: {server.pid}")
print(f"[MU/TH/ER] Added server PID {server.pid} to PROCESSES list.")

# ------------------------------------------------------------------
# 5. Start the game
# ------------------------------------------------------------------
print("Launching Muther2026Screen.exe...")
print("[MU/TH/ER] Preparing to launch Muther2026Screen.exe.")
game_cmd = 'Muther2026Screen.exe'
game_path = GAME_DIR / game_cmd
print(f"[MU/TH/ER] Checking if game executable exists at: {game_path}")
if not game_path.exists():
    print(f"[MU/TH/ER] Error: Game executable not found at {game_path}")
    print(f"[MU/TH/ER] Listing contents of GAME_DIR for debug:")
    try:
        print(os.listdir(GAME_DIR))
    except Exception as e:
        print(f"[MU/TH/ER] Failed to list GAME_DIR: {e}")
    print("[MU/TH/ER] Aborting game launch due to missing executable.")
    # Continue to monitoring, or sys.exit(1) if you want to abort entirely
else:
    print(f"[MU/TH/ER] Game executable found. Listing contents of GAME_DIR for debug:")
    try:
        print(os.listdir(GAME_DIR))
    except Exception as e:
        print(f"[MU/TH/ER] Failed to list GAME_DIR: {e}")
    game = subprocess.Popen([str(game_path)], cwd=GAME_DIR)
    print(f"[MU/TH/ER] Launched game process with command: {game.args}")
    PROCESSES.append(game)
    print(f"Game PID: {game.pid}")
    print(f"[MU/TH/ER] Added game PID {game.pid} to PROCESSES list.")

# ------------------------------------------------------------------
# 6. Keep launcher alive + monitor processes
# ------------------------------------------------------------------
print("\nLauncher is running. Close this window (or press Ctrl+C) to shut everything down cleanly.\n")
print("[MU/TH/ER] Entering main monitoring loop.")

try:
    while True:
        print("[MU/TH/ER] Starting iteration of monitoring loop.")
        for p in PROCESSES:
            print(f"[MU/TH/ER] Checking status of process PID {p.pid}.")
            if p.poll() is not None:
                code = p.returncode
                name = "llama-server" if p == server else "Muther2026Screen.exe"
                print(f"{name} (PID {p.pid}) exited with code {code}")
                print(f"[MU/TH/ER] Detected exit of {name} PID {p.pid} with code {code}.")
        # Sleep a bit – signal.pause() works on Unix, sleep fallback everywhere
        if hasattr(signal, 'pause'):
            print("[MU/TH/ER] Using signal.pause() for waiting.")
            signal.pause()
        else:
            print("[MU/TH/ER] Using time.sleep(2) for waiting.")
            __import__('time').sleep(2)
        print("[MU/TH/ER] Ending iteration of monitoring loop.")
except KeyboardInterrupt:
    print("[MU/TH/ER] Caught KeyboardInterrupt in main loop. Handling via signal handler.")
    pass  # Ctrl+C → handled by signal handler above