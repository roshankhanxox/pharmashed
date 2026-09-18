// Generates web/src/types/contracts.ts from contracts/schemas/*.schema.json (M01).
// Run via `pnpm run gen:types` (wired into `make fixtures`).
import { compile } from 'json-schema-to-typescript'
import { readFileSync, writeFileSync, readdirSync, mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SCHEMAS_DIR = join(__dirname, '..', '..', 'contracts', 'schemas')
const OUT_FILE = join(__dirname, '..', 'src', 'types', 'contracts.ts')

const HEADER = `/**
 * Generated from contracts/schemas/*.schema.json by scripts/gen-types.mjs.
 * Do not edit by hand -- run \`pnpm run gen:types\`.
 */

`

async function main() {
  const files = readdirSync(SCHEMAS_DIR)
    .filter((f) => f.endsWith('.schema.json'))
    .sort()

  const parts = []
  for (const file of files) {
    const schema = JSON.parse(readFileSync(join(SCHEMAS_DIR, file), 'utf-8'))
    const ts = await compile(schema, schema.title ?? file, {
      cwd: SCHEMAS_DIR,
      bannerComment: '',
      additionalProperties: false,
    })
    parts.push(`// ---- ${file} ----\n${ts}`)
  }

  mkdirSync(dirname(OUT_FILE), { recursive: true })
  writeFileSync(OUT_FILE, HEADER + parts.join('\n'))
  console.log(`wrote ${OUT_FILE}`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
