# 工程文件核验（前端）

本地 Web 工作台：按**用户 → 工程批次**管理上传材料。上传经 API 落盘到 `cases/<id>/files/`；核查按钮整段交给本机 AGH Agent，并可跳转 AGH 网页查看过程。

## 启动（三端）

```bash
# 1) API（8787）
cd ../server && npm install && npm run dev

# 2) 前端（5173，/api 代理到 8787）
cd ../web && npm install && npm run dev

# 3) AGH Web（4177）
cd ../../agnes-harness
# 需已 build:local
node .\packages\cli\dist\local\agnes.mjs serve
```

浏览器打开 `http://localhost:5173`。

## 结构

```text
src/
├── App.tsx                 # 用户 / 项目壳层；对接 API + AGH
├── types.ts
├── store.ts                # UI 状态 localStorage；文件本体在磁盘
├── lib/api.ts              # 落盘 / 核查 API
├── lib/files.ts            # 路径工具
├── lib/auditMock.ts        # annotateFromFindings（读真实 findings）
└── components/
```
