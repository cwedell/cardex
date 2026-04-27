import { useCallback, useContext, useRef, useState } from 'react'
import { Camera, Upload, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react'
import { useInference } from '../hooks/useInference'
import { RarityBadge } from '../components/RarityBadge'
import { addSpot, hasSpotted } from '../lib/storage'
import { RARITY_POINTS } from '../lib/rarity'
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="bg-rally-paper border border-rally-rule max-w-sm w-full p-6 text-center animate-slide-up">
        <AlertCircle className="mx-auto mb-3 text-rally-gold" size={40} />
        <h2 className="font-serif italic text-xl mb-2 text-rally-dark">Great Spot!</h2>
        <p className="font-serif text-rally-muted text-sm leading-relaxed mb-5">
          We don't recognise this car! Your photo helps us improve — click below
          to flag it for our team and we'll investigate.
        </p>
        <button
          onClick={onClose}
          className="w-full py-3 bg-rally-gold text-rally-cream font-display font-black text-[10px] tracking-[3px] uppercase transition-colors hover:bg-rally-muted"
        >
          Add to Training Data
        </button>
        <button
          onClick={onClose}
          className="mt-2 w-full py-2 font-display text-[10px] text-rally-muted hover:text-rally-dark tracking-[2px] uppercase transition-colors"
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
    <div className="border border-rally-rule bg-rally-paper p-5 animate-slide-up">
      {isFirstSpot ? (
        <div className="flex items-center gap-2 text-rally-gold font-display font-bold text-[9px] tracking-[1.5px] uppercase mb-3">
          <CheckCircle2 size={14} />
          First spot! Added to your collection.
        </div>
      ) : (
        <div className="flex items-center gap-2 text-rally-muted font-display font-bold text-[9px] tracking-[1.5px] uppercase mb-3">
          <CheckCircle2 size={14} className="text-rally-gold" />
          Spotted again — logged to history.
        </div>
      )}

      <div className="flex gap-4">
        <img
          src={photoDataUrl}
          alt={label}
          className="w-24 h-24 object-cover flex-shrink-0"
        />
        <div className="flex flex-col justify-center min-w-0">
          <RarityBadge tier={rarity} size="sm" />
          <h2 className="font-serif italic text-lg mt-1 leading-snug text-rally-dark">{label}</h2>
          <p className="font-display text-rally-muted text-[10px] tracking-[1px] mt-1">
            {Math.round(confidence * 100)}% confidence
          </p>
          <p className="font-display font-bold text-[9px] text-rally-gold tracking-[2px] uppercase mt-0.5">
            +{RARITY_POINTS[rarity]} pts
          </p>
        </div>
      </div>

      <button
        onClick={onSpotAnother}
        className="mt-4 w-full py-3 bg-rally-paper2 hover:bg-rally-rule border border-rally-rule
                   font-display font-bold text-[10px] tracking-[3px] uppercase text-rally-muted
                   transition-colors flex items-center justify-center gap-2"
      >
        <RefreshCw size={14} /> Spot Another
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

  if (modelError) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16 text-center">
        <AlertCircle className="mx-auto mb-4 text-rally-red" size={40} />
        <h2 className="font-display font-bold text-xl tracking-[2px] uppercase mb-2 text-rally-dark">Model Not Found</h2>
        <p className="font-serif text-rally-muted text-sm leading-relaxed whitespace-pre-wrap">{modelError}</p>
      </div>
    )
  }

  return (
    <div className="max-w-[900px] mx-auto px-12 py-9 font-serif text-rally-dark">
      {/* Header */}
      <div className="mb-7 pb-5 border-b border-rally-rule">
        <p className="font-display font-bold text-[10px] tracking-[4px] text-rally-muted uppercase mb-1.5">Log Entry</p>
        <h1 className="font-serif font-normal italic text-[34px]">Spot a Car</h1>
        <p className="font-display text-[11px] text-rally-muted mt-1.5 tracking-[0.5px]">
          {modelReady ? 'Upload a photo to identify and log it.' : 'Loading model…'}
        </p>
      </div>

      {/* Upload zone */}
      {phase !== 'result' && (
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`relative border-2 border-dashed transition-colors mb-7
            ${dragOver ? 'border-rally-red bg-rally-paper2' : 'border-rally-rule bg-rally-paper'}
            ${phase === 'inferring' ? 'pointer-events-none' : 'cursor-pointer hover:border-rally-muted'}
          `}
          onClick={() => phase === 'idle' && fileInputRef.current?.click()}
        >
          {previewUrl && (
            <img
              src={previewUrl}
              alt="preview"
              className="w-full aspect-video object-cover"
            />
          )}

          <div className={`${previewUrl ? 'absolute inset-0 bg-black/50' : 'py-[52px] px-10'} flex flex-col items-center justify-center gap-3`}>
            {phase === 'inferring' ? (
              <>
                <RefreshCw size={32} className="text-rally-red animate-spin" />
                <p className="font-display font-bold text-[11px] tracking-[2px] uppercase text-rally-dark">Identifying…</p>
              </>
            ) : (
              !previewUrl && (
                <>
                  <div className="flex gap-3">
                    <Camera size={28} className="text-rally-muted" />
                    <Upload size={28} className="text-rally-muted" />
                  </div>
                  <p className="font-display font-bold text-[12px] tracking-[2px] text-rally-dark uppercase">
                    {modelReady ? 'Tap to upload or drag a photo here' : 'Loading model…'}
                  </p>
                  <p className="font-display text-[10px] text-rally-muted tracking-[1px]">JPG, PNG, WEBP</p>
                </>
              )
            )}
          </div>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileChange}
        disabled={!modelReady || phase === 'inferring'}
      />

      {phase !== 'result' && (
        <p className="font-display text-[10px] text-rally-muted text-center tracking-[1px]">
          Your photo will be analysed to identify the make, model &amp; generation.
        </p>
      )}

      {phase === 'result' && result && (
        <ResultCard {...result} onSpotAnother={reset} />
      )}

      {phase === 'unrecognized' && (
        <UnrecognizedModal onClose={reset} />
      )}
    </div>
  )
}
