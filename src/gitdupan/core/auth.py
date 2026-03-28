import os
import json
import time
import requests
import webbrowser
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
from rich.console import Console

console = Console()

# 我们将全局配置存储在用户的 home 目录下
GLOBAL_CONFIG_DIR = os.path.expanduser("~/.gitdupan")
AUTH_FILE = os.path.join(GLOBAL_CONFIG_DIR, "auth.json")

# 默认的 Serverless 授权服务地址 (Cloudflare Worker)
# 用户可以直接使用而无需自己申请 AppKey
DEFAULT_WORKER_URL = "https://gitdupan-auth.str1ct.top" # TODO: 替换为实际部署后的 URL

def get_auth_file_path():
    if not os.path.exists(GLOBAL_CONFIG_DIR):
        os.makedirs(GLOBAL_CONFIG_DIR)
    return AUTH_FILE

def load_auth():
    auth_file = get_auth_file_path()
    if os.path.exists(auth_file):
        with open(auth_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_auth(data):
    auth_file = get_auth_file_path()
    with open(auth_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """用于接收本地 OAuth 回调的简易 HTTP 服务器"""
    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/callback':
            query_components = parse_qs(parsed_path.query)
            if 'access_token' in query_components:
                self.server.auth_data = {
                    "access_token": query_components['access_token'][0],
                    "refresh_token": query_components.get('refresh_token', [''])[0],
                    "expires_in": int(query_components.get('expires_in', ['2592000'])[0])
                }
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                
                # 返回给浏览器一个美观的成功页面
                html = """
                <html>
                <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                    <h1 style="color: #4CAF50;">授权成功！</h1>
                    <p>GitDuPan 已经成功获取登录凭证。</p>
                    <p>您可以关闭此网页并返回命令行继续操作了。</p>
                    <script>
                        // 尝试自动关闭窗口
                        setTimeout(function() { window.close(); }, 3000);
                    </script>
                </body>
                </html>
                """
                self.wfile.write(html.encode('utf-8'))
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write("<html><body><h1 style='color: red;'>授权失败</h1><p>未找到 access_token。</p></body></html>")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # 禁用默认的 HTTP 日志输出，保持终端整洁
        pass

def login_via_worker():
    """通过 Serverless 服务进行授权（开箱即用，免 AppKey）"""
    # 启动一个本地随机端口的 HTTP 服务器接收回调
    server = HTTPServer(('127.0.0.1', 0), OAuthCallbackHandler)
    port = server.server_port
    server.auth_data = None
    
    auth_url = f"{DEFAULT_WORKER_URL}/login?port={port}"
    console.print("[cyan]正在浏览器中打开授权页面...[/cyan]")
    console.print(f"如果浏览器没有自动打开，请手动访问：\n[underline]{auth_url}[/underline]\n")
    
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass
        
    # 等待接收回调请求
    console.print("[yellow]等待授权回调... (请在浏览器中完成登录并授权)[/yellow]")
    while server.auth_data is None:
        server.handle_request()
        
    auth_data = server.auth_data
    auth_data["expires_at"] = time.time() + auth_data.get("expires_in", 2592000)
    auth_data["is_serverless"] = True # 标记为 serverless 模式
    
    save_auth(auth_data)
    console.print("[green]登录成功！认证信息已保存在本地。[/green]")

def login_via_oob(client_id: str, client_secret: str):
    """传统的 OOB 授权模式（适合高级用户自定义 AppKey）"""
    redirect_uri = "oob"
    auth_url = (
        f"https://openapi.baidu.com/oauth/2.0/authorize"
        f"?response_type=code&client_id={client_id}"
        f"&redirect_uri={redirect_uri}&scope=basic,netdisk"
    )
    
    console.print("[bold cyan]请在浏览器中打开以下链接进行授权:[/bold cyan]")
    console.print(auth_url)
    
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass
        
    code = console.input("[bold yellow]请输入授权码 (Authorization code): [/bold yellow]").strip()
    
    if not code:
        console.print("[red]授权码不能为空。[/red]")
        return
        
    token_url = "https://openapi.baidu.com/oauth/2.0/token"
    params = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri
    }
    
    response = requests.get(token_url, params=params)
    data = response.json()
    
    if "access_token" in data:
        data["expires_at"] = time.time() + data.get("expires_in", 2592000)
        data["client_id"] = client_id
        data["client_secret"] = client_secret
        data["is_serverless"] = False
        
        save_auth(data)
        console.print("[green]登录成功！认证信息已保存在本地。[/green]")
    else:
        console.print(f"[red]获取 Token 失败: {data.get('error_description', data)}[/red]")

def login(app_key: str = None, secret_key: str = None):
    """登录入口：根据是否提供自定义 key 决定使用哪种授权模式"""
    if app_key and secret_key:
        console.print("[cyan]检测到自定义 AppKey，使用独立 OOB 授权模式。[/cyan]")
        login_via_oob(app_key, secret_key)
    else:
        console.print("[cyan]使用 GitDuPan 官方开箱即用授权模式。[/cyan]")
        login_via_worker()

def get_access_token():
    """
    获取有效的 access token。如果已过期则自动刷新。
    """
    auth_data = load_auth()
    if not auth_data or "access_token" not in auth_data:
        raise Exception("未登录。请先运行 `gitdupan login`。")
        
    if time.time() > auth_data.get("expires_at", 0) - 300: # 5分钟缓冲时间
        return refresh_token()
        
    return auth_data["access_token"]

def refresh_token():
    """
    使用 refresh_token 刷新 access token。
    """
    auth_data = load_auth()
    if not auth_data or "refresh_token" not in auth_data:
        raise Exception("没有可用的 refresh token，请重新登录。")
        
    is_serverless = auth_data.get("is_serverless", False)
    
    if is_serverless:
        # 通过 Serverless Worker 刷新，保护 Secret
        refresh_url = f"{DEFAULT_WORKER_URL}/refresh"
        params = {"refresh_token": auth_data["refresh_token"]}
        response = requests.get(refresh_url, params=params)
        data = response.json()
    else:
        # 传统模式刷新，需要本地存放有 client_secret
        token_url = "https://openapi.baidu.com/oauth/2.0/token"
        params = {
            "grant_type": "refresh_token",
            "refresh_token": auth_data["refresh_token"],
            "client_id": auth_data.get("client_id", ""),
            "client_secret": auth_data.get("client_secret", ""),
        }
        response = requests.get(token_url, params=params)
        data = response.json()
    
    if "access_token" in data:
        auth_data.update(data)
        auth_data["expires_at"] = time.time() + data.get("expires_in", 2592000)
        save_auth(auth_data)
        return auth_data["access_token"]
    else:
        raise Exception(f"刷新 Token 失败: {data.get('error_description', data)}")
