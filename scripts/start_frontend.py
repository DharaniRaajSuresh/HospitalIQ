import subprocess, os, sys
log = open("frontend_out.log", "w", encoding="utf-8")
err = open("frontend_err.log", "w", encoding="utf-8")
p = subprocess.Popen(
    ["npm.cmd", "run", "dev"],
    cwd=os.path.join(os.path.dirname(__file__), "frontend"),
    stdout=log, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW
)
with open("frontend.pid", "w") as f:
    f.write(str(p.pid))
print(f"Frontend started (PID: {p.pid})")
