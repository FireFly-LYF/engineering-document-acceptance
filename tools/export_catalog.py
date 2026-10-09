"""Generate the human-readable catalog from YAML, without duplicate configuration."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.registry import Registry, ROOT


def export():
    reg = Registry()
    lines = ['# 工程竣工核查 tag 与 label 完整字典', '',
        '本文件由 `tools/export_catalog.py` 从配置生成。维护 YAML 后重新生成，不在本文件修改字段定义。', '',
        '## 资料类型 tag', '', '| code | 中文名称 | 阶段 |', '|---|---|---|']
    for code, definition in reg.tags.items():
        lines.append(f"| {code} | {definition['name']} | {definition['stage']} |")
    lines += ['', '## 可维护 label', '', '| semantic key | 中文名称 | 类型 | 比较策略 | 比较范围 |', '|---|---|---|---|---|']
    for code, d in reg.labels.items():
        lines.append(f"| {code} | {d['label']} | {d['type']} | {d['comparator']} | {d['comparison_scope']} |")
    lines += ['', '## 每类资料的完整字段绑定', '',
        '绑定表示有则提取，不是法定必填字段。UNKNOWN 的基础字段用于归属调查，不可直接判清单通过。', '',
        '| tag | label semantic keys |', '|---|---|']
    for tag in reg.tags:
        lines.append(f"| {tag} | {', '.join(reg.labels_for_tag(tag))} |")
    target = ROOT / 'docs/tag-label完整字典.md'
    target.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Exported {len(reg.tags)} tags and {len(reg.labels)} labels')


if __name__ == '__main__':
    export()
