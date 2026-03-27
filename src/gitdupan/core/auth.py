import os
import json
import time
import requests
import webbrowser
from rich.console import Console

console = Console()

# We will store global config in user's home directory
GLOBAL_CONFIG_DIR = os.path.expanduser("~/.gitdupan")
AUTH_FILE = os.path.join(GLOBAL_CONFIG_DIR, "auth.json")

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

def login(client_id: str, client_secret: str):
    """
    Perform OAuth 2.0 login with Baidu Netdisk API.
    Uses 'oob' (out-of-band) flow for desktop applications.
    """
    redirect_uri = "oob"
    auth_url = (
        f"https://openapi.baidu.com/oauth/2.0/authorize"
        f"?response_type=code&client_id={client_id}"
        f"&redirect_uri={redirect_uri}&scope=basic,netdisk"
    )
    
    console.print("[bold cyan]Please open the following URL in your browser to authorize:[/bold cyan]")
    console.print(auth_url)
    
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass
        
    code = console.input("[bold yellow]Enter the authorization code: [/bold yellow]").strip()
    
    if not code:
        console.print("[red]Authorization code is required.[/red]")
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
        # Add timestamp to know when it expires
        data["expires_at"] = time.time() + data.get("expires_in", 2592000)
        data["client_id"] = client_id
        data["client_secret"] = client_secret
        
        save_auth(data)
        console.print("[green]Login successful! Token saved globally.[/green]")
    else:
        console.print(f"[red]Failed to get token: {data.get('error_description', data)}[/red]")

def get_access_token():
    """
    Get the valid access token. Refresh if expired.
    """
    auth_data = load_auth()
    if not auth_data or "access_token" not in auth_data:
        raise Exception("Not logged in. Please run `gitdupan login` first.")
        
    if time.time() > auth_data.get("expires_at", 0) - 300: # 5 minutes buffer
        return refresh_token()
        
    return auth_data["access_token"]

def refresh_token():
    """
    Refresh the access token using the refresh_token.
    """
    auth_data = load_auth()
    if not auth_data or "refresh_token" not in auth_data:
        raise Exception("No refresh token available. Please login again.")
        
    token_url = "https://openapi.baidu.com/oauth/2.0/token"
    params = {
        "grant_type": "refresh_token",
        "refresh_token": auth_data["refresh_token"],
        "client_id": auth_data["client_id"],
        "client_secret": auth_data["client_secret"],
    }
    
    response = requests.get(token_url, params=params)
    data = response.json()
    
    if "access_token" in data:
        auth_data.update(data)
        auth_data["expires_at"] = time.time() + data.get("expires_in", 2592000)
        save_auth(auth_data)
        return auth_data["access_token"]
    else:
        raise Exception(f"Failed to refresh token: {data.get('error_description', data)}")
