from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from edict.reporting.caf_stats import load_stats


def _run(cmd: list[str], timeout: int = 10) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout)
        return out.decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: {exc}"


def _get_cron_list() -> dict:
    txt = _run(["openclaw", "cron", "list"], timeout=15)
    return {"raw": txt}


def _get_docker_ps() -> dict:
    txt = _run(["docker", "ps", "--format", "{{json .}}"], timeout=10)
    rows = []
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith("ERROR"):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"containers": rows, "raw_error": txt if txt.startswith("ERROR") else None}


def _proc_running(substr: str) -> bool:
    txt = _run(["ps", "aux"], timeout=10)
    return substr in txt


def _caf_health() -> dict:
    stats_path = Path(os.getenv("EDICT_CAF_STATS_PATH", "data/caf_stats.json"))
    stats = load_stats(stats_path)
    if stats is None:
        return {"winrate": None, "n": 0, "long": None, "short": None}

    def pack(wl):
        return {
            "win": wl.win,
            "loss": wl.loss,
            "n": wl.n,
            "winrate": wl.winrate,
        }

    return {
        "long": pack(stats.long),
        "short": pack(stats.short),
    }


def create_app() -> FastAPI:
    app = FastAPI(title="edict-hub", version="0.1")

    @app.get("/api/status")
    async def status():
        now = datetime.now(tz=timezone.utc).isoformat()
        return {
            "now_utc": now,
            "services": {
                "edict_tv_serve": _proc_running("edict tv-serve"),
                "cloudflared": _proc_running("cloudflared tunnel"),
                "edict_caf_watch": _proc_running("edict caf-watch"),
            },
            "cron": _get_cron_list(),
            "docker": _get_docker_ps(),
            "caf": _caf_health(),
        }

    @app.get("/", response_class=HTMLResponse)
    async def home():
        return """<!doctype html>
<html><head><meta charset='utf-8'><title>OpenClaw Hub</title>
<style>
body{font-family:ui-sans-serif,system-ui;max-width:900px;margin:24px auto;}
pre{background:#111;color:#eee;padding:12px;border-radius:8px;overflow:auto;}
.bad{color:#b91c1c;font-weight:700}
.good{color:#15803d;font-weight:700}
.warn{color:#a16207;font-weight:700}
</style></head>
<body>
<h1>OpenClaw / edict 状态面板（本机）</h1>
<p>刷新即可更新。数据接口：<a href='/api/status'>/api/status</a></p>
<div id='app'>loading...</div>
<script>
async function main(){
  const r=await fetch('/api/status');
  const j=await r.json();
  const s=j.services;
  function tag(v){return v?"<span class='good'>在线</span>":"<span class='bad'>离线</span>"}
  const caf=j.caf;
  let cafLine='暂无';
  if(caf && caf.long){
    const lw=caf.long.winrate, sw=caf.short.winrate;
    const lwTxt = (lw==null?'-':(lw*100).toFixed(1)+'%');
    const swTxt = (sw==null?'-':(sw*100).toFixed(1)+'%');
    cafLine = `做多胜率: ${lwTxt} (n=${caf.long.n}) ｜ 做空胜率: ${swTxt} (n=${caf.short.n})`;
  }
  document.getElementById('app').innerHTML = `
  <h2>常驻服务</h2>
  <ul>
    <li>tv-serve: ${tag(s.edict_tv_serve)}</li>
    <li>cloudflared: ${tag(s.cloudflared)}</li>
    <li>caf-watch: ${tag(s.edict_caf_watch)}</li>
  </ul>
  <h2>CAF</h2>
  <p>${cafLine}</p>
  <h2>Cron（raw）</h2>
  <pre>${(j.cron.raw||'').replaceAll('<','&lt;')}</pre>
  <h2>Docker 容器（摘要）</h2>
  <pre>${JSON.stringify(j.docker.containers,null,2)}</pre>
  `;
}
main();
</script>
</body></html>"""

    return app
