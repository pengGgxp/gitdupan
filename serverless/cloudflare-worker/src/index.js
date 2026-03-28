/**
 * GitDuPan 授权服务端 (Cloudflare Worker)
 * 用于隐藏 Baidu OAuth 2.0 的 Client Secret，实现开箱即用的登录体验。
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 从 Cloudflare 环境变量中获取配置 (在部署时配置)
    const CLIENT_ID = env.BAIDU_APP_KEY;
    const CLIENT_SECRET = env.BAIDU_SECRET_KEY;

    if (!CLIENT_ID || !CLIENT_SECRET) {
      return new Response("Server configuration error: missing AppKey or Secret", { status: 500 });
    }

    // CORS Headers 允许跨域请求 (比如后续如果有 Web 端需求)
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    // 1. 发起登录授权重定向
    if (url.pathname === "/login") {
      // 客户端传过来的本地 HTTP 端口号，用于接收回调
      const port = url.searchParams.get("port");
      if (!port) {
        return new Response("Missing 'port' parameter from client", { status: 400 });
      }

      // 百度回调到本 Worker 的 /callback
      const redirectUri = `${url.origin}/callback`;
      
      // 使用 state 参数传递本地端口号，这样回调时能知道回传到哪里
      const state = port;
      
      // 构造百度的授权链接
      const baiduAuthUrl = `https://openapi.baidu.com/oauth/2.0/authorize?response_type=code&client_id=${CLIENT_ID}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=basic,netdisk&state=${state}`;
      
      return Response.redirect(baiduAuthUrl, 302);
    }

    // 2. 接收百度回调并用 Code 换取 Token
    if (url.pathname === "/callback") {
      const code = url.searchParams.get("code");
      const state = url.searchParams.get("state"); // 这里是客户端的本地端口号
      const redirectUri = `${url.origin}/callback`;

      if (!code || !state) {
        return new Response("Invalid callback: missing code or state", { status: 400 });
      }

      // 用 code 换取 token，此时可以在后端安全地使用 CLIENT_SECRET
      const tokenUrl = `https://openapi.baidu.com/oauth/2.0/token?grant_type=authorization_code&code=${code}&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&redirect_uri=${encodeURIComponent(redirectUri)}`;

      try {
        const tokenResp = await fetch(tokenUrl);
        const tokenData = await tokenResp.json();

        if (tokenData.access_token) {
          // 成功获取 Token，重定向回本地客户端
          // 为了防止有些浏览器屏蔽 http 到 http 的跳转，或者 http://127.0.0.1 更好用
          const localUrl = `http://127.0.0.1:${state}/callback?access_token=${tokenData.access_token}&refresh_token=${tokenData.refresh_token}&expires_in=${tokenData.expires_in}`;
          return Response.redirect(localUrl, 302);
        } else {
          return new Response("Failed to get token from Baidu: " + JSON.stringify(tokenData), { status: 400 });
        }
      } catch (err) {
        return new Response("Error fetching token: " + err.message, { status: 500 });
      }
    }

    // 3. 刷新 Token 的接口
    if (url.pathname === "/refresh") {
      const refreshToken = url.searchParams.get("refresh_token");
      if (!refreshToken) {
        return new Response(JSON.stringify({ error: "Missing refresh_token" }), { 
          status: 400,
          headers: { "Content-Type": "application/json", ...corsHeaders }
        });
      }

      const tokenUrl = `https://openapi.baidu.com/oauth/2.0/token?grant_type=refresh_token&refresh_token=${refreshToken}&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}`;
      
      try {
        const tokenResp = await fetch(tokenUrl);
        const tokenData = await tokenResp.json();
        return new Response(JSON.stringify(tokenData), {
          headers: { "Content-Type": "application/json", ...corsHeaders }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: "Error refreshing token", details: err.message }), { 
          status: 500,
          headers: { "Content-Type": "application/json", ...corsHeaders }
        });
      }
    }

    return new Response("GitDuPan Serverless Auth API is running.", { 
      status: 200,
      headers: corsHeaders
    });
  },
};
