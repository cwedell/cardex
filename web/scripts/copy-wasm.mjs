// Copies onnxruntime-web WASM files from node_modules into public/ so that
// the served binaries always match the installed JS package version.
import { copyFileSync, existsSync, mkdirSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dir  = dirname(fileURLToPath(import.meta.url))
const srcDir = join(__dir, '../node_modules/onnxruntime-web/dist')
const dstDir = join(__dir, '../public')

mkdirSync(dstDir, { recursive: true })

const files = [
  'ort-wasm-simd-threaded.wasm',
  'ort-wasm-simd-threaded.mjs',
]

for (const file of files) {
  const src = join(srcDir, file)
  if (existsSync(src)) {
    copyFileSync(src, join(dstDir, file))
    console.log(`  copied ${file}`)
  } else {
    console.warn(`  WARNING: ${file} not found in onnxruntime-web/dist`)
  }
}
