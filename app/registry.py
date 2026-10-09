"""Versioned tag/label/rule catalog compiled from the given Markdown reference."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _unique_yaml(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f'配置含重复键：{key}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


class UniqueLoader(yaml.SafeLoader):
    pass


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_yaml)


def read_yaml(path):
    return yaml.load(Path(path).read_text(encoding='utf-8-sig'), Loader=UniqueLoader)


class Registry:
    def __init__(self, reference=None):
        self.reference = Path(reference or ROOT / 'reference/housing-audit-reference.md').resolve()
        markdown = self.reference.read_text(encoding='utf-8-sig')
        front = re.match(r'^---\s*\n(.*?)\n---\s*\n', markdown, re.S)
        if not front:
            raise ValueError('参考 Markdown 缺少 YAML frontmatter')
        self.meta = yaml.load(front.group(1), Loader=UniqueLoader)
        configs = {}
        for key in ('tags_config', 'labels_config', 'bindings_config', 'rules_config'):
            path = (self.reference.parent / self.meta[key]).resolve()
            if not path.is_relative_to(ROOT):
                raise ValueError('配置必须位于工程竣工项目内')
            configs[key] = read_yaml(path)
        self.tags = configs['tags_config']['tags']
        self.labels = configs['labels_config']['fields']
        self.bindings = configs['bindings_config']
        self.rules = configs['rules_config']
        self.validate()
        self.snapshot = {'reference': markdown, 'configurations': configs}
        self.sha256 = hashlib.sha256(json.dumps(self.snapshot, ensure_ascii=False,
            sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.bundle_id = 'registry_' + self.sha256[:24]

    def validate(self):
        if 'UNKNOWN' not in self.tags:
            raise ValueError('必须定义 UNKNOWN tag')
        for code, definition in self.labels.items():
            if definition['comparator'] not in ('normalized_exact','decimal_exact','date_exact','none'):
                raise ValueError(f'未知比较策略：{code}')
        for tag, labels in self.bindings['bindings'].items():
            if tag not in self.tags:
                raise ValueError(f'绑定未知 tag：{tag}')
            for label in [*self.bindings['defaults'], *labels]:
                if label not in self.labels:
                    raise ValueError(f'绑定未知 label：{label}')
        if set(self.tags) != set(self.bindings['bindings']):
            raise ValueError('每个 tag 必须具有显式 label 绑定')
        seen = set()
        for rule in self.rules['rules']:
            code = rule['rule_id']
            if code in seen:
                raise ValueError(f'重复规则编号：{code}')
            seen.add(code)
            for tag in [*rule.get('accepted_tags', []), *rule.get('excluded_tags', [])]:
                if tag not in self.tags:
                    raise ValueError(f'规则 {code} 引用未知 tag：{tag}')
            for label in rule.get('labels', []):
                if label not in self.labels:
                    raise ValueError(f'规则 {code} 引用未知 label：{label}')

    def labels_for_tag(self, tag):
        if tag not in self.tags:
            raise ValueError(f'未知 tag：{tag}')
        # UNKNOWN has no authoritative business role. Identity fields only for investigation.
        codes = [*self.bindings['defaults'], *self.bindings['bindings'][tag]]
        return list(dict.fromkeys(codes))

    def install(self, connection):
        """Insert an immutable catalog snapshot with FK-checked bindings in one transaction."""
        with connection:
            connection.execute('INSERT OR IGNORE INTO registry_bundle(id,version,sha256,reference_markdown,snapshot_json) VALUES(?,?,?,?,?)',
                (self.bundle_id, self.meta['version'], self.sha256,
                 self.snapshot['reference'], json.dumps(self.snapshot, ensure_ascii=False)))
            for code, d in self.tags.items():
                connection.execute('INSERT OR IGNORE INTO tag_definition VALUES(?,?,?,?,?)',
                    (self.bundle_id, code, d['name'], d['stage'], json.dumps(d, ensure_ascii=False)))
            for code, d in self.labels.items():
                connection.execute('INSERT OR IGNORE INTO label_definition VALUES(?,?,?,?,?,?)',
                    (self.bundle_id, code, d['label'], d['type'], d['comparison_scope'], json.dumps(d, ensure_ascii=False)))
            for tag in self.tags:
                for label in self.labels_for_tag(tag):
                    connection.execute('INSERT OR IGNORE INTO tag_label_binding VALUES(?,?,?,1)', (self.bundle_id, tag, label))
            for d in self.rules['rules']:
                connection.execute('INSERT OR IGNORE INTO rule_definition VALUES(?,?,?,?,?)',
                    (self.bundle_id, d['rule_id'], d['kind'], d['name'], json.dumps(d, ensure_ascii=False)))


def applicability(conditions, context):
    """No unknown-as-false fallback: known mismatch is inapplicable; missing is unknown."""
    unknown = False
    for key, expected in conditions.items():
        if key not in context or context[key] is None or context[key] == 'unknown':
            unknown = True
        elif context[key] != expected:
            return 'not_applicable'
    return 'unknown' if unknown else 'applicable'
