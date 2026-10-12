工程归档公开参考资料（分类索引）

本目录存放规则模板层用的公开目录/规范 PDF，不是真实竣工档案包。
PDF 默认不纳入 Git；请用下方脚本拉取。

目录分类
--------
archive-catalogs/     跨类型归档目录与国标（道路/桥梁/管线/建筑共用）
road-bridge/          道路与桥梁侧重参考
municipal-pipeline/   市政/地下管线侧重参考
public-pdfs/          既有空白样表与房屋类参考（施工许可、合同、验收表等）

拉取
----
  python tools/fetch_public_pdfs.py          # 原有样表与江门/深圳目录
  python tools/fetch_archive_catalogs.py    # 本轮分类归档目录（韶关/国标/公路/管线）

规则文件如何使用这些参考
------------------------
  rules/housing-construction.json   ← public-pdfs + archive-catalogs（建筑部分）
  rules/road-bridge.json            ← archive-catalogs + road-bridge/
  rules/municipal-pipeline.json     ← archive-catalogs + municipal-pipeline/

各子目录的 SOURCES.txt 有具体 URL 与用途说明。
实际项目以当地主管部门目录为准；本仓库清单为可配置演示模板。
