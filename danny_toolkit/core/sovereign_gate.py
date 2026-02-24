import os
import sys
import ctypes
import psutil
import subprocess

def lock_environment():
    """
    THE SOVEREIGN GATE
    Executes before Omega boots. If any check fails, the process dies instantly.
    """

    # 1. THE ROOT LAW
    expected_root = r"C:\Users\danny\danny-toolkit"
    current_path = os.path.normpath(os.getcwd())
    if current_path.lower() != expected_root.lower():
        sys.exit(f"🚨 [GATE] Execution Denied. Invalid Root. Expected {expected_root}, got {current_path}")

    # 2. THE AUTHORITY LAW (Admin Check)
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        is_admin = False
    if not is_admin:
        sys.exit("🚨 [GATE] Execution Denied. Admin privileges required. Ghost sessions blocked.")

    # 3. THE TERMINAL LAW (Must be PowerShell)
    try:
        parent_pid = os.getppid()
        parent_process = psutil.Process(parent_pid)
        parent_name = parent_process.name().lower()
        if "powershell" not in parent_name and "pwsh" not in parent_name:
            sys.exit(f"🚨 [GATE] Execution Denied. Native PowerShell required. Found: {parent_name}")
    except Exception:
        sys.exit("🚨 [GATE] Execution Denied. Cannot verify parent process.")

    # 4. THE PHYSICAL CONSOLE LAW (No attached/remote sessions)
    session_name = os.environ.get("SESSIONNAME", "").lower()
    if session_name != "console":
        sys.exit(f"🚨 [GATE] Execution Denied. Remote or attached shadow terminal detected ({session_name}).")

    # 5. THE IDENTITY LAW (Email Binding - Option 3)
    authorized_identities = [
        "danny.laurent1988@gmail.com",
        "dannyanny1212@users.noreply.github.com"
    ]

    try:
        git_email = subprocess.check_output(["git", "config", "user.email"]).decode().strip().lower()
        if git_email not in authorized_identities:
            sys.exit(f"🚨 [GATE] Execution Denied. Identity mismatch. Found: {git_email}")
    except Exception:
        sys.exit("🚨 [GATE] Execution Denied. Identity signature missing. No Git config found.")

    print("✅ [SOVEREIGN GATE] Environment Verified. Welcome, Commander Danny.")
    return True

# Run the gate immediately upon import
lock_environment()
