import { useCallback, useContext, useRef, useState } from 'react'
import { Camera, Upload, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react'
import { useInference } from '../hooks/useInference'
import { RarityBadge } from '../components/RarityBadge'
import { addSpot, hasSpotted } from '../lib/storage'
import { RARITY_BG, RARITY_POINTS } from '../lib/rarity'
import { CarDataContext } from '../context/CarDataContext'
import type { SpottedCar, RarityTier } from '../types'

type Phase = 'idle' | 'preview' | 'inferring' | 'result' | 'unrecognized'

function generateThumbnail(file: File): Promise<string> {
  return new Promise(resolve => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      const MAX = 300
      const scale = Math.min(MAX / img.width, MAX / img.height, 1)
      const c = document.createElement('canvas')
      c.width  = Math.round(img.width  * scale)
      c.height = Math.round(img.height * scale)
      c.getContext('2d')!.drawImage(img, 0, 0, c.width, c.height)
      URL.revokeObjectURL(url)
      resolve(c.toDataURL('image/jpeg', 0.82))
    }
    img.src = url
  })
}

function UnrecognizedModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-zinc-900 border border-zinc-700 rounded-2xl max-w-sm w-full p-6 text-center animate-slide-up">
        <AlertCircle className="mx-auto mb-3 text-amber-400" size={40} />
        <h2 className="text-xl font-bold mb-2">Great Spot!</h2>
        <p className="text-zinc-400 text-sm leading-relaxed mb-5">
          We don't recognise this car! Your photo helps us improve — click below
          to flag it for our team and we'll investigate.
        </p>
        <button
          onClick={onClose}
          className="w-full py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-semibold transition-colors"
        >
          Add to Training Data
        </button>
        <button
          onClick={onClose}
          className="mt-2 w-full py-2 text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          Dismiss
        </button>
      </div>
    </div>
  )
}

interface ResultCardProps {
  label: string
  rarity: RarityTier
  confidence: number
  isFirstSpot: boolean
  photoDataUrl: string
  onSpotAnother: () => void
}

function ResultCard({ label, rarity, confidence, isFirstSpot, photoDataUrl, onSpotAnother }: ResultCardProps) {
  return (
    <div className={`rounded-2xl border p-5 animate-slide-up ${RARITY_BG[rarity]}`}>
      {isFirstSpot && (
        <div className="flex items-center gap-2 text-amber-400 text-sm font-semibold mb-3">
          <CheckCircle2 size={16} />
          First spot! Added to your collection.
        </div>
      )}
      {!isFirstSpot && (
        <div className="flex items-center gap-2 text-zinc-400 text-sm mb-3">
          <CheckCircle2 size={16} className="text-emerald-400" />
          Spotted again — logged to history.
        </div>
      )}

      <div className="flex gap-4">
        <img
          src={photoDataUrl}
          alt={label}
          className="w-24 h-24 rounded-xl object-cover flex-shrink-0"
        />
        <div className="flex flex-col justify-center min-w-0">
          <RarityBadge tier={rarity} size="sm" />
          <h2 className="text-lg font-bold mt-1 leading-snug">{label}</h2>
          <p className="text-zinc-400 text-sm mt-1">
            {Math.round(confidence * 100)}% confidence
          </p>
          <p className="text-xs text-zinc-500 mt-0.5">
            +{RARITY_POINTS[rarity]} pts
          </p>
        </div>
      </div>

      <button
        onClick={onSpotAnother}
        className="mt-4 w-full py-3 rounded-xl bg-zinc-800 hover:bg-zinc-700
                   border border-zinc-600 text-sm font-semibold transition-colors flex items-center justify-center gap-2"
      >
        <RefreshCw size={15} /> Spot Another
      </button>
    </div>
  )
}

export function SpotPage() {
  const { carData } = useContext(CarDataContext)
  const { modelReady, modelError, identify, CONFIDENCE_THRESHOLD } = useInference()
  const [phase, setPhase] = useState<Phase>('idle')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [result, setResult] = useState<{
    label: string; rarity: RarityTier; confidence: number
    isFirstSpot: boolean; photoDataUrl: string
  } | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  const processFile = useCallback(async (file: File) => {
    if (!file.type.startsWith('image/')) return

    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    setPhase('inferring')

    const res = await identify(file)

    if (!res || res.confidence < CONFIDENCE_THRESHOLD) {
      setPhase('unrecognized')
      return
    }

    const car = carData.find(c => c.idx === res.idx)
    if (!car) { setPhase('unrecognized'); return }

    const firstSpot = !hasSpotted(car.label)
    const thumb = await generateThumbnail(file)

    const spot: SpottedCar = {
      id:          `${Date.now()}-${res.idx}`,
      label:       car.label,
      idx:         car.idx,
      confidence:  res.confidence,
      timestamp:   new Date().toISOString(),
      rarityTier:  car.rarity,
      photoDataUrl: thumb,
      isFirstSpot:  firstSpot,
    }
    addSpot(spot)

    setResult({
      label:       car.label,
      rarity:      car.rarity,
      confidence:  res.confidence,
      isFirstSpot: firstSpot,
      photoDataUrl: thumb,
    })
    setPhase('result')
  }, [carData, identify, CONFIDENCE_THRESHOLD])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) processFile(file)
    e.target.value = ''
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) processFile(file)
  }

  const reset = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(null)
    setResult(null)
    setPhase('idle')
  }

  // ── Model not ready ────────────────────────────────────────────────────────
  if (modelError) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16 text-center">
        <AlertCircle className="mx-auto mb-4 text-red-400" size={40} />
        <h2 className="text-xl font-bold mb-2">Model Not Found</h2>
        <p className="text-zinc-400 text-sm leading-relaxed whitespace-pre-wrap">{modelError}</p>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-1">Spot a Car</h1>
      <p className="text-zinc-400 text-sm mb-6">
        {modelReady ? 'Upload a photo to identify and log it.' : 'Loading model…'}
      </p>

      {/* Upload zone — shown unless showing a result */}
      {phase !== 'result' && (
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`relative rounded-2xl border-2 border-dashed transition-colors
            ${dragOver ? 'border-blue-400 bg-blue-950/20' : 'border-zinc-700 bg-zinc-900'}
            ${phase === 'inferring' ? 'pointer-events-none' : 'cursor-pointer hover:border-zinc-500'}
          `}
          onClick={() => phase === 'idle' && fileInputRef.current?.click()}
        >
          {/* Preview image */}
          {previewUrl && (
            <img
              src={previewUrl}
              alt="preview"
              className="w-full aspect-video object-cover rounded-2xl"
            />
          )}

          {/* Overlay content */}
          <div className={`${previewUrl ? 'absolute inset-0 bg-black/50 rounded-2xl' : 'py-20'} flex flex-col items-center justify-center gap-3`}>
            {phase === 'inferring' ? (
              <>
                <RefreshCw size={32} className="text-blue-400 animate-spin" />
                <p className="text-sm text-zinc-300 font-medium">Identifying…</p>
              </>
            ) : (
              <>
                {!previewUrl && (
                  <>
                    <div className="flex gap-3">
                      <Camera size={28} className="text-zinc-500" />
                      <Upload size={28} className="text-zinc-500" />
                    </div>
                    <p className="text-zinc-400 text-sm font-medium">
                      {modelReady ? 'Tap to upload or drag a photo here' : 'Loading model…'}
                    </p>
                    <p className="text-zinc-600 text-xs">JPG, PNG, WEBP</p>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Hidden file input — accept camera on mobile */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileChange}
        disabled={!modelReady || phase === 'inferring'}
      />

      {/* Result card */}
      {phase === 'result' && result && (
        <ResultCard {...result} onSpotAnother={reset} />
      )}

      {/* Unrecognized modal */}
      {phase === 'unrecognized' && (
        <UnrecognizedModal onClose={reset} />
      )}
    </div>
  )
}
