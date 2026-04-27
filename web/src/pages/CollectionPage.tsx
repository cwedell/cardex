import { useContext, useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { CarDataContext } from '../context/CarDataContext'
import { getSpots, getSpottedLabels } from '../lib/storage'
import { RarityBadge } from '../components/RarityBadge'
import { RARITY_ORDER, RARITY_LABEL } from '../lib/rarity'
import type { RarityTier } from '../types'

const RARITY_COLORS: Record<RarityTier, string> = {
  common:    '#6b7280',
  uncommon:  '#22c55e',
  rare:      '#3b82f6',
  epic:      '#a855f7',
  legendary: '#f59e0b',
}

type Filter = 'all' | RarityTier | 'spotted' | 'unspotted'

function CarSilhouette() {
  return (
    <svg viewBox="0 0 120 60" width="100%" height="100%" fill="none">
      <path d="M10 40 Q15 30 30 26 L45 18 Q55 14 70 14 L90 16 Q102 18 108 26 L112 40 Z" fill="#dfd7c4" />
      <ellipse cx="30" cy="40" rx="10" ry="10" fill="#c8bfad" />
      <ellipse cx="90" cy="40" rx="10" ry="10" fill="#c8bfad" />
      <path d="M40 26 L55 16 L80 16 L92 26 Z" fill="#c8bfad" opacity="0.4" />
    </svg>
  )
}

function CarCard({ label, rarity, photoDataUrl, spotted }: {
  label: string; rarity: RarityTier; photoDataUrl?: string; spotted: boolean
}) {
  return (
    <div className={`border overflow-hidden transition-opacity
      ${spotted ? 'border-rally-rule bg-rally-paper' : 'border-rally-rule bg-rally-paper opacity-60'}`}>
      <div className="w-full bg-rally-paper2 relative" style={{ height: 110 }}>
        {spotted && photoDataUrl ? (
          <img src={photoDataUrl} alt={label} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center p-2">
            <CarSilhouette />
          </div>
        )}
      </div>
      <div className="p-[10px_12px_12px]">
        <p className="font-serif italic text-[12px] leading-tight mb-1.5 text-rally-dark"
           style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {label}
        </p>
        <RarityBadge tier={rarity} size="sm" />
      </div>
    </div>
  )
}

function FilterPill({ label, active, dot, onClick }: {
  label: string; active?: boolean; dot?: string; onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 font-display font-bold text-[10px] tracking-[1.5px] uppercase border transition-colors
        ${active
          ? 'bg-rally-dark border-rally-dark text-rally-cream'
          : 'bg-rally-paper border-rally-rule text-rally-muted hover:border-rally-muted'
        }`}
    >
      {dot && <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: dot }} />}
      {label}
    </button>
  )
}

export function CollectionPage() {
  const { carData }   = useContext(CarDataContext)
  const [query, setQuery]   = useState('')
  const [filter, setFilter] = useState<Filter>('all')

  const spots         = getSpots()
  const spottedLabels = useMemo(() => getSpottedLabels(), [spots.length])

  const photoByLabel = useMemo(() => {
    const m = new Map<string, string>()
    for (const s of [...spots].reverse()) {
      m.set(s.label, s.photoDataUrl)
    }
    return m
  }, [spots.length])

  const filtered = useMemo(() => {
    let list = carData
    if (filter === 'spotted')   list = list.filter(c => spottedLabels.has(c.label))
    if (filter === 'unspotted') list = list.filter(c => !spottedLabels.has(c.label))
    if (RARITY_ORDER.includes(filter as RarityTier)) {
      list = list.filter(c => c.rarity === filter)
    }
    if (query.trim()) {
      const q = query.trim().toLowerCase()
      list = list.filter(c => c.label.toLowerCase().includes(q))
    }
    return list
  }, [carData, filter, query, spottedLabels])

  const spottedCount = spottedLabels.size

  return (
    <div className="max-w-[900px] mx-auto px-12 py-9 font-serif text-rally-dark">
      {/* Header */}
      <div className="flex items-end justify-between mb-[22px] pb-[18px] border-b border-rally-rule">
        <div>
          <p className="font-display font-bold text-[10px] tracking-[4px] text-rally-muted uppercase mb-[5px]">Your Garage</p>
          <h1 className="font-serif font-normal italic text-[32px]">Collection</h1>
        </div>
        <div className="text-right">
          <p className="font-display font-black text-[11px] tracking-[3px] text-rally-muted uppercase">Cars Spotted</p>
          <p className="font-display font-black text-[40px] text-rally-red leading-none" style={{ letterSpacing: '-1px' }}>
            {spottedCount}{' '}
            <span className="text-[18px] text-rally-muted font-normal" style={{ letterSpacing: 0 }}>/{carData.length}</span>
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-rally-muted" />
        <input
          type="text"
          placeholder="Search cars…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 bg-rally-paper border border-rally-rule
                     font-serif italic text-[13px] text-rally-dark placeholder-rally-muted
                     focus:outline-none focus:border-rally-red transition-colors"
        />
      </div>

      {/* Filter pills */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        <FilterPill label="All"       active={filter === 'all'}       onClick={() => setFilter('all')} />
        <FilterPill label="Spotted"   active={filter === 'spotted'}   onClick={() => setFilter('spotted')} />
        <FilterPill label="Unspotted" active={filter === 'unspotted'} onClick={() => setFilter('unspotted')} />
        {RARITY_ORDER.map(tier => (
          <FilterPill
            key={tier}
            label={RARITY_LABEL[tier]}
            active={filter === tier}
            dot={RARITY_COLORS[tier]}
            onClick={() => setFilter(tier)}
          />
        ))}
      </div>

      <p className="font-display text-[9px] tracking-[2px] text-rally-muted uppercase mb-3.5">
        Showing {filtered.length} cars
      </p>

      {/* Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {filtered.map(car => (
          <CarCard
            key={car.idx}
            label={car.label}
            rarity={car.rarity}
            photoDataUrl={photoByLabel.get(car.label)}
            spotted={spottedLabels.has(car.label)}
          />
        ))}
        {filtered.length === 0 && (
          <p className="col-span-full text-center font-serif italic text-rally-muted py-16">
            No cars match your search.
          </p>
        )}
      </div>
    </div>
  )
}
