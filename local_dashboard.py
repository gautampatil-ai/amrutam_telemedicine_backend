from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import socket
import urllib.request
import subprocess

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Amrutam Local Services</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0f172a;color:#e2e8f0;font:15px Arial,sans-serif}
header{padding:24px 5%;background:#111c32;border-bottom:1px solid #26344d}
h1{margin:0 0 8px;font-size:26px}header p{margin:0;color:#94a3b8}
main{max-width:1100px;margin:28px auto;padding:0 20px}
.summary{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:22px}
.pill,.card{background:#18243a;border:1px solid #2a3952;border-radius:12px;padding:18px}
.pill{flex:1;min-width:150px}.label{color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:1px}
.value{font-size:22px;font-weight:bold;margin-top:8px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}
.card h2{font-size:18px;margin:0 0 18px}.status{font-weight:bold;margin-bottom:14px}
.up{color:#4ade80}.down{color:#fb7185}.unknown{color:#fbbf24}
.detail{display:flex;justify-content:space-between;gap:12px;border-top:1px solid #2a3952;padding:12px 0}
.muted{color:#94a3b8}button{background:#2563eb;color:white;border:0;padding:11px 16px;border-radius:8px;cursor:pointer}
footer{color:#94a3b8;font-size:12px;margin:22px 0}
</style>
</head>
<body>
<header><h1>Amrutam Service Dashboard</h1><p>Local development · Docker-free service monitor</p></header>
<main>
<div class="summary">
<div class="pill"><div class="label">Overall status</div><div class="value" id="overall">Checking…</div></div>
<div class="pill"><div class="label">Refresh interval</div><div class="value">10 seconds</div></div>
<div class="pill"><div class="label">Environment</div><div class="value">Local</div></div>
</div>
<div class="grid" id="services"></div>
<p style="margin-top:22px"><button onclick="refresh()">Refresh now</button></p>
<footer>Only checks local services. PostgreSQL and Memurai checks use TCP ports; API health uses /health/live. This page is bound to your own computer.</footer>
</main>
<script>
async function refresh(){
  try{
    const r=await fetch('/status'); const d=await r.json();
    document.getElementById('overall').textContent=d.overall;
    document.getElementById('services').innerHTML=d.services.map(s=>
      `<section class="card"><h2>${s.name}</h2><div class="status ${s.ok?'up':s.unknown?'unknown':'down'}">${s.ok?'● Running':s.unknown?'● Unknown':'● Not responding'}</div>
      <div class="detail"><span class="muted">Address</span><span>${s.address}</span></div>
      <div class="detail"><span class="muted">Port</span><span>${s.port}</span></div>
      <div class="detail"><span class="muted">Windows service</span><span>${s.service||'N/A'}</span></div>
      <div class="detail"><span class="muted">Details</span><span>${s.detail}</span></div></section>`).join('');
  }catch(e){document.getElementById('overall').textContent='Dashboard error';}
}
refresh(); setInterval(refresh,10000);
</script>
</body></html>"""

def port_check(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return True
    except OSError:
        return False

def service_state(name):
    try:
        result = subprocess.run(
            ["sc.exe", "query", name], capture_output=True, text=True, timeout=3
        )
        output = (result.stdout + result.stderr).upper()
        if "RUNNING" in output:
            return "Running"
        if "STOPPED" in output:
            return "Stopped"
        return "Not found"
    except Exception:
        return "Unknown"

def get_status():
    services = []
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health/live", timeout=3) as r:
            api_ok = r.status == 200
        api_detail = "GET /health/live returned HTTP 200" if api_ok else "Unexpected response"
    except Exception as e:
        api_ok = False
        api_detail = "API unavailable: " + type(e).__name__
    services.append({"name":"Backend API","address":"127.0.0.1","port":8000,
                     "service":"uvicorn (terminal process)","ok":api_ok,
                     "detail":api_detail})

    for name, port, svc in [
        ("PostgreSQL","5432","postgresql-x64-17"),
        ("Memurai / Redis","6379","Memurai")
    ]:
        listening = port_check(port)
        state = service_state(svc)
        services.append({"name":name,"address":"127.0.0.1","port":port,
                         "service":svc + ": " + state,"ok":listening,
                         "detail":"TCP port accepting connections" if listening else "No TCP response on port"})

    overall = "All services running" if all(s["ok"] for s in services) else "Some services need attention"
    return {"overall":overall,"services":services}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            body = json.dumps(get_status()).encode()
            self.send_response(200)
            self.send_header("Content-Type","application/json; charset=utf-8")
        elif self.path == "/":
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
        else:
            body = b"Not found"
            self.send_response(404)
            self.send_header("Content-Type","text/plain; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1",8765), Handler)
    print("Amrutam dashboard: http://127.0.0.1:8765")
    print("Keep this window open. Press Ctrl+C to stop the dashboard.")
    server.serve_forever()
