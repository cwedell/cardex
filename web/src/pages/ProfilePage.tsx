import { useMemo, useState } from 'react'
import { getSpots, getUser, saveUser } from '../lib/storage'
import { RarityBadge } from '../components/RarityBadge'
import { RARITY_ORDER, RARITY_LABEL, RARITY_DOT, RARITY_POINTS } from '../lib/rarity'
import { Pencil, Check } from 'lucide-react'
import type { RarityTier } from '../types'

export function ProfilePage() {
  const user   = getUser()
  const spots  = getSpots()

  const [editing, setEditing]   = useState(false)
  const [nameInput, setNameInput] = useState(user.name)

  const spottedLabels = useMemo(() => new Set(spots.map(s => s.label)), [spots])

  const tierBreakdown = useMemo(() => {
    const counts: Record<RarityTier, number> = {
      common: 0, uncommon: 0, rare: 0, epic: 0, legendary: 0,
    }
    for (const s of spots) counts[s.rarityTier] = (counts[s.rarityTier] ?? 0) + 1
    return counts
  }, [spots])

  const totalPoints = spots.reduce(
    (sum, s) => sum + (RARITY_POINTS[s.rarityTier] ?? 10), 0
  )

  const initials = user.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
  const joinDate  = new Date(user.joinDate).toLocaleDateString('en-US', { year: 'numeric', month: 'long' })

  function saveName() {
    if (nameInput.trim()) {
      saveUser({ ...user, name: nameInput.trim() })
    }
    setEditing(false)
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-8 space-y-8">
      {/* Avatar + name */}
      <div className="flex items-center gap-4">
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold text-white flex-shrink-0"
          style={{ backgroundColor: user.avatarColor }}
        >
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          {editing ? (
            <div className="flex items-center gap-2">
              <input
                value={nameInput}
                onChange={e => setNameInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && saveName()}
                autoFocus
                className="bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-1.5
                           text-lg font-bold focus:outline-none focus:border-blue-500 w-full"
              />
              <button onClick={saveName} className="text-emerald-400 hover:text-emerald-300">
                <Check size={20} />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{user.name}</h1>
              <button
                onClick={() => { setNameInput(user.name); setEditing(true) }}
                className="text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                <Pencil size={14} />
              </button>
            </div>
          )}
          <p className="text-zinc-500 text-sm">Member since {joinDate}</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Total Spots',  value: spots.length },
          { label: 'Unique Cars',  value: spottedLabels.size },
          { label: 'Points',       value: totalPoints.toLocaleString() },
        ].map(({ label, value }) => (
          <div key={label} className="bg-zinc-900 border border-zinc-800 rounded-xl p-3 text-center">
            <p className="text-zinc-500 text-xs uppercase tracking-wide">{label}</p>
            <p className="text-xl font-bold mt-0.5">{value}</p>
          </div>
        ))}
      </div>

      {/* Rarity breakdown */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide mb-3">By Rarity</h2>
        <div className="space-y-2">
          {RARITY_ORDER.map(tier => (
            <div key={tier} className="flex items-center gap-3">
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${RARITY_DOT[tier]}`} />
              <span className="text-sm text-zinc-300 w-20">{RARITY_LABEL[tier]}</span>
              <div className="flex-1 bg-zinc-800 rounded-full h-1.5">
                <div
                  className="h-1.5 rounded-full"
                  style={{
                    width: `${spots.length ? Math.min(100, (tierBreakdown[tier] / spots.length) * 100) : 0}%`,
                    backgroundColor: getColor(tier),
                  }}
                />
              </div>
              <span className="text-xs text-zinc-500 w-6 text-right">{tierBreakdown[tier]}</span>
            </div>
          ))}
        </div>
      </section>

      {/* History */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide mb-3">
          Spot History
        </h2>
        {spots.length === 0 ? (
          <p className="text-zinc-500 text-sm">No spots yet. Head to the Spot page to get started!</p>
        ) : (
          <div className="space-y-2">
            {spots.map(spot => (
              <div key={spot.id}
                className="flex items-center gap-3 bg-zinc-900 border border-zinc-800 rounded-xl p-3">
                <img
                  src={spot.photoDataUrl}
                  alt={spot.label}
                  className="w-14 h-14 rounded-lg object-cover flex-shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{spot.label}</p>
                  <RarityBadge tier={spot.rarityTier} size="sm" />
                  <p className="text-zinc-600 text-xs mt-0.5">
                    {Math.round(spot.confidence * 100)}% confidence
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-xs text-zinc-500">
                    {new Date(spot.timestamp).toLocaleDateString()}
                  </p>
                  <p className="text-xs text-zinc-600">
                    {new Date(spot.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function getColor(tier: RarityTier): string {
  const map: Record<RarityTier, string> = {
    common: '#6b7280', uncommon: '#22c55e', rare: '#3b82f6', epic: '#a855f7', legendary: '#f59e0b',
  }
  return map[tier]
}
