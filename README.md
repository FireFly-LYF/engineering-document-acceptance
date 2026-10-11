# Agnes-Harness Monorepo

工程资料核查演示（EDA）与 Agnes Harness（AGH）的本地一体仓库。

## 目录与依赖关系

```text
Agnes-Harness/                          ← 本仓库根
├── agnes-harness/                      ← AGH 源码（pnpm workspace）
│   └── packages/cli/dist/local/        ← build:local 产物（gitignore，不入库）
└── engineering-document-acceptance/    ← EDA 前端 + API + Skills
```

- EDA **依赖** 同级目录 `agnes-harness`：默认 CLI 路径为  
  `../agnes-harness/packages/cli/dist/local/agnes.mjs`
- 一键启动：`engineering-document-acceptance/start-dev.ps1`（需上述 CLI 已构建）
- 上游参考（合并前各自独立仓库）：
  - AGH: https://github.com/AgnesAI-Labs/agnes-harness.git @ `cde816b8`
  - EDA: https://github.com/FireFly-LYF/engineering-document-acceptance.git @ `8077a26`

## 新机器安装

要求：Node.js ≥ 24.10、pnpm 10（可用 corepack）、Python 3（核查脚本）。

```powershell
# 在仓库根执行
.\setup.ps1
```

或分步：

```powershell
# 1) AGH
cd agnes-harness
pnpm install --frozen-lockfile
pnpm --filter @agnes/cli build:local

# 2) EDA
cd ..\engineering-document-acceptance\server
npm ci
cd ..\web
npm ci
cd ..\.agh\skills\engineering-doc-generator
npm ci
```

Windows 上 AGH 原生依赖失败时，先跑 `agnes-harness\.github\scripts\prepare-windows-native.ps1`，再 `build:local`。

## 启动核查台

```powershell
cd engineering-document-acceptance
.\start-dev.ps1
```

浏览器打开终端提示的地址（一般是 `http://127.0.0.1:5173`）。
