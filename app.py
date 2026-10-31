from flask import Flask, render_template, request, jsonify, Response
import sqlite3
import base64
import secrets
import os
from datetime import datetime

app = Flask(__name__)
DB_PATH = "encoder.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS scripts (id INTEGER PRIMARY KEY AUTOINCREMENT, script_id TEXT UNIQUE NOT NULL, code_encrypted TEXT NOT NULL, created_at TEXT NOT NULL)")
    conn.commit()
    conn.close()

def build_lua_loader(encoded):
    """Tạo mã Lua tự giải mã (Tương thích 100% Roblox Quốc Tế)"""
    chunks = [encoded[i:i+150] for i in range(0, len(encoded), 150)]
    
    parts = []
    parts.append("local _c={}")
    for chunk in chunks:
        parts.append("_c[#_c+1]='%s'" % chunk)
    parts.append("local _d=table.concat(_c)")
    parts.append("_c=nil")
    
    parts.append("local _b='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'")
    parts.append("local function _dec(s)")
    parts.append("s=string.gsub(s,'[^'.._b..'=]','')")
    parts.append("return (s:gsub('.',function(x)")
    parts.append("if x=='=' then return '' end")
    parts.append("local r,f='',(_b:find(x,1,true)-1)")
    parts.append("for i=6,1,-1 do r=r..(f%2^i-f%2^(i-1)>0 and '1' or '0') end")
    parts.append("return r")
    parts.append("end):gsub('%d%d%d?%d?%d?%d?%d?%d?',function(x)")
    parts.append("if #x~=8 then return '' end")
    parts.append("local c=0")
    parts.append("for i=1,8 do c=c+(x:sub(i,i)=='1' and 2^(8-i) or 0) end")
    parts.append("return string.char(c)")
    parts.append("end))")
    parts.append("end")
    
    parts.append("local _code=_dec(_d)")
    parts.append("_d=nil")
    
    # Sử dụng load cho Roblox Quốc tế
    parts.append("local _fn=load or loadstring")
    parts.append("if _fn then _fn(_code)() end")
    
    return chr(10).join(parts)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/encode", methods=["POST"])
def api_encode():
    try:
        data = request.get_json()
        code = data.get("code", "").strip()
        if not code:
            return jsonify({"ok": False, "error": "Nhap code Lua!"})

        encoded = base64.b64encode(code.encode('utf-8')).decode('utf-8')
        init_db()
        script_id = secrets.token_urlsafe(8)
        
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO scripts (script_id, code_encrypted, created_at) VALUES (?, ?, ?)",
                     (script_id, encoded, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

        host = request.host_url.rstrip("/")
        raw_url = host + "/raw/" + script_id
        loadstring_url = 'loadstring(game:HttpGet("' + raw_url + '"))()'

        return jsonify({
            "ok": True,
            "raw_url": raw_url,
            "loadstring_url": loadstring_url
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/raw/<script_id>")
def raw_script(script_id):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT code_encrypted FROM scripts WHERE script_id = ?", (script_id,)).fetchone()
    conn.close()

    if not row:
        return "-- Script khong ton tai hoac da bi xoa.\nreturn", 404

    loader = build_lua_loader(row["code_encrypted"])

    # CHẶN XEM CODE: Nếu là trình duyệt (có chữ Mozilla, Chrome, Safari) thì chặn
    ua = request.headers.get("User-Agent", "").lower()
    if "mozilla" in ua or "chrome" in ua or "safari" in ua:
        return render_template("protected.html"), 200

    # Nếu không phải trình duyệt (Delta X, Roblox, Krnl...) thì cho phép đọc code Lua
    return Response(loader, mimetype="text/plain")

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)