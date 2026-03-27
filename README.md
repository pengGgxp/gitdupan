# GitDuPan

GitDuPan 是一个基于 **百度网盘开放平台 (Baidu PCS API)** 开发的类 Git 数据管理与备份工具。

它结合了 Git 优秀的版本控制理念（如暂存区、提交快照、哈希去重等）和百度网盘的海量云端存储能力。通过引入创新的“增量打包 (Pack) 机制”，它完美解决了云盘 API 对大量小文件碎片上传的性能限制，让你能够像使用 Git 一样轻松管理和备份你的个人数据。

---

## ✨ 核心特性

- **类 Git 体验**：支持 `init`, `add`, `commit`, `status`, `log`, `checkout` 等熟悉的命令。
- **本地秒级快照**：采用基于 SHA-256 的 Blob 对象存储机制，本地提交和状态比对极其迅速。
- **增量打包同步**：在 `push` 时，自动计算本地与远端的版本差异，将变动的数据打包为一个压缩包 (`.tar.gz`) 进行单文件上传，突破网盘 API 频控瓶颈。
- **OAuth 2.0 鉴权**：内置百度网盘官方授权流程，Token 本地安全持久化及自动刷新。
- **单文件便携**：支持通过 PyInstaller 打包为独立的 `.exe` 可执行文件，无需安装 Python 环境即可使用。

---

## 🚀 安装指南

### 方法一：直接下载可执行文件 (推荐 Windows 用户)

如果你不想配置 Python 环境，可以直接在 `dist` 目录中找到已经打包好的 `gitdupan.exe`。
你可以将其复制到任何地方，并建议将其所在目录添加到系统的环境变量 `PATH` 中。

### 方法二：基于源码和 `uv` 运行

如果你是开发者或希望在 Linux/macOS 上运行：

1. 确保你已安装 [uv](https://github.com/astral-sh/uv) 和 Python 3.12+。
2. 克隆或下载本项目源码。
3. 在项目根目录下执行安装：
   ```bash
   uv pip install -e .
   ```
4. 现在你可以直接在终端中使用 `gitdupan` 命令了。

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
# 1. 登录并授权
# 你需要提供在百度网盘开放平台申请的 App Key 和 Secret Key
gitdupan login --app-key YOUR_APP_KEY --secret-key YOUR_SECRET_KEY

# 2. 绑定远程网盘目录
# 这会在你的网盘中创建一个对应的工作区 (如 /apps/gitdupan/my_backup)
gitdupan remote add /apps/gitdupan/my_backup

# 3. 将本地数据推送到网盘
# 系统会自动计算增量并打包上传
gitdupan push

# 4. 在其他设备上拉取网盘数据
gitdupan pull
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

---

## ⚠️ 注意事项与免责声明

1. **API 限制**：由于百度网盘 API 的限制，极其频繁的 API 调用可能导致账号被临时封禁，这也是本作设计“增量打包”机制的初衷。请勿短时间内疯狂执行 `push/pull`。
2. **测试阶段**：本软件目前处于早期原型阶段，请**务必妥善保管好你的重要数据**，避免由于误操作或未知 Bug 导致数据丢失。建议先使用非关键数据进行体验。
3. **App Key**：为了安全起见，程序不内置开发者 Key。用户需自行前往[百度开发者平台](https://pan.baidu.com/union)申请应用并获取。

---

## 📄 开源协议

本项目采用 MIT License。
