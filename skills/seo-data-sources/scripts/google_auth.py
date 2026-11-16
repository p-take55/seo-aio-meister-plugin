"""Google のサービスアカウントで API を呼ぶための共通部品。

環境変数 GOOGLE_SERVICE_ACCOUNT_JSON（鍵の JSON そのまま、または base64）を使う。
依存は Python 標準ライブラリと openssl コマンドだけ。
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ENV_NAME = "GOOGLE_SERVICE_ACCOUNT_JSON"


def fail(message, code=1):
    print(f"{os.path.basename(sys.argv[0])}: {message}", file=sys.stderr)
    sys.exit(code)


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def load_credentials():
    raw = os.environ.get(ENV_NAME, "").strip()
    if not raw:
        fail(f"{ENV_NAME} が設定されていません")
    if not raw.startswith("{"):
        try:
            raw = base64.b64decode(raw).decode()
        except Exception:
            fail(f"{ENV_NAME} は JSON でも base64 でもありません")
    try:
        creds = json.loads(raw)
    except json.JSONDecodeError:
        fail(f"{ENV_NAME} を JSON として読めません")
    for key in ("client_email", "private_key"):
        if key not in creds:
            fail(f"サービスアカウントの鍵に {key} がありません")
    return creds


def post_json(url, body, headers):
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        fail(f"HTTP {error.code} {url}\n{error.read().decode(errors='replace')[:800]}")
    except urllib.error.URLError as error:
        fail(f"接続できません {url}: {error.reason}")


def access_token(scope):
    """サービスアカウントの鍵で署名し、指定した範囲のアクセストークンを得る。"""
    creds = load_credentials()
    token_uri = creds.get("token_uri", "https://oauth2.googleapis.com/token")
    now = int(time.time())
    header = b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claims = b64url(json.dumps({
        "iss": creds["client_email"],
        "scope": scope,
        "aud": token_uri,
        "iat": now,
        "exp": now + 600,
    }).encode())
    signing_input = f"{header}.{claims}".encode()
    with tempfile.NamedTemporaryFile("w", suffix=".pem") as key_file:
        os.chmod(key_file.name, 0o600)
        key_file.write(creds["private_key"])
        key_file.flush()
        try:
            signed = subprocess.run(
                ["openssl", "dgst", "-sha256", "-sign", key_file.name],
                input=signing_input, capture_output=True,
            )
        except FileNotFoundError:
            print("openssl が見つかりません。openssl を入れてから、もう一度実行してください。", file=sys.stderr)
            sys.exit(1)
    if signed.returncode != 0:
        fail(f"鍵で署名できません: {signed.stderr.decode(errors='replace')[:300]}")
    assertion = f"{header}.{claims}.{b64url(signed.stdout)}"
    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }).encode()
    result = post_json(token_uri, body, {"Content-Type": "application/x-www-form-urlencoded"})
    return result["access_token"]


def api_post(url, token, body):
    return post_json(url, json.dumps(body).encode(), {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
