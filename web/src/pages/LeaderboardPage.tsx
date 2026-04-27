import { useMemo, useState } from 'react'
import { getAllTimeLeaderboard, getWeeklyLeaderboard, getDailyLeaderboard } from '../lib/mockUsers'
import type { MockUser } from '../types'

type Period = 'alltime' | 'weekly' | 'daily'

const TROPHY_COLORS: Record<number, string> = {
  1: '#b8873f',
  2: '#9ca3af',
  3: '#c07a4a',
}

function Avatar({ name, color, size = 36 }: { name: string; color: string; size?: number }) {
  const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
  return (
    <div
      className="rounded-full flex items-center justify-center text-white font-display font-black flex-shrink-0"
      style={{ width: size, height: size, backgroundColor: color, fontSize: size * 0.38 }}
    >
      {initials}
    </div>
  )
}

function TrophyIcon({ color }: { color: string }) {
  return (
    <svg width="18" height="20" viewBox="0 0 18 20" fill="none">
      <path d="M2 1h14v9a7 7 0 01-14 0V1Z" fill={color} fillOpacity="0.2" stroke={color} strokeWidth="1.3" />
      <path d="M0 4h2M16 4h2" stroke={color} strokeWidth="1.3" strokeLinecap="round" />
      <path d="M9 10v4M6 18h6" stroke={color} strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  )
}

function RankRow({ user, rank }: { user: MockUser; rank: number }) {
  const trophyColor = TROPHY_COLORS[rank]

  return (
    <div className={`flex items-center gap-3.5 px-4 py-3 transition-colors
      ${user.isMe
        ? 'bg-rally-paper border border-rally-red mb-0.5'
        : 'border-b border-rally-rule'
      }`}>
      <div className="w-7 text-center flex-shrink-0 flex items-center justify-center">
        {trophyColor ? (
          <TrophyIcon color={trophyColor} />
        ) : (
          <span className={`font-display font-bold text-[13px] ${user.isMe ? 'text-rally-red' : 'text-rally-muted'}`}>
            {rank}
          </span>
        )}
      </div>
      <Avatar name={user.name} color={user.avatarColor} />
      <div className="flex-1 min-w-0">
        <p className="font-serif italic text-[14px] text-rally-dark">
          {user.name}{' '}
          {user.isMe && (
            <span className="font-display font-bold text-[9px] text-rally-red tracking-[1px] uppercase not-italic">
              YOU
            </span>
          )}
        </p>
        <p className="font-display text-[9px] text-rally-muted tracking-[0.5px]">{user.uniqueCars} unique cars</p>
      </div>
      <div className="text-right flex-shrink-0">
        <p
          className={`font-display font-black text-[22px] leading-none ${user.isMe ? 'text-rally-red' : 'text-rally-dark'}`}
        >
          {user.totalSpots}
        </p>
        <p className="font-display text-[9px] text-rally-muted tracking-[1px]">spots</p>
      </div>
    </div>
  )
}

export function LeaderboardPage() {
  const [period, setPeriod] = useState<Period>('alltime')

  const board = useMemo(() => {
    if (period === 'alltime') return getAllTimeLeaderboard()
    if (period === 'weekly')  return getWeeklyLeaderboard()
    return getDailyLeaderboard()
  }, [period])

  const myRank = board.findIndex(u => u.isMe) + 1

  return (
    <div className="max-w-[900px] mx-auto px-12 py-9 font-serif text-rally-dark">
      {/* Header */}
      <div className="mb-7 pb-5 border-b border-rally-rule">
        <p className="font-display font-bold text-[10px] tracking-[4px] text-rally-muted uppercase mb-[5px]">Community</p>
        <h1 className="font-serif font-normal italic text-[34px]">Leaderboard</h1>
        <p className="font-display text-[10px] text-rally-muted mt-1.5 tracking-[0.5px]">
          You are ranked #{myRank} · {board.find(u => u.isMe)?.totalSpots ?? 0} spots
        </p>
      </div>

      {/* Period tabs */}
      <div className="flex border border-rally-rule w-fit mb-6">
        {([['alltime', 'All Time'], ['weekly', 'This Week'], ['daily', 'Today']] as [Period, string][]).map(([p, label], i, arr) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`py-2 px-5 font-display font-bold text-[10px] tracking-[2px] uppercase transition-colors
              ${i < arr.length - 1 ? 'border-r border-rally-rule' : ''}
              ${period === p
                ? 'bg-rally-dark text-rally-cream'
                : 'bg-transparent text-rally-muted hover:text-rally-dark'
              }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Rankings */}
      <div>
        {board.map((user, i) => (
          <RankRow key={user.id} user={user} rank={i + 1} />
        ))}
      </div>
    </div>
  )
}
