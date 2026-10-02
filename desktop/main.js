// Electron 主进程:启动本地 FastAPI 后端,并打开原生窗口加载前端。
// 环境完全隔离:后端由 PyInstaller 打包为独立可执行文件,数据写入用户目录。
const { app, BrowserWindow, Menu, shell, dialog } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const net = require('net')
const http = require('http')
const fs = require('fs')

// —— 后端可执行文件路径 ——
// 打包后:app 的 Resources/backend/chronicle-backend/chronicle-backend(见 package.json 的 extraResources)
// 开发时:desktop/build/chronicle-backend/chronicle-backend(先跑 build-app.sh 生成)
function backendBinaryPath() {
  if (process.env.CHRONICLE_BACKEND_BIN) return process.env.CHRONICLE_BACKEND_BIN
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend', 'chronicle-backend', 'chronicle-backend')
  }
  return path.join(__dirname, 'build', 'chronicle-backend', 'chronicle-backend')
}

// 找一个空闲端口
function findFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer()
    srv.once('error', reject)
    srv.listen(0, '127.0.0.1', () => {
      const { port } = srv.address()
      srv.close(() => resolve(port))
    })
  })
}

// 轮询后端就绪(请求一个轻量 API)
function waitForReady(port, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(
        { host: '127.0.0.1', port, path: '/api/v1/persons', timeout: 800 },
        (res) => {
          res.resume()
          resolve()
        },
      )
      req.once('error', () => {
        if (Date.now() > deadline) reject(new Error('后端启动超时'))
        else setTimeout(tick, 200)
      })
    }
    tick()
  })
}

let backend = null

function startBackend(port) {
  const bin = backendBinaryPath()
  if (!fs.existsSync(bin)) {
    throw new Error(`后端程序不存在:${bin}`)
  }
  backend = spawn(bin, [], {
    env: {
      ...process.env,
      CHRONICLE_PORT: String(port),
      // 数据(SQLite)写到用户目录,升级/覆盖 app 也不丢数据
      CHRONICLE_DATA_DIR: app.getPath('userData'),
    },
    stdio: 'ignore',
  })
  backend.once('exit', () => {
    backend = null
  })
}

function createWindow(port) {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    title: '人物志',
    backgroundColor: '#0d1117',
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  })
  win.once('ready-to-show', () => win.show())
  // 外部链接交给系统浏览器,不在应用内新开窗口
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
  win.loadURL(`http://127.0.0.1:${port}/`)
  return win
}

app.whenReady().then(async () => {
  Menu.setApplicationMenu(null) // 去掉默认 Electron 菜单
  try {
    const port = await findFreePort()
    startBackend(port)
    await waitForReady(port)
    createWindow(port)
  } catch (err) {
    dialog.showErrorBox('启动失败', String(err && err.message ? err.message : err))
    app.quit()
  }
})

app.on('window-all-closed', () => {
  app.quit()
})

app.on('will-quit', () => {
  if (backend && !backend.killed) {
    backend.kill()
  }
})
