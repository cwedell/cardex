import { useContext, useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { CarDataContext } from '../context/CarDataContext'
import { getSpots, getSpottedLabels } from '../lib/storage'
import { RarityBadge } from '../components/RarityBadge'
import { RARITY_ORDER, RARITY_LABEL, RARITY_DOT } from '../lib/rarity'
import type { RarityTier } from '../types'

type Filter = 'all' | RarityTier | 'spotted' | 'unspotted'

function CarCard({ label, rarity, photoDataUrl, spotted }: {
  label: string; rarity: RarityTier; photoDataUrl?: string; spotted: boolean
}) {
  return (
    <div className={`rounded-xl border overflow-hidden transition-opacity
      ${spotted ? 'border-zinc-700 bg-zinc-900' : 'border-zinc-800 bg-zinc-950 opacity-60'}`}>
      <div className="aspect-video w-full bg-zinc-800 relative">
        {spotted && photoDataUrl ? (
          <img src={photoDataUrl} alt={label} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <svg viewBox="0 0 64 40" className="w-16 opacity-20 fill-zinc-400">
              <path d="M10 28 L6 28 C4 28 2 26 2 24 L2 18 C2 16 3 14 5 13 L12 11 L20 6 C22 5 24 4 26 4 L42 4 C44 4 46 5 48 6 L56 11 L61 13 C63 14 64 16 64 18 L64 24 C64 26 62 28 60 28 L54 28 C53 32 50 36 46 36 C42 36 39 32 38 28 L26 28 C25 32 22 36 18 36 C14 36 11 32 10 28Z" />
            </svg>
          </div>
        )}
      </div>
      <div className="p-2.5">
        <p className="text-xs font-medium leading-tight mb-1 line-clamp-2">{label}</p>
        <RarityBadge tier={rarity} size="sm" />
      </div>
    </div>
  )
}

export function CollectionPage() {
  const { carData }   = useContext(CarDataContext)
  const [query, setQuery]   = useState('')
  const [filter, setFilter] = useState<Filter>('all')

  const spots        = getSpots()
  const spottedLabels = useMemo(() => getSpottedLabels(), [spots.length])

  // Most recent photo per label
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
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-1">Collection</h1>
      <p className="text-zinc-400 text-sm mb-5">
        {spottedCount} of {carData.length} spotted
      </p>

      {/* Search */}
      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
        <input
          type="text"
          placeholder="Search cars…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-zinc-900 border border-zinc-700
                     text-sm placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition-colors"
        />
      </div>

      {/* Filter pills */}
      <div className="flex gap-2 flex-wrap mb-5">
        {(['all', 'spotted', 'unspotted', ...RARITY_ORDER] as Filter[]).map(f => {
          const isRarity = RARITY_ORDER.includes(f as RarityTier)
          return (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold
                border transition-colors
                ${filter === f
                  ? 'bg-blue-600 border-blue-500 text-white'
                  : 'bg-zinc-900 border-zinc-700 text-zinc-400 hover:border-zinc-500'
                }`}
            >
              {isRarity && (
                <span className={`w-1.5 h-1.5 rounded-full ${RARITY_DOT[f as RarityTier]}`} />
              )}
              {f === 'all' ? 'All' : f === 'spotted' ? 'Spotted' : f === 'unspotted' ? 'Unspotted' : RARITY_LABEL[f as RarityTier]}
            </button>
          )
        })}
      </div>

      <p className="text-xs text-zinc-600 mb-4">Showing {filtered.length} cars</p>

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
          <p className="col-span-full text-center text-zinc-500 py-16">No cars match your search.</p>
        )}
      </div>
    </div>
  )
}
