import { useEffect, useRef, useState } from 'react'
import type { InferenceResult } from '../types'

// Must match val_tf in train.py
const RESIZE = 288
const CROP   = 256
const MEAN   = [0.485, 0.456, 0.406]
const STD    = [0.229, 0.224, 0.225]

const CONFIDENCE_THRESHOLD = 0.10

// ── Image preprocessing ───────────────────────────────────────────────────────

function drawResized(
  img: HTMLImageElement,
  targetW: number,
  targetH: number,
): HTMLCanvasElement {
  const c = document.createElement('canvas')
  c.width  = targetW
  c.height = targetH
  c.getContext('2d')!.drawImage(img, 0, 0, targetW, targetH)
  return c
}

function preprocessImage(img: HTMLImageElement): Float32Array {
  const { naturalWidth: w, naturalHeight: h } = img

  // 1. Resize shortest side to RESIZE (288)
  let rW: number, rH: number
  if (w <= h) {
    rW = RESIZE
    rH = Math.round((h / w) * RESIZE)
  } else {
    rH = RESIZE
    rW = Math.round((w / h) * RESIZE)
  }
  const resized = drawResized(img, rW, rH)

  // 2. Center crop to CROP × CROP (256)
  const cx = Math.floor((rW - CROP) / 2)
  const cy = Math.floor((rH - CROP) / 2)
  const cropped = document.createElement('canvas')
  cropped.width  = CROP
  cropped.height = CROP
  cropped.getContext('2d')!.drawImage(resized, cx, cy, CROP, CROP, 0, 0, CROP, CROP)

  // 3. Extract RGBA and convert to NCHW float32 with ImageNet normalisation
  const { data } = cropped.getContext('2d')!.getImageData(0, 0, CROP, CROP)
  const tensor = new Float32Array(3 * CROP * CROP)
  for (let y = 0; y < CROP; y++) {
    for (let x = 0; x < CROP; x++) {
      const pi = (y * CROP + x) * 4
      const ti =  y * CROP + x
      for (let c = 0; c < 3; c++) {
        tensor[c * CROP * CROP + ti] = (data[pi + c] / 255 - MEAN[c]) / STD[c]
      }
    }
  }
  return tensor
}

function softmax(logits: Float32Array): Float32Array {
  const max = logits.reduce((a, b) => Math.max(a, b), -Infinity)
  const exps = new Float32Array(logits.length)
  let sum = 0
  for (let i = 0; i < logits.length; i++) {
    exps[i] = Math.exp(logits[i] - max)
    sum += exps[i]
  }
  for (let i = 0; i < exps.length; i++) exps[i] /= sum
  return exps
}

function argmax(arr: Float32Array): number {
  let best = 0
  for (let i = 1; i < arr.length; i++) {
    if (arr[i] > arr[best]) best = i
  }
  return best
}

function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => { URL.revokeObjectURL(url); resolve(img) }
    img.onerror = reject
    img.src = url
  })
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export interface UseInferenceReturn {
  modelReady: boolean
  modelError: string | null
  inferring: boolean
  identify: (file: File) => Promise<InferenceResult | null>
  CONFIDENCE_THRESHOLD: number
}

export function useInference(): UseInferenceReturn {
  const [modelReady, setModelReady] = useState(false)
  const [modelError, setModelError] = useState<string | null>(null)
  const [inferring, setInferring]   = useState(false)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const sessionRef = useRef<any>(null)

  useEffect(() => {
    let cancelled = false

    async function loadModel() {
      try {
        // Dynamic import keeps ort out of the initial bundle
        const ort = await import('onnxruntime-web')
        // CDN must match the pinned version in package.json.
        // Using a CDN URL avoids Vite intercepting the dynamic .jsep.mjs import
        // that ort-web 1.24.x performs for its WASM backend.
        ort.env.wasm.wasmPaths =
          'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.24.3/dist/'
        ort.env.wasm.numThreads = 1

        const modelUrl = `${import.meta.env.BASE_URL}model.onnx`
        const session  = await ort.InferenceSession.create(modelUrl, {
          executionProviders: ['wasm'],
        })
        if (!cancelled) {
          sessionRef.current = session
          setModelReady(true)
        }
      } catch (err) {
        if (!cancelled) {
          setModelError(
            `Could not load model: ${String(err)}.\n` +
            `Run scripts/export_onnx.py to generate web/public/model.onnx`
          )
        }
      }
    }

    loadModel()
    return () => { cancelled = true }
  }, [])

  async function identify(file: File): Promise<InferenceResult | null> {
    if (!sessionRef.current) return null
    setInferring(true)
    try {
      const ort  = await import('onnxruntime-web')
      const img  = await loadImage(file)
      const data = preprocessImage(img)

      const tensor = new ort.Tensor('float32', data, [1, 3, CROP, CROP])
      const feeds  = { input: tensor }
      const output = await sessionRef.current.run(feeds)

      // Output name may be 'logits' or the first key
      const logitKey = 'logits' in output ? 'logits' : Object.keys(output)[0]
      const logits   = output[logitKey].data as Float32Array
      const probs    = softmax(logits)
      const idx      = argmax(probs)

      // Debug: log top-5 predictions to console
      const top5 = Array.from(probs)
        .map((p, i) => ({ i, p }))
        .sort((a, b) => b.p - a.p)
        .slice(0, 5)
      console.log('[cardex] top-5 predictions:', top5.map(({ i, p }) => `idx=${i} (${(p * 100).toFixed(2)}%)`).join(', '))

      return { idx, confidence: probs[idx] }
    } finally {
      setInferring(false)
    }
  }

  return { modelReady, modelError, inferring, identify, CONFIDENCE_THRESHOLD }
}
