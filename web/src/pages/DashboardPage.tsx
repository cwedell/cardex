import { useContext, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Camera, ChevronRight } from 'lucide-react'
import { getSpots, getUser } from '../lib/storage'
import { getOrInitChallenges } from '../lib/challenges'
import { RARITY_ORDER, RARITY_LABEL, RARITY_COLOR, RARITY_DOT } from '../lib/rarity'
import { RarityBadge } from '../components/RarityBadge'
import { CarDataContext } from '../context/CarDataContext'
import type { RarityTier } from '../types'

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex flex-col gap-1">
      <span className="text-zinc-400 text-xs uppercase tracking-wide">{label}</span>
      <span className="text-2xl font-bold">{value}</span>
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
}: {
  title: string
  description: string
  progress: number
  target: number
  points: number
  completedAt: string | null
}) {
  const pct = Math.min(100, Math.round((progress / target) * 100))
  const done = completedAt !== null

  return (
    <div className={`rounded-xl border p-4 ${done ? 'border-emerald-800 bg-emerald-950/30' : 'border-zinc-800 bg-zinc-900'}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-zinc-500 uppercase tracking-wide font-semibold">{title}</span>
        <span className={`text-xs font-semibold ${done ? 'text-emerald-400' : 'text-blue-400'}`}>
          {done ? '✓ Complete' : `+${points} pts`}
        </span>
      </div>
      <p className="text-sm font-medium mb-3">{description}</p>
      <div className="w-full bg-zinc-800 rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full transition-all ${done ? 'bg-emerald-500' : 'bg-blue-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-zinc-500 mt-1">{progress} / {target}</p>
    </div>
  )
}

export function DashboardPage() {
  const { carData } = useContext(CarDataContext)
  const user       = getUser()
  const spots      = getSpots()
  const challenges = getOrInitChallenges()

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

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-8">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold">Welcome back, {user.name} 👋</h1>
        <p className="text-zinc-400 text-sm mt-1">
          {spottedLabels.size} of {totalCars} cars spotted
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Total Spots" value={spots.length} />
        <StatCard label="Unique Cars" value={spottedLabels.size} />
        <StatCard label="Points"      value={totalPts.toLocaleString()} />
      </div>

      {/* Progress by tier */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide mb-3">Collection Progress</h2>
        <div className="space-y-2">
          {RARITY_ORDER.map(tier => {
            const { spotted, total } = tierCounts[tier]
            const pct = total > 0 ? Math.round((spotted / total) * 100) : 0
            return (
              <div key={tier} className="flex items-center gap-3">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${RARITY_DOT[tier]}`} />
                <span className={`text-sm w-20 ${RARITY_COLOR[tier]}`}>{RARITY_LABEL[tier]}</span>
                <div className="flex-1 bg-zinc-800 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full transition-all`}
                    style={{ width: `${pct}%`, backgroundColor: getComputedColor(tier) }}
                  />
                </div>
                <span className="text-xs text-zinc-500 w-16 text-right">{spotted}/{total}</span>
              </div>
            )
          })}
        </div>
      </section>

      {/* Daily & Weekly challenges */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide">Challenges</h2>
          <Link to="/challenges" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-0.5">
            View all <ChevronRight size={12} />
          </Link>
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          <ChallengeCard
            title="Daily"
            description={challenges.daily.description}
            progress={challenges.daily.progress}
            target={typeof challenges.daily.target === 'number' ? challenges.daily.target : 1}
            points={challenges.daily.points}
            completedAt={challenges.daily.completedAt}
          />
          <ChallengeCard
            title="Weekly"
            description={challenges.weekly.description}
            progress={challenges.weekly.progress}
            target={typeof challenges.weekly.target === 'number' ? challenges.weekly.target : 1}
            points={challenges.weekly.points}
            completedAt={challenges.weekly.completedAt}
          />
        </div>
      </section>

      {/* Recent spots */}
      {recentSpots.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide">Recent Spots</h2>
            <Link to="/profile" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-0.5">
              Full history <ChevronRight size={12} />
            </Link>
          </div>
          <div className="space-y-2">
            {recentSpots.map(spot => (
              <div key={spot.id} className="flex items-center gap-3 bg-zinc-900 border border-zinc-800 rounded-xl p-3">
                <img
                  src={spot.photoDataUrl}
                  alt={spot.label}
                  className="w-14 h-14 rounded-lg object-cover flex-shrink-0"
                />
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-sm truncate">{spot.label}</p>
                  <RarityBadge tier={spot.rarityTier} size="sm" />
                </div>
                <span className="text-xs text-zinc-600 flex-shrink-0">
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
        className="flex items-center justify-center gap-2 w-full py-4 rounded-2xl
                   bg-blue-600 hover:bg-blue-500 text-white font-semibold text-lg
                   transition-colors shadow-lg shadow-blue-900/30"
      >
        <Camera size={22} /> Spot a Car
      </Link>
    </div>
  )
}

function getComputedColor(tier: RarityTier): string {
  const map: Record<RarityTier, string> = {
    common:    '#6b7280',
    uncommon:  '#22c55e',
    rare:      '#3b82f6',
    epic:      '#a855f7',
    legendary: '#f59e0b',
  }
  return map[tier]
}
