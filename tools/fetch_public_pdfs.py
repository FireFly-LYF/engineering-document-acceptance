# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "reference" / "public-pdfs"
BASE.mkdir(parents=True, exist_ok=True)

DOWNLOADS = [
    (
        "sz-archive-guide-2025.pdf",
        "https://zjj.sz.gov.cn/attachment/1/1628/1628043/12250554.pdf",
    ),
    (
        "jm-archive-unified-catalog.pdf",
        "http://www.jiangmen.gov.cn/attachment/0/341/341760/3304209.pdf",
    ),
    (
        "gb50300-2013-acceptance-standard.pdf",
        "https://www.sldchina-sc.cn/ueditor/php/upload/file/20190328/1553764819654771.pdf",
    ),
    (
        "acceptance-check-forms-unified.pdf",
        "https://www.hzcinda.com/upload/at/file/20220510/1652145437126743mwm8.pdf",
    ),
    (
        "construction-permit-application-sd.pdf",
        "https://jnszjj.jining.gov.cn/module/download/downfile.jsp?classid=0&filename=4f8f58018a71433abe9e7c21865a0a6f.pdf",
    ),
    (
        "construction-permit-sample-sd.pdf",
        "http://app.shandong.gov.cn/attach/2015/24/38-1.pdf",
    ),
    (
        "construction-contract-gf2017.pdf",
        "https://www.ahsz.gov.cn/group1/M00/3A/F2/Cpc8VmV5eV6AXmFVACavp3R8Q-o444.pdf",
    ),
    (
        "unit-completion-acceptance-report.pdf",
        "https://download.s21i.faiusr.com/31941469/0/0/ABUIABA9GAAghuPuqwYoztvz2gE.pdf?f=%E5%8D%95%E4%BD%8D%E7%AB%A3%E5%B7%A5%E9%AA%8C%E6%94%B6%E6%8A%A5%E5%91%8A.pdf&v=1702605190",
    ),
    (
        "zj-unified-forms-2025.pdf",
        "https://zjjcmspublic.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/jcms_files/jcms1/web3162/site/attach/0/21c6d07177ec4c5990c03604c4e0a5f1.pdf",
    ),
]

SOURCES = """公开 PDF 来源索引（规则/空白样表类，非真实竣工档案包）

已下载到本目录：

1. sz-archive-guide-2025.pdf
   名称：深圳市建设工程文件归档与档案验收移交指南（2025版）
   URL：https://zjj.sz.gov.cn/attachment/1/1628/1628043/12250554.pdf
   用途：归档范围、责任单位、验收/移交规则（规则模板层）

2. jm-archive-unified-catalog.pdf
   名称：江门市建设工程竣工验收技术资料和工程档案验收归档统一目录
   URL：http://www.jiangmen.gov.cn/attachment/0/341/341760/3304209.pdf
   用途：房屋/市政/管线归档目录清单（规则模板层）

3. gb50300-2013-acceptance-standard.pdf
   名称：建筑工程施工质量验收统一标准（含检验批等附录表）
   URL：https://www.sldchina-sc.cn/ueditor/php/upload/file/20190328/1553764819654771.pdf
   用途：检验批/分项/分部/单位工程验收记录表样
   注意：第三方站点转载，正式引用以国家标准文本为准

4. acceptance-check-forms-unified.pdf
   名称：建筑工程施工质量验收检查用表统一标准（含空白表）
   URL：https://www.hzcinda.com/upload/at/file/20220510/1652145437126743mwm8.pdf
   用途：检验批等检查用表版式参考
   注意：企业站点转载，非政府官网原文

5. construction-permit-sample-sd.pdf / construction-permit-application-sd.pdf
   名称：山东省建筑工程施工许可证样表 / 申请表
   URL：http://app.shandong.gov.cn/attach/2015/24/38-1.pdf
        https://jnszjj.jining.gov.cn/module/download/downfile.jsp?classid=0&filename=4f8f58018a71433abe9e7c21865a0a6f.pdf
   用途：施工许可证密表栏目（合成 make_construction_permit）

6. construction-contract-gf2017.pdf
   名称：建设工程施工合同（示范文本）GF-2017-0201
   URL：https://www.ahsz.gov.cn/group1/M00/3A/F2/Cpc8VmV5eV6AXmFVACavp3R8Q-o444.pdf
   用途：合同封面 + 协议书首页（合成 make_construction_contract）

7. unit-completion-acceptance-report.pdf
   名称：单位竣工验收报告（GD-E1 类空白/样表）
   URL：见 DOWNLOADS 列表
   用途：竣工验收封面 + 工程概况（合成 make_completion_pack）

8. zj-unified-forms-2025.pdf
   名称：浙江省建筑工程统一用表相关材料
   URL：见 DOWNLOADS 列表
   用途：统一用表目录与表头结构参考

网上有入口但多为 DOC/XLS、或需办事系统登录：

- 济南竣工验收备案办事指南空白样表（多为 docx）
- 广东政务服务网 / 东莞住建：竣工验收报告空表多为 docx/xls
- 连云港政务服务：竣工验收报告空白表格/示例样表在办事指南内
- 雅安住建：建筑/道路/桥梁/地下管线归档规范为 xls 附件
  https://zfhcxjsj.yaan.gov.cn/xinwen/show/fd6cebf4-bad0-4afe-b000-7ac6ae6228bc.html
- 深圳指南 2026 修订版通知页附件：
  https://zjj.sz.gov.cn/xxgk/tzgg/content/post_12960759.html

不建议直接抓取作为演示项目包：完整真实工程竣工档案扫描包。

造数：按文种异构 builder（tools/pdf_forms.py）+ 合成项目信息生成 cases/ 下演示 PDF（非真实档案）。
"""


def fetch(url: str, out: Path) -> None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "application/pdf,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        out.write_bytes(resp.read())


def main() -> None:
    for name, url in DOWNLOADS:
        out = BASE / name
        if out.exists() and out.stat().st_size > 1000:
            print(f"SKIP exists {name} ({out.stat().st_size})")
            continue
        print(f"GET {url}")
        try:
            fetch(url, out)
            head = out.read_bytes()[:5]
            print(f"OK {out.stat().st_size} magic={head!r} -> {name}")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {name}: {exc}")

    dup = BASE / "sz-archive-guide-2025-alt.pdf"
    if dup.exists():
        dup.unlink()

    # Try Shenzhen 2026 attachment links from notice page
    page = "https://zjj.sz.gov.cn/xxgk/tzgg/content/post_12960759.html"
    try:
        html = urllib.request.urlopen(page, timeout=60).read().decode("utf-8", "ignore")
        links = sorted(set(re.findall(r"(?:https?://[^\"'\\s>]+\.pdf|/[^\"'\\s>]+\.pdf)", html, flags=re.I)))
        print("SZ2026 candidate links:")
        for link in links:
            print(" ", link)
            if link.startswith("/"):
                link = "https://zjj.sz.gov.cn" + link
            if "2026" in link or "修订" in html:
                out = BASE / "sz-archive-guide-2026.pdf"
                if not out.exists():
                    try:
                        urllib.request.urlretrieve(link, out)
                        if out.read_bytes()[:4] == b"%PDF":
                            print("OK downloaded", out.name, out.stat().st_size)
                        else:
                            print("NOT PDF, remove", out.name)
                            out.unlink(missing_ok=True)
                    except Exception as exc:  # noqa: BLE001
                        print("download fail", link, exc)
    except Exception as exc:  # noqa: BLE001
        print("SZ page fail", exc)

    (BASE / "SOURCES.txt").write_text(SOURCES, encoding="utf-8")
    print("files in", BASE)
    for p in sorted(BASE.iterdir()):
        print(f"  {p.name}\t{p.stat().st_size}")


if __name__ == "__main__":
    main()
