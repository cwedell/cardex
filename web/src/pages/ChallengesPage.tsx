import { getOrInitChallenges } from '../lib/challenges'
import { CheckCircle2, Clock, Trophy } from 'lucide-react'
import type { ActiveChallenge } from '../types'

function ProgressBar({ value, max, done }: { value: number; max: number; done: boolean }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0
  return (
    <div className="w-full bg-zinc-800 rounded-full h-2 mt-3">
      <div
        className={`h-2 rounded-full transition-all ${done ? 'bg-emerald-500' : 'bg-blue-500'}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

function ChallengeCard({
  title,
  period,
  challenge,
}: {
  title: string
  period: string
  challenge: ActiveChallenge
}) {
  const done    = challenge.completedAt !== null
  const target  = typeof challenge.target === 'number' ? challenge.target : 1

  return (
    <div className={`rounded-2xl border p-5 ${done
      ? 'bg-emerald-950/30 border-emerald-800'
      : 'bg-zinc-900 border-zinc-800'
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{title}</span>
            <span className="text-xs text-zinc-600">· resets {period}</span>
          </div>
          <h3 className="font-semibold text-base leading-snug">{challenge.description}</h3>
        </div>
        {done ? (
          <CheckCircle2 className="text-emerald-400 flex-shrink-0 mt-0.5" size={22} />
        ) : (
          <Trophy className="text-blue-400 flex-shrink-0 mt-0.5" size={20} />
        )}
      </div>

      <ProgressBar value={challenge.progress} max={target} done={done} />

      <div className="flex items-center justify-between mt-2">
        <span className="text-sm text-zinc-400">
          {done
            ? `Completed at ${new Date(challenge.completedAt!).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
            : `${challenge.progress} / ${target}`
          }
        </span>
        <span className={`text-sm font-semibold ${done ? 'text-emerald-400' : 'text-blue-400'}`}>
          +{challenge.points} pts
        </span>
      </div>
    </div>
  )
}

export function ChallengesPage() {
  const challenges = getOrInitChallenges()

  const nextMidnight = (() => {
    const d = new Date()
    d.setHours(24, 0, 0, 0)
    const h = Math.floor((d.getTime() - Date.now()) / 3600000)
    const m = Math.floor(((d.getTime() - Date.now()) % 3600000) / 60000)
    return `${h}h ${m}m`
  })()

  return (
    <div className="max-w-lg mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Challenges</h1>
        <div className="flex items-center gap-1.5 text-zinc-500 text-sm">
          <Clock size={13} />
          Daily resets in {nextMidnight}
        </div>
      </div>

      <ChallengeCard
        title="Daily Challenge"
        period="at midnight"
        challenge={challenges.daily}
      />

      <ChallengeCard
        title="Weekly Challenge"
        period="on Monday"
        challenge={challenges.weekly}
      />

      {/* Historical flavour */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wide mb-3">How Challenges Work</h2>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-3 text-sm text-zinc-400">
          <p>A new daily challenge unlocks every midnight. Complete it to earn bonus points on top of every spot.</p>
          <p>Weekly challenges refresh every Monday and reward more points for bigger goals.</p>
          <p>Challenges automatically track your spots — just keep spotting!</p>
        </div>
      </section>
    </div>
  )
}
