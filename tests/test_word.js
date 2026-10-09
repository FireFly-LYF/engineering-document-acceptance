const assert = require('node:assert/strict');
const { parseMarkdownToBlocks,validateStatement } = require('../.agh/skills/engineering-doc-generator/scripts/generate.js');
const blocks = parseMarkdownToBlocks('# 标题\n\n1. 第一项\n2. 第二项\n\n**加粗**正文\n\n| 单独管道文本');
assert.equal(blocks[1].type,'ol');
assert.equal(blocks[1].items.length,2);
assert.equal(blocks.at(-1).type,'p');
assert.throws(() => validateStatement('共接收文件99份',{file_count:2}),/统计/);
console.log('Word parsing and fact guards passed');
