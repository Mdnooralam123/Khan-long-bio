from flask import Flask, request, jsonify, make_response
import requests
import binascii
import jwt
import time
import urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

try:
    import my_pb2
    import output_pb2
except ImportError:
    pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════
#   CONSTANTS
# ══════════════════════════════════════════════════════════════
FREEFIRE_UPDATE_URL = "https://client.ind.freefiremobile.com/UpdateSocialBasicInfo"
MAJOR_LOGIN_URL = "https://loginbp.ppmainecoonghj.com/MajorLogin"
OAUTH_URL = "https://100067.connect.garena.com/oauth/guest/token/grant"
FREEFIRE_VERSION = "OB55"

# ✨ Access Token se JWT generate karne wali API (response me nahi dikhega)
JWT_GEN_API = "https://ff-jwt-gen-api.lovable.app/api/public/token"

KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

BIO_HEADERS = {
    "Expect": "100-continue",
    "X-Unity-Version": "2018.4.11f1",
    "X-GA": "v1 1",
    "ReleaseVersion": FREEFIRE_VERSION,
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
}

LOGIN_HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
    "Content-Type": "application/octet-stream",
    "Expect": "100-continue",
    "X-Unity-Version": "2018.4.11f1",
    "X-GA": "v1 1",
    "ReleaseVersion": FREEFIRE_VERSION
}

# ══════════════════════════════════════════════════════════════
#   PROTOBUF SETUP
# ══════════════════════════════════════════════════════════════
_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\ndata.proto\"\xbb\x01\n\x04\x44\x61ta\x12\x0f\n\x07\x66ield_2\x18\x02 \x01(\x05\x12\x1e\n\x07\x66ield_5\x18\x05 \x01(\x0b\x32\r.EmptyMessage\x12\x1e\n\x07\x66ield_6\x18\x06 \x01(\x0b\x32\r.EmptyMessage\x12\x0f\n\x07\x66ield_8\x18\x08 \x01(\t\x12\x0f\n\x07\x66ield_9\x18\t \x01(\x05\x12\x1f\n\x08\x66ield_11\x18\x0b \x01(\x0b\x32\r.EmptyMessage\x12\x1f\n\x08\x66ield_12\x18\x0c \x01(\x0b\x32\r.EmptyMessage\"\x0e\n\x0c\x45mptyMessageb\x06proto3'
)
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'data1_pb2', _globals)
BioData = _sym_db.GetSymbol('Data')
EmptyMessage = _sym_db.GetSymbol('EmptyMessage')


# ══════════════════════════════════════════════════════════════
#   HELPER FUNCTIONS (सारे पुराने वैसे ही)
# ══════════════════════════════════════════════════════════════

def encrypt_data(data_bytes):
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    padded = pad(data_bytes, AES.block_size)
    return cipher.encrypt(padded)


def get_name_region_from_reward(access_token):
    """Reward API se UID/Name/Region (पुराना वाला)"""
    try:
        uid_url = "https://prod-api.reward.ff.garena.com/redemption/api/auth/inspect_token/"
        uid_headers = {
            "authority": "prod-api.reward.ff.garena.com",
            "method": "GET",
            "path": "/redemption/api/auth/inspect_token/",
            "scheme": "https",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "access-token": access_token,
            "origin": "https://reward.ff.garena.com",
            "referer": "https://reward.ff.garena.com/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        uid_res = requests.get(uid_url, headers=uid_headers, verify=False, timeout=10)
        uid_data = uid_res.json()
        return uid_data.get("uid"), uid_data.get("name"), uid_data.get("region")
    except Exception:
        return None, None, None


def get_openid_from_shop2game(uid):
    """Shop2Game se OpenID (पुराना वाला)"""
    if not uid:
        return None
    try:
        openid_url = "https://shop2game.com/api/auth/player_id_login"
        openid_headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ar-MA,ar;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Origin": "https://shop2game.com",
            "Referer": "https://shop2game.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"'
        }
        payload = {"app_id": 100067, "login_id": str(uid)}
        res = requests.post(openid_url, headers=openid_headers, json=payload, verify=False, timeout=10)
        data = res.json()
        return data.get("open_id")
    except Exception:
        return None


def decode_jwt_info(token):
    """JWT se UID/Name/Region (पुराना वाला)"""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        name = decoded.get("nickname")
        region = decoded.get("lock_region")
        uid = decoded.get("account_id")
        return str(uid), name, region
    except:
        return None, None, None


def perform_major_login(access_token, open_id):
    """MajorLogin se JWT (पुराना वाला - UID/Pass फ्लो में इस्तेमाल होता है)"""
    platforms = [8, 3, 4, 6]
    for platform_type in platforms:
        try:
            game_data = my_pb2.GameData()
            game_data.timestamp = "2024-12-05 18:15:32"
            game_data.game_name = "free fire"
            game_data.game_version = 1
            game_data.version_code = "1.108.3"
            game_data.os_info = "Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)"
            game_data.device_type = "Handheld"
            game_data.network_provider = "Verizon Wireless"
            game_data.connection_type = "WIFI"
            game_data.screen_width = 1280
            game_data.screen_height = 960
            game_data.dpi = "240"
            game_data.cpu_info = "ARMv7 VFPv3 NEON VMH | 2400 | 4"
            game_data.total_ram = 5951
            game_data.gpu_name = "Adreno (TM) 640"
            game_data.gpu_version = "OpenGL ES 3.0"
            game_data.user_id = "Google|74b585a9-0268-4ad3-8f36-ef41d2e53610"
            game_data.ip_address = "172.190.111.97"
            game_data.language = "en"
            game_data.open_id = open_id
            game_data.access_token = access_token
            game_data.platform_type = platform_type
            game_data.field_99 = str(platform_type)
            game_data.field_100 = str(platform_type)

            serialized_data = game_data.SerializeToString()
            encrypted = encrypt_data(serialized_data)
            hex_encrypted = binascii.hexlify(encrypted).decode('utf-8')
            edata = bytes.fromhex(hex_encrypted)

            response = requests.post(MAJOR_LOGIN_URL, data=edata, headers=LOGIN_HEADERS, verify=False, timeout=10)

            if response.status_code == 200:
                try:
                    example_msg = output_pb2.Garena_420()
                    example_msg.ParseFromString(response.content)
                    if example_msg.token:
                        return example_msg.token
                except Exception:
                    pass
        except Exception:
            continue
    return None


def perform_guest_login(uid, password):
    """Guest Login (पुराना वाला)"""
    payload = {
        'uid': uid,
        'password': password,
        'response_type': "token",
        'client_type': "2",
        'client_secret': "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        'client_id': "100067"
    }
    headers = {
        'User-Agent': "GarenaMSDK/4.0.19P9(SM-M526B ;Android 13;pt;BR;)",
        'Connection': "Keep-Alive"
    }
    try:
        resp = requests.post(OAUTH_URL, data=payload, headers=headers, timeout=10, verify=False)
        data = resp.json()
        if 'access_token' in data:
            return data['access_token'], data.get('open_id')
    except Exception:
        pass
    return None, None


# ══════════════════════════════════════════════════════════════
#   ✨ NAYA: Access Token → JWT (API source hidden)
# ══════════════════════════════════════════════════════════════
def get_jwt_from_access_token(access_token):
    """
    Nayi API se JWT token generate karta hai.
    Returns: (jwt_token, error_message)
    """
    try:
        resp = requests.get(
            JWT_GEN_API,
            params={"access_token": access_token},
            headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"
            },
            timeout=15,
            verify=False
        )

        if resp.status_code != 200:
            return None, f"JWT API error: HTTP {resp.status_code}"

        # Try JSON first
        try:
            data = resp.json()
            jwt_token = None

            if isinstance(data, dict):
                jwt_token = (
                    data.get("token") or
                    data.get("jwt") or
                    data.get("jwt_token") or
                    data.get("access_token")
                )
                if not jwt_token and isinstance(data.get("data"), dict):
                    jwt_token = data["data"].get("token") or data["data"].get("jwt")
                if not jwt_token and isinstance(data.get("data"), str):
                    jwt_token = data["data"]
            elif isinstance(data, str):
                jwt_token = data

            if not jwt_token:
                return None, "JWT token response me nahi mila"

            jwt_token = jwt_token.replace("Bearer ", "").strip()
            return jwt_token, None

        except ValueError:
            # Non-JSON response (maybe direct text)
            text = resp.text.strip()
            if text.startswith("eyJ"):
                return text, None
            return None, f"Non-JSON response from JWT API"

    except Exception as e:
        return None, f"JWT API Exception: {str(e)}"


def upload_bio_request(jwt_token, bio_text):
    """JWT se bio change (पुराना वाला)"""
    try:
        data = BioData()
        data.field_2 = 17
        data.field_5.CopyFrom(EmptyMessage())
        data.field_6.CopyFrom(EmptyMessage())
        data.field_8 = bio_text
        data.field_9 = 1
        data.field_11.CopyFrom(EmptyMessage())
        data.field_12.CopyFrom(EmptyMessage())

        data_bytes = data.SerializeToString()
        encrypted = encrypt_data(data_bytes)

        headers = BIO_HEADERS.copy()
        headers["Authorization"] = f"Bearer {jwt_token}"

        resp = requests.post(FREEFIRE_UPDATE_URL, headers=headers, data=encrypted, timeout=20, verify=False)

        status_text = "Unknown"
        if resp.status_code == 200:
            status_text = "✅ Success"
        elif resp.status_code == 401:
            status_text = "❌ Unauthorized (Invalid JWT)"
        else:
            status_text = f"⚠️ Status {resp.status_code}"

        raw_hex = binascii.hexlify(resp.content).decode('utf-8')

        return {
            "status": status_text,
            "code": resp.status_code,
            "bio": bio_text,
            "server_response": raw_hex
        }
    except Exception as e:
        return {"status": f"Error: {str(e)}", "code": 500, "bio": bio_text, "server_response": "N/A"}


# ══════════════════════════════════════════════════════════════
#   MAIN ROUTE
# ══════════════════════════════════════════════════════════════
@app.route("/bio_upload", methods=["GET", "POST"])
def combined_bio_upload():
    # ✨ Overall timer start
    request_start = time.time()

    bio = request.args.get("bio") or request.form.get("bio")
    jwt_token = request.args.get("jwt") or request.form.get("jwt")
    uid = request.args.get("uid") or request.form.get("uid")
    password = request.args.get("pass") or request.form.get("pass")
    access_token = (
        request.args.get("access") or request.form.get("access") or
        request.args.get("access_token") or request.form.get("access_token")
    )

    if not bio:
        return jsonify({
            "Credit": "KHAN",
            "Join For More": "Telegram: @KHAN",
            "status": "❌ Error",
            "code": 400,
            "error": "Missing 'bio' parameter",
            "⏱️ Total Time": f"{round(time.time() - request_start, 3)} sec"
        }), 400

    final_jwt = None
    login_method = "Direct JWT"
    final_open_id = None
    final_access_token = None
    final_uid = None
    final_name = None
    final_region = None

    # ✨ Step timers
    jwt_time = 0.0
    bio_time = 0.0

    # ─────────────────────────────────────────────
    # 1️⃣ DIRECT JWT
    # ─────────────────────────────────────────────
    if jwt_token:
        step_start = time.time()
        final_jwt = jwt_token
        j_uid, j_name, j_region = decode_jwt_info(jwt_token)
        final_uid = j_uid
        final_name = j_name
        final_region = j_region
        jwt_time = round(time.time() - step_start, 3)

    # ─────────────────────────────────────────────
    # 2️⃣ UID / PASSWORD (पुराना वाला - वैसा ही)
    # ─────────────────────────────────────────────
    elif uid and password:
        login_method = "UID/Pass Login"
        step_start = time.time()

        acc_token, login_openid = perform_guest_login(uid, password)

        if acc_token and login_openid:
            final_access_token = acc_token
            final_open_id = login_openid

            final_jwt = perform_major_login(final_access_token, final_open_id)

            if final_jwt:
                j_uid, j_name, j_region = decode_jwt_info(final_jwt)
                final_uid = j_uid
                final_name = j_name
                final_region = j_region
            else:
                return jsonify({
                    "Credit": "KHAN",
                    "Join For More": "Telegram: @KHAN",
                    "status": "❌ JWT Generation Failed",
                    "login_method": login_method,
                    "code": 500,
                    "⏱️ Total Time": f"{round(time.time() - request_start, 3)} sec"
                }), 500
        else:
            return jsonify({
                "Credit": "KHAN",
                "Join For More": "Telegram: @KHAN",
                "status": "❌ Guest Login Failed (Check UID/Pass)",
                "login_method": login_method,
                "code": 401,
                "⏱️ Total Time": f"{round(time.time() - request_start, 3)} sec"
            }), 401

        jwt_time = round(time.time() - step_start, 3)

    # ─────────────────────────────────────────────
    # 3️⃣ ACCESS TOKEN → JWT (नई API)
    # ─────────────────────────────────────────────
    elif access_token:
        login_method = "Access Token"
        final_access_token = access_token
        step_start = time.time()

        # ✨ Nayi API se JWT
        final_jwt, jwt_err = get_jwt_from_access_token(access_token)

        if not final_jwt:
            return jsonify({
                "Credit": "KHAN",
                "Join For More": "Telegram: @KHAN",
                "status": "❌ JWT Generation Failed",
                "login_method": login_method,
                "code": 401,
                "error": jwt_err,
                "⏱️ Total Time": f"{round(time.time() - request_start, 3)} sec"
            }), 401

        # JWT se UID/Name/Region
        f_uid, f_name, f_region = decode_jwt_info(final_jwt)
        final_uid = f_uid
        final_name = f_name
        final_region = f_region

        jwt_time = round(time.time() - step_start, 3)

    else:
        return jsonify({
            "Credit": "KHAN",
            "Join For More": "Telegram: @KHAN",
            "status": "❌ Error",
            "code": 400,
            "error": "Provide JWT, or UID/Pass, or Access Token",
            "⏱️ Total Time": f"{round(time.time() - request_start, 3)} sec"
        }), 400

    # ─────────────────────────────────────────────
    # BIO UPLOAD
    # ─────────────────────────────────────────────
    if not final_jwt:
        return jsonify({
            "Credit": "KHAN",
            "Join For More": "Telegram: @KHAN",
            "status": "❌ JWT Generation Failed",
            "code": 500,
            "⏱️ Total Time": f"{round(time.time() - request_start, 3)} sec"
        }), 500

    step_start = time.time()
    result = upload_bio_request(final_jwt, bio)
    bio_time = round(time.time() - step_start, 3)

    # ✨ Final total time
    total_time = round(time.time() - request_start, 3)

    # ═══════════════════════════════════════════════════
    #   💎 BADA + SUNDAR RESPONSE (API source hidden + Time)
    # ═══════════════════════════════════════════════════
    response_data = {
        "🎯 Credit": "KHAN",
        "📢 Join For More": "Telegram: @KHAN",
        "━━━━━━━━━━━━━━━━━━━━": "━━━━━━━━━━━━━━━━━━━━",
        "✅ STATUS": result["status"],
        "🔢 Response Code": result["code"],

        "━━━━━ ⏱️ TIMING ━━━━━": "━━━━━━━━━━━━━━━━━━━━",
        "⏳ Total Time": f"{total_time} sec",
        "🔐 JWT Time": f"{jwt_time} sec",
        "📤 Bio Upload Time": f"{bio_time} sec",

        "━━━━━ 📋 BIO INFO ━━━━━": "━━━━━━━━━━━━━━━━━━━━",
        "📝 Bio Uploaded": result["bio"],
        "🔤 Bio Length": len(bio),

        "━━━━━ 👤 USER INFO ━━━━━": "━━━━━━━━━━━━━━━━━━━━",
        "🆔 UID": str(final_uid) if final_uid else "N/A",
        "🏷️ Name": final_name or "N/A",
        "🌍 Region": final_region or "N/A",
        "🔓 Open ID": final_open_id or "N/A",

        "━━━━━ 🔐 TOKEN INFO ━━━━━": "━━━━━━━━━━━━━━━━━━━━",
        "🔑 Login Method": login_method,
        "🎟️ Access Token": (final_access_token[:30] + "..." + final_access_token[-10:]) if final_access_token else "N/A",
        "🪙 Generated JWT (truncated)": (final_jwt[:60] + "..." + final_jwt[-20:]) if final_jwt else "N/A",

        "━━━━━ 📡 SERVER ━━━━━": "━━━━━━━━━━━━━━━━━━━━",
        "📨 Server Response (hex)": result["server_response"],

        "━━━━━ ℹ️ EXTRA ━━━━━": "━━━━━━━━━━━━━━━━━━━━",
        "⚙️ Free Fire Version": FREEFIRE_VERSION,
    }

    response = make_response(jsonify(response_data))
    response.headers["Content-Type"] = "application/json"
    return response


# ══════════════════════════════════════════════════════════════
#   RUN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
