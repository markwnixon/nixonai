import time
import paramiko
import traceback
import os
from datetime import datetime

# Paths
REMOTE_SCRIPT = "/home/mark/flask/agents/shellscripts/getpin2.sh"
LOG_DIR = "/home/mark/pin_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# SSH credentials
SSH_HOST = '172.233.199.180'
SSH_USER = 'mark'
SSH_KEY = '/home/nixonai/.ssh/id_rsa'

# Optional queue file
QUEUE_FILE = "/home/nixonai/task_queue.txt"

def run_remote_job(pinid, scac="TEST", domain="localhost", mode="all"):
    """Executes a remote pin-getting job via SSH."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"pinout_{pinid}_{timestamp}.log")

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SSH_HOST, username=SSH_USER, key_filename=SSH_KEY)

        cmd = (
            f"source /home/mark/flask/flaskenv/bin/activate && "
            f"/bin/bash {REMOTE_SCRIPT} {scac} {pinid} {mode} {domain}"
        )

        print(f"[Worker] Executing: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)

        out = stdout.read().decode()
        err = stderr.read().decode()
        if out:
            with open(log_file, "a") as f:
                f.write("[STDOUT]\n" + out + "\n")
        if err:
            with open(log_file, "a") as f:
                f.write("[STDERR]\n" + err + "\n")

        ssh.close()
        print(f"[Worker] Finished job for PINID {pinid}. Log: {log_file}")

    except Exception as e:
        print(f"[Worker] Exception for PINID {pinid}: {e}")
        traceback.print_exc()

def worker_loop():
    """Main loop for always-on worker to pick up jobs."""
    while True:
        try:
            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE, "r") as f:
                    jobs = [line.strip() for line in f if line.strip()]

                open(QUEUE_FILE, "w").close()

                for job in jobs:
                    # Expected format in queue: pinid|scac|domain|mode
                    parts = job.split("|")
                    pinid = parts[0]
                    scac = parts[1] if len(parts) > 1 else "TEST"
                    domain = parts[2] if len(parts) > 2 else "localhost"
                    mode = parts[3] if len(parts) > 3 else "all"

                    run_remote_job(pinid, scac, domain, mode)

            time.sleep(2)

        except Exception:
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    print("[Worker] Starting always-on worker without task IDs...")
    worker_loop()



