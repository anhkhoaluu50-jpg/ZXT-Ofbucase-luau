from flask import Flask, render_template, request, jsonify
import base64
import secrets
import os

app = Flask(__name__)

def xor_encrypt(data, key):
    return bytes([b ^ key for b in data])

def build_standalone_loader(lua_code):
    key = secrets.randbelow(254) + 1
    encoded_bytes = base64.b64encode(lua_code.encode('utf-8'))
    xored_bytes = xor_encrypt(encoded_bytes, key)
    final_b64 = base64.b64encode(xored_bytes).decode('utf-8')
    
    chunks = [final_b64[i:i+150] for i in range(0, len(final_b64), 150)]
    
    parts = []
    parts.append("-- ANHKHOA OFFLINE LOADER")
    parts.append("local _c={}")
    for c in chunks:
        parts.append("_c[#_c+1]='%s'" % c)
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
    parts.append("local function _xor(s,k)")
    parts.append("local r=''")
    parts.append("for i=1,#s do r=r..string.char(bit32.bxor(string.byte(s,i),k)) end")
    parts.append("return r")
    parts.append("end")
    parts.append("local _raw=_dec(_d)")
    parts.append("_d=nil")
    parts.append("local _code=_xor(_raw, %d)" % key)
    parts.append("_raw=nil")
    parts.append("local _fn=loadstring or load")
    parts.append("if not _fn then return end")
    parts.append("_fn(_code)()")
    
    return chr(10).join(parts)

@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception as e:
        return f"<h1>Lỗi: Không tìm thấy file templates/index.html</h1><p>{str(e)}</p>"

@app.route("/api/encode", methods=["POST"])
def api_encode():
    try:
        data = request.get_json()
        code = data.get("code", "").strip()
        if not code:
            return jsonify({"ok": False, "error": "Nhap code Lua!"})
        
        standalone_code = build_standalone_loader(code)
        return jsonify({
            "ok": True,
            "standalone_code": standalone_code,
            "original_size": len(code),
            "final_size": len(standalone_code)
        })
    except Exception as e:
        return jsonify({"ok": False, "error": "Loi: " + str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)