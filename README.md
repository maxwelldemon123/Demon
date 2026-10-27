# dsh-demon

Demon 伴生引擎的 monorepo：酒馆插件 + Demon 本体 + DSH 本地服务。

非商业许可，需署名。见 `LICENSE` 与 `THIRD-PARTY-NOTICES.txt`。

## 结构

```
apps/demon        Demon（Qt 6 / C++）
apps/st-plugin    smartdemon（SillyTavern 扩展）
services/dsh-demon  DSH 本地服务（Node / Fastify）
contracts/v1      三方共用的 JSON Schema 与版本
docs/plan         技术方案与计划书
tools             构建 / 发布脚本
third_party       第三方组件（各自许可）
```

## 端口

| 服务 | 端口 |
| --- | --- |
| Demon | 8790 |
| dsh-demon | 8791 |
| SillyTavern | 8000 |
| VTube Studio | 8001 |

## 构建

```powershell
# Demon
.\tools\build-demon.ps1

# dsh-demon
cd services\dsh-demon
npm install
npm start
```

## 版本

- 契约版本：`contracts/version.json`
- 发布物：`Demon-2.0.0.zip`、`smartdemon-2.1.0.zip`、`dsh-demon-0.1.0.zip`
