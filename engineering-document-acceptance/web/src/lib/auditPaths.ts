/** 对齐 case 内相对路径：去掉 files/ 前缀、统一斜杠 */
export function normalizeCaseFilePath(raw?: string | null): string {
  if (!raw) return ''
  let s = String(raw).replace(/\\/g, '/')
  while (s.startsWith('files/')) s = s.slice('files/'.length)
  return s.replace(/^\/+/, '')
}

export function pathsEqual(a?: string | null, b?: string | null): boolean {
  return normalizeCaseFilePath(a) === normalizeCaseFilePath(b)
}
