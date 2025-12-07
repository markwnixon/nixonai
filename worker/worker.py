# worker.py
import os
import time
import json
import paramiko
import traceback

TASK_DIR = "/home/nixonai/tasks"
LOG_DIR = "/home/nixonai"
REMOTE_HOST = "172.233.199.180"
REMOTE_USER = "mark"
SSH_KEY = "/home/nixonai/.ssh/id_rsa"

while True:
    try:
        for filename in os.listdir(TASK_DIR):
            if not filename.endswith(".json"):
                continue

            task_file = os.path.join(TASK_DIR, filename)
            with open(task_file) as f:
                task = json.load(f)

            if task["status"] != "starting":
                continue  # skip tasks already running or done

            task_id = filename.replace(".json", "")
            pinid = task["pinid"]
            scac = task["scac"]
            domain = task["domain"]
            mode = task["mode"]

            log_file = os.path.join(LOG_DIR, f"pinout_{task_id}.log")
            remote_script = "/home/mark/flask/agents/shellscripts/getpin2.sh"

            print(f"Running task {task_id}...")

            try:
                task["status"] = "running"
                with open(task_file, "w") as f:
                    json.dump(task, f)

                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    REMOTE_HOST,
                    username=REMOTE_USER,
                    key_filename=SSH_KEY
                )

                # Make sure the remote script is executable
                ssh.exec_command(f"chmod +x {remote_script}")

                cmd = f"nohup /bin/bash {remote_script} {scac} {pinid} {mode} {task_id} {domain} > {log_file} 2>&1 &"
                stdin, stdout, stderr = ssh.exec_command(cmd)
                out = stdout.read().decode()
                err = stderr.read().decode()
                if out: print(f"SSH stdout: {out}")
                if err: print(f"SSH stderr: {err}")

                ssh.close()

                task["status"] = "waiting_for_callback"
                with open(task_file, "w") as f:
                    json.dump(task, f)

                print(f"Task {task_id} launched, log file: {log_file}")

            except Exception as e:
                task["status"] = "error"
                task["result"] = str(e)
                with open(task_file, "w") as f:
                    json.dump(task, f)
                print(f"Error executing task {task_id}: {e}")
                traceback.print_exc()

        time.sleep(5)

    except Exception as e:
        print("Worker main loop exception:", e)
        traceback.print_exc()
        time.sleep(5)

