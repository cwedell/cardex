import { getOrInitChallenges } from '../lib/challenges'
import { Clock } from 'lucide-react'
import type { ActiveChallenge } from '../types'

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="font-display font-bold text-[14px] tracking-[4px] text-rally-muted uppercase border-b border-rally-rule pb-[7px] mb-4">
      {children}
    </div>
  )
}

function ChallengeCard({
  title,
  period,
  challenge,
  accentColor,
}: {
  title: string
  period: string
  challenge: ActiveChallenge
  accentColor: string
}) {
  const done   = challenge.completedAt !== null
  const target = typeof challenge.target === 'number' ? challenge.target : 1
  const pct    = target > 0 ? Math.min(100, Math.round((challenge.progress / target) * 100)) : 0

  return (
    <div
      className="bg-rally-paper border border-rally-rule p-[20px_24px] mb-3.5"
      style={{ borderTop: `3px solid ${accentColor}` }}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="font-display font-bold text-[14px] tracking-[3px] text-rally-muted uppercase mb-1.5">
            {title}{' '}
            <span className="text-rally-rule ml-1">· resets {period}</span>
          </div>
          <h3 className="font-serif italic text-[20px] text-rally-dark leading-snug">
            {challenge.description}
          </h3>
        </div>
        {/* Trophy icon */}
        <svg width="22" height="26" viewBox="0 0 22 26" fill="none" className="flex-shrink-0 mt-0.5">
          <path d="M4 2h14v14a7 7 0 01-14 0V2Z" stroke={accentColor} strokeWidth="1.5" fill={accentColor} fillOpacity="0.1" />
          <path d="M1 6h3M18 6h3" stroke={accentColor} strokeWidth="1.5" strokeLinecap="round" />
          <path d="M11 16v4M8 24h6" stroke="#8a7a62" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </div>

      <div className="h-[5px] bg-rally-paper2 mb-2">
        <div className="h-full transition-all" style={{ width: `${pct}%`, backgroundColor: accentColor }} />
      </div>

      <div className="flex justify-between items-center">
        <span className="font-display text-[15px] text-rally-muted">
          {done
            ? `Completed at ${new Date(challenge.completedAt!).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
            : `${challenge.progress} / ${target}`
          }
        </span>
        <span className="font-display font-bold text-[15px] text-rally-gold">
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
    <div className="max-w-[900px] mx-auto px-12 py-9 font-serif text-rally-dark">
      {/* Header */}
      <div className="mb-7 pb-5 border-b border-rally-rule">
        <p className="font-display font-bold text-[15px] tracking-[4px] text-rally-muted uppercase mb-[5px]">
          Active Objectives
        </p>
        <h1 className="font-serif font-normal italic text-[34px]">Challenges</h1>
        <div className="flex items-center gap-1.5 mt-1.5">
          <Clock size={12} className="text-rally-muted" />
          <span className="font-display text-[15px] text-rally-muted tracking-[1px]">
            Daily resets in {nextMidnight}
          </span>
        </div>
      </div>

      <ChallengeCard
        title="Daily Challenge"
        period="at midnight"
        challenge={challenges.daily}
        accentColor="#c0200f"
      />

      <ChallengeCard
        title="Weekly Challenge"
        period="on Monday"
        challenge={challenges.weekly}
        accentColor="#b8873f"
      />

      {/* How it works */}
      <SectionLabel>How Challenges Work</SectionLabel>
      <div className="bg-rally-paper border border-rally-rule p-[20px_24px]">
        {[
          'A new daily challenge unlocks every midnight. Complete it to earn bonus points on top of every spot.',
          'Weekly challenges refresh every Monday and reward more points for bigger goals.',
          'Challenges automatically track your spots — just keep spotting!',
        ].map((text, i) => (
          <div key={i} className={`flex gap-3 ${i < 2 ? 'mb-3.5' : ''}`}>
            <div
              className="w-[18px] h-[18px] border border-rally-rule flex-shrink-0 flex items-center justify-center
                         font-display font-bold text-[14px] text-rally-muted mt-0.5"
            >
              {i + 1}
            </div>
            <p className="font-serif italic text-[16px] leading-relaxed text-rally-dark">{text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
