import { useContext, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { getSpots, getUser } from '../lib/storage'
import { getOrInitChallenges } from '../lib/challenges'
import { RARITY_ORDER, RARITY_LABEL } from '../lib/rarity'
import { RarityBadge } from '../components/RarityBadge'
import { CarDataContext } from '../context/CarDataContext'
import type { RarityTier } from '../types'

const RARITY_COLORS: Record<RarityTier, string> = {
  common:    '#6b7280',
  uncommon:  '#22c55e',
  rare:      '#3b82f6',
  epic:      '#a855f7',
  legendary: '#f59e0b',
}

function SectionLabel({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center font-display font-bold text-[9px] tracking-[4px] text-rally-muted uppercase border-b border-rally-rule pb-[7px] mb-4">
      <span>{children}</span>
      {action && <span className="text-rally-red">{action}</span>}
    </div>
  )
}

function ChallengeCard({
  title,
  description,
  progress,
  target,
  points,
  completedAt,
  accentColor,
}: {
  title: string
  description: string
  progress: number
  target: number
  points: number
  completedAt: string | null
  accentColor: string
}) {
  const pct  = Math.min(100, Math.round((progress / target) * 100))
  const done = completedAt !== null

  return (
    <div
      className="bg-rally-paper border border-rally-rule p-[14px_18px]"
      style={{ borderTop: `3px solid ${accentColor}` }}
    >
      <div className="flex justify-between items-center mb-2">
        <span className="font-display font-bold text-[9px] tracking-[3px] text-rally-muted uppercase">{title}</span>
        <span className={`font-display font-bold text-[10px] ${done ? 'text-rally-gold' : 'text-rally-gold'}`}>
          {done ? '✓ Complete' : `+${points} pts`}
        </span>
      </div>
      <p className="font-serif italic text-sm mb-3">{description}</p>
      <div className="h-[3px] bg-rally-paper2">
        <div className="h-full transition-all" style={{ width: `${pct}%`, backgroundColor: accentColor }} />
      </div>
      <p className="font-display text-[9px] text-rally-muted tracking-[1px] mt-1.5">{progress} / {target}</p>
    </div>
  )
}

export function DashboardPage() {
  const { carData } = useContext(CarDataContext)
  const user        = getUser()
  const spots       = getSpots()
  const challenges  = getOrInitChallenges()

  const spottedLabels = useMemo(() => new Set(spots.map(s => s.label)), [spots])
  const totalCars     = carData.length

  const tierCounts = useMemo(() => {
    const counts: Record<RarityTier, { spotted: number; total: number }> = {
      common:    { spotted: 0, total: 0 },
      uncommon:  { spotted: 0, total: 0 },
      rare:      { spotted: 0, total: 0 },
      epic:      { spotted: 0, total: 0 },
      legendary: { spotted: 0, total: 0 },
    }
    for (const car of carData) {
      counts[car.rarity].total++
      if (spottedLabels.has(car.label)) counts[car.rarity].spotted++
    }
    return counts
  }, [carData, spottedLabels])

  const recentSpots = spots.slice(0, 3)
  const totalPts    = spots.reduce((sum, s) => {
    const pts: Record<RarityTier, number> = { common: 10, uncommon: 25, rare: 75, epic: 200, legendary: 500 }
    return sum + (pts[s.rarityTier] ?? 10)
  }, 0)

  const stats = [
    { label: 'Total Spots', value: spots.length },
    { label: 'Unique Cars', value: spottedLabels.size },
    { label: 'Points',      value: totalPts.toLocaleString() },
  ]

  return (
    <div className="max-w-[900px] mx-auto px-12 py-9 font-serif text-rally-dark">
      {/* Header */}
      <div className="flex items-end justify-between mb-7 pb-[22px] border-b border-rally-rule">
        <div>
          <p className="font-display font-bold text-[10px] tracking-[4px] text-rally-muted uppercase mb-1.5">Driver Dashboard</p>
          <h1 className="text-[36px] font-serif font-normal italic leading-tight">
            Welcome back,<br />
            <span
              className="not-italic font-display font-black text-[40px] text-rally-red uppercase"
              style={{ letterSpacing: '-1px' }}
            >
              {user.name}
            </span>
          </h1>
        </div>
        <div className="text-right">
          <p className="font-display font-black text-[64px] text-rally-dark leading-none" style={{ letterSpacing: '-2px' }}>
            {spottedLabels.size}
          </p>
          <p className="font-display font-bold text-[9px] text-rally-muted tracking-[2px] uppercase">
            of {totalCars} spotted
          </p>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 border border-b-0 border-rally-rule mb-7">
        {stats.map(({ label, value }, i) => (
          <div
            key={label}
            className={`p-[14px_20px] border-b border-rally-rule ${i < stats.length - 1 ? 'border-r border-rally-rule' : ''}`}
          >
            <p className="font-display font-bold text-[9px] tracking-[3px] text-rally-muted uppercase mb-1.5">{label}</p>
            <p className="font-display font-black text-[44px] text-rally-red leading-none" style={{ letterSpacing: '-1px' }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Collection Progress */}
      <div className="bg-rally-paper border border-rally-rule p-[20px_24px] mb-7">
        <SectionLabel>Collection Progress</SectionLabel>
        <div className="space-y-2.5">
          {RARITY_ORDER.map(tier => {
            const { spotted, total } = tierCounts[tier]
            const pct = total > 0 ? Math.round((spotted / total) * 100) : 0
            return (
              <div key={tier} className="flex items-center gap-3">
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: RARITY_COLORS[tier] }}
                />
                <span className="font-serif italic text-[13px] w-20">{RARITY_LABEL[tier]}</span>
                <div className="flex-1 h-[3px] bg-rally-paper2">
                  <div
                    className="h-full"
                    style={{ width: `${pct}%`, backgroundColor: RARITY_COLORS[tier] }}
                  />
                </div>
                <span className="font-display font-bold text-[10px] text-rally-muted text-right" style={{ minWidth: 44 }}>
                  {spotted}/{total}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Challenges */}
      <SectionLabel action={<Link to="/challenges" className="flex items-center gap-0.5">View All <ChevronRight size={10} /></Link>}>
        Challenges
      </SectionLabel>
      <div className="grid sm:grid-cols-2 gap-3.5 mb-7">
        <ChallengeCard
          title="Daily"
          description={challenges.daily.description}
          progress={challenges.daily.progress}
          target={typeof challenges.daily.target === 'number' ? challenges.daily.target : 1}
          points={challenges.daily.points}
          completedAt={challenges.daily.completedAt}
          accentColor="#c0200f"
        />
        <ChallengeCard
          title="Weekly"
          description={challenges.weekly.description}
          progress={challenges.weekly.progress}
          target={typeof challenges.weekly.target === 'number' ? challenges.weekly.target : 1}
          points={challenges.weekly.points}
          completedAt={challenges.weekly.completedAt}
          accentColor="#b8873f"
        />
      </div>

      {/* Recent spots */}
      {recentSpots.length > 0 && (
        <section className="mb-7">
          <SectionLabel action={<Link to="/profile" className="flex items-center gap-0.5">Full History <ChevronRight size={10} /></Link>}>
            Recent Spots
          </SectionLabel>
          <div className="space-y-2">
            {recentSpots.map(spot => (
              <div key={spot.id} className="flex items-center gap-3 bg-rally-paper border border-rally-rule p-3">
                <img
                  src={spot.photoDataUrl}
                  alt={spot.label}
                  className="w-14 h-14 object-cover flex-shrink-0"
                />
                <div className="min-w-0 flex-1">
                  <p className="font-serif italic text-sm truncate">{spot.label}</p>
                  <RarityBadge tier={spot.rarityTier} size="sm" />
                </div>
                <span className="font-display text-[9px] text-rally-muted flex-shrink-0 tracking-[1px]">
                  {new Date(spot.timestamp).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* CTA */}
      <Link
        to="/spot"
        className="flex items-center justify-center w-full py-[15px] bg-rally-red text-rally-cream
                   font-display font-black text-[11px] tracking-[5px] uppercase transition-colors
                   hover:bg-rally-dark"
      >
        Spot a Car
      </Link>
    </div>
  )
}
