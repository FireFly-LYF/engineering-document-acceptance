# 竣工资料核查台（前端）

本地 Web 工作台：按**用户 → 工程批次**管理上传材料，支持 ZIP / PDF / 本地文件夹，核查后对照 `_work/findings` 形态为文件与目录打标。

> 当前为**大框架**：核查为前端启发式演示，尚未调用 `audit_prepare.py`。数据存在浏览器 `localStorage`。

## 启动

```bash
cd web
npm install
npm run dev
```

浏览器打开终端提示的本地地址（默认 `http://localhost:5173`）。

## 结构

```text
src/
├── App.tsx                 # 用户 / 项目壳层
├── types.ts                # 项目、文件、标注类型
├── store.ts                # localStorage 持久化
├── lib/files.ts            # ZIP / PDF / 文件夹摄入
├── lib/auditMock.ts        # 演示核查 + findings 打标
└── components/             # 上传、目录树、结果面板
```

## 后续对接（未做）

- 后端接收上传 → 写入 `cases/<id>/files/`
- 调用 `audit_prepare.py` 生成真实 `_work/`
- 前端拉取 findings 替换 `runMockAudit`
