const fs = require('fs');
const path = require('path');
const { buildDocxFromMarkdown, validateStatement } = require('../.agh/skills/engineering-doc-generator/scripts/generate.js');
async function main() {
  const args = process.argv.slice(2);
  const option = (name) => args[args.indexOf(name) + 1];
  for (const name of ['--body','--facts','--out']) {
    if (!args.includes(name)) throw new Error('缺少参数 ' + name);
  }
  const md = fs.readFileSync(option('--body'),'utf8');
  const facts = JSON.parse(fs.readFileSync(option('--facts'),'utf8'));
  validateStatement(md,facts);
  const output = path.resolve(option('--out'));
  fs.mkdirSync(path.dirname(output),{recursive:true});
  await buildDocxFromMarkdown(md,output);
  console.log(output);
}
main().catch((e) => {console.error(e.message); process.exit(1);});
