import { useMemo, useState } from 'react'
import { getSpots, getUser, saveUser } from '../lib/storage'
import { RarityBadge } from '../components/RarityBadge'
import { RARITY_ORDER, RARITY_LABEL, RARITY_POINTS } from '../lib/rarity'
import { Pencil, Check } from 'lucide-react'
import type { RarityTier } from '../types'

const RARITY_COLORS: Record<RarityTier, string> = {
  common:    '#6b7280',
  uncommon:  '#22c55e',
  rare:      '#3b82f6',
  epic:      '#a855f7',
  legendary: '#f59e0b',
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="font-display font-bold text-[9px] tracking-[4px] text-rally-muted uppercase border-b border-rally-rule pb-[7px] mb-4">
      {children}
    </div>
  )
}

export function ProfilePage() {
  const user  = getUser()
  const spots = getSpots()

  const [editing, setEditing]     = useState(false)
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

  const stats = [
    { label: 'Total Spots', value: spots.length },
    { label: 'Unique Cars', value: spottedLabels.size },
    { label: 'Points',      value: totalPoints.toLocaleString() },
  ]

  return (
    <div className="max-w-[900px] mx-auto px-12 py-9 font-serif text-rally-dark">
      {/* Avatar + name */}
      <div className="flex items-center gap-5 mb-7 pb-6 border-b border-rally-rule">
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center font-display font-black text-2xl text-white flex-shrink-0"
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
                className="bg-rally-paper border border-rally-rule px-3 py-1.5
                           font-serif italic text-lg text-rally-dark focus:outline-none focus:border-rally-red w-full"
              />
              <button onClick={saveName} className="text-rally-gold hover:text-rally-dark transition-colors">
                <Check size={20} />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <h1 className="font-serif italic text-[28px] font-normal">{user.name}</h1>
              <button
                onClick={() => { setNameInput(user.name); setEditing(true) }}
                className="text-rally-muted hover:text-rally-dark transition-colors"
              >
                <Pencil size={14} />
              </button>
            </div>
          )}
          <p className="font-display text-[10px] text-rally-muted tracking-[1px] mt-1">Member since {joinDate}</p>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 border border-b-0 border-rally-rule mb-7">
        {stats.map(({ label, value }, i) => (
          <div
            key={label}
            className={`p-[14px_20px] border-b border-rally-rule text-center ${i < stats.length - 1 ? 'border-r border-rally-rule' : ''}`}
          >
            <p className="font-display font-bold text-[9px] tracking-[3px] text-rally-muted uppercase mb-1.5">{label}</p>
            <p className="font-display font-black text-[36px] text-rally-red leading-none" style={{ letterSpacing: '-1px' }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Rarity breakdown */}
      <div className="bg-rally-paper border border-rally-rule p-[20px_24px] mb-7">
        <SectionLabel>By Rarity</SectionLabel>
        <div className="space-y-2.5">
          {RARITY_ORDER.map(tier => (
            <div key={tier} className="flex items-center gap-3">
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: RARITY_COLORS[tier] }}
              />
              <span className="font-serif italic text-[13px] w-20">{RARITY_LABEL[tier]}</span>
              <div className="flex-1 h-[3px] bg-rally-paper2">
                <div
                  className="h-full"
                  style={{
                    width: `${spots.length ? Math.min(100, (tierBreakdown[tier] / spots.length) * 100) : 0}%`,
                    backgroundColor: RARITY_COLORS[tier],
                  }}
                />
              </div>
              <span className="font-display font-bold text-[10px] text-rally-muted w-6 text-right">
                {tierBreakdown[tier]}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Spot history */}
      <SectionLabel>Spot History</SectionLabel>
      {spots.length === 0 ? (
        <p className="font-serif italic text-rally-muted text-sm">
          No spots yet. Head to the Spot page to get started!
        </p>
      ) : (
        <div className="space-y-2">
          {spots.map(spot => (
            <div key={spot.id} className="flex items-center gap-3.5 bg-rally-paper border border-rally-rule p-[10px_14px]">
              <div className="w-[60px] h-[44px] flex-shrink-0 overflow-hidden">
                <img
                  src={spot.photoDataUrl}
                  alt={spot.label}
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-serif italic text-[13px] mb-1 text-rally-dark truncate">{spot.label}</p>
                <div className="flex items-center gap-2">
                  <RarityBadge tier={spot.rarityTier} size="sm" />
                  <span className="font-display text-[9px] text-rally-muted">
                    · {Math.round(spot.confidence * 100)}% confidence
                  </span>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="font-display font-bold text-[10px] text-rally-muted">
                  {new Date(spot.timestamp).toLocaleDateString()}
                </p>
                <p className="font-display text-[9px] text-rally-rule mt-0.5">
                  {new Date(spot.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
