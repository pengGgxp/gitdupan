# GitDuPan

GitDuPan 是一个基于 **百度网盘开放平台 (Baidu PCS API)** 开发的类 Git 数据管理与备份工具。

它结合了 Git 优秀的版本控制理念（如暂存区、提交快照、哈希去重等）和百度网盘的海量云端存储能力。通过引入创新的“增量打包 (Pack) 机制”，它完美解决了云盘 API 对大量小文件碎片上传的性能限制，让你能够像使用 Git 一样轻松管理和备份你的个人数据。

---

## ✨ 核心特性

- **类 Git 体验**：支持 `init`, `add`, `commit`, `status`, `log`, `checkout` 等熟悉的命令。
- **本地秒级快照**：采用基于 SHA-256 的 Blob 对象存储机制，本地提交和状态比对极其迅速。
- **增量打包同步**：在 `push` 时，自动计算本地与远端的版本差异，将变动的数据打包为一个压缩包 (`.tar.gz`) 进行单文件上传，突破网盘 API 频控瓶颈。
- **无感 OAuth 2.0 鉴权**：通过 Serverless 架构实现开箱即用的登录体验，Token 本地安全持久化及自动刷新。
- **单文件便携**：支持通过 PyInstaller 打包为独立的 `.exe` 可执行文件，无需安装 Python 环境即可使用。

---

## 🚀 安装指南

### 方法一：使用 uv 全局安装 (推荐 🌟)

如果你是一名开发者，并且已经安装了超快的 Python 包管理器 [uv](https://github.com/astral-sh/uv)，这是最优雅且占用体积最小的方式。它会自动为你创建隔离环境并将命令暴露到全局。

```bash
uv tool install git+https://github.com/pengGgxp/gitdupan.git
```

安装完成后，你可以在任何目录直接使用 `gitdupan`（或简写 `gitdp`, `gid`）命令。

### 方法二：直接下载独立可执行文件 (小白友好)

如果你不想配置任何 Python 环境，可以直接在 GitHub 的 **Releases** 页面下载对应系统和架构的压缩包：

**Windows**
- `gitdupan-windows-amd64.zip` (64位系统)
- `gitdupan-windows-386.zip` (32位系统)

**macOS**
- `gitdupan-macos-arm64.tar.gz` (Apple Silicon M1/M2/M3)
*(注：由于 GitHub Actions 弃用了旧版 macOS-13 Intel 运行器，目前 macOS 仅提供 Apple Silicon 版本。Intel Mac 用户建议使用 `uv` 方式安装)*

**Linux**
- `gitdupan-linux-amd64.tar.gz` (x86_64)
- `gitdupan-linux-arm64.tar.gz` (ARM64 架构)

解压后，你会得到 `gitdupan.exe`（以及 `gitdp.exe`, `gid.exe`）。你可以将其复制到任何地方，并建议将其所在目录添加到系统的环境变量 `PATH` 中。


### 方法三：基于源码运行

1. 确保你已安装 [uv](https://github.com/astral-sh/uv) 和 Python 3.12+。
2. 克隆本项目源码：
   ```bash
   git clone https://github.com/pengGgxp/gitdupan.git
   cd gitdupan
   ```
3. 在项目根目录下执行安装：
   ```bash
   uv pip install -e .
   ```

---

## 📖 快速入门

### 1. 本地版本控制

像使用 Git 一样在本地管理你的文件：

```bash
# 初始化仓库 (会在当前目录创建 .gitdupan 隐藏文件夹)
gitdupan init

# 创建一个测试文件
echo "Hello GitDuPan" > data.txt

# 查看工作区状态
gitdupan status

# 添加文件到暂存区
gitdupan add data.txt

# 提交更改
gitdupan commit -m "First commit: add data.txt"

# 查看提交历史
gitdupan log

# 回退到指定的 commit (复制 log 中的 commit hash)
gitdupan checkout <commit_hash>
```

### 2. 连接百度网盘与同步

要将数据备份到百度网盘，你需要先进行授权并绑定远程目录：

```bash
# 1. 登录并授权 (浏览器自动弹出，开箱即用)
gitdupan login

# 2. 绑定远程网盘目录
# 这会在你的网盘中创建一个对应的工作区 (如 /apps/gitdupan/my_backup)
gitdupan remote add /apps/gitdupan/my_backup

# 3. 将本地数据推送到网盘
# 系统会自动计算增量并打包上传
gitdupan push

# 4. 在其他设备上拉取网盘数据
gitdupan pull
```

#### 高级玩法：使用自定义 AppKey

如果你遇到官方授权服务限流，或者想使用自己的开发者账号，GitDuPan 依然保留了传统的 OOB 授权模式：

```bash
gitdupan login --app-key YOUR_APP_KEY --secret-key YOUR_SECRET_KEY
```

---

## 🛠️ 开发者指南

### 目录结构说明

- `src/gitdupan/cli.py`: Click 命令行程序入口。
- `src/gitdupan/core/repo.py`: 本地版本控制核心逻辑（Index、Object Store、Commit 等）。
- `src/gitdupan/core/auth.py`: 百度网盘 OAuth 2.0 鉴权与 Token 管理。
- `src/gitdupan/core/pack.py`: 针对网盘优化的增量打包与解包引擎。
- `src/gitdupan/core/sync.py`: 远程同步交互逻辑（Push, Pull）。
- `src/gitdupan/core/remote.py`: 封装的 Baidu PCS API 请求客户端。

### 运行测试

本项目使用 `pytest` 进行单元和集成测试。确保已安装开发依赖：

```bash
uv run pytest
```

### 重新打包为 EXE

如果你修改了源码并希望重新生成 `.exe` 文件：

```bash
uv run pyinstaller --name gitdupan --onefile --console src/gitdupan/cli.py
```
生成的程序将位于 `dist/gitdupan.exe`。

### 独立部署授权服务 (Serverless)

为了实现客户端的开箱即用，本项目在 `serverless/cloudflare-worker` 目录下提供了一个 Cloudflare Worker 脚本。
开发者可以将其部署到自己的 Cloudflare 账号，隐藏真实的 `Client Secret`：

1. 进入 `serverless/cloudflare-worker` 目录
2. 使用 `wrangler login` 登录
3. 配置环境变量：`wrangler secret put BAIDU_APP_KEY` 和 `BAIDU_SECRET_KEY`
4. 部署：`wrangler deploy`
5. **重要**：前往百度网盘开放平台，将部署后的 Worker 地址 (例如 `https://gitdupan-auth.your-username.workers.dev/callback`) 填入应用的**授权回调地址**中。
6. 修改 `src/gitdupan/core/auth.py` 中的 `DEFAULT_WORKER_URL` 为你的部署地址。

---

## ⚠️ 注意事项与免责声明

1. **API 限制**：由于百度网盘 API 的限制，极其频繁的 API 调用可能导致账号被临时封禁，这也是本作设计“增量打包”机制的初衷。请勿短时间内疯狂执行 `push/pull`。
2. **测试阶段**：本软件目前处于早期原型阶段，请**务必妥善保管好你的重要数据**，避免由于误操作或未知 Bug 导致数据丢失。建议先使用非关键数据进行体验。

---

## 📄 开源协议

本项目采用 MIT License。
