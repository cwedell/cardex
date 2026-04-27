import { useMemo, useState } from 'react'
import { getAllTimeLeaderboard, getWeeklyLeaderboard, getDailyLeaderboard } from '../lib/mockUsers'
import type { MockUser } from '../types'

type Period = 'alltime' | 'weekly' | 'daily'

function Avatar({ name, color, size = 36 }: { name: string; color: string; size?: number }) {
  const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
  return (
    <div
      className="rounded-full flex items-center justify-center text-white font-bold flex-shrink-0"
      style={{ width: size, height: size, backgroundColor: color, fontSize: size * 0.38 }}
    >
      {initials}
    </div>
  )
}

function RankRow({ user, rank }: { user: MockUser; rank: number }) {
  const medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : null

  return (
    <div className={`flex items-center gap-3 p-3 rounded-xl border transition-colors
      ${user.isMe
        ? 'bg-blue-950/40 border-blue-700'
        : 'bg-zinc-900 border-zinc-800'}`}>
      <span className="w-7 text-center text-sm font-bold flex-shrink-0">
        {medal ?? <span className="text-zinc-500">{rank}</span>}
      </span>
      <Avatar name={user.name} color={user.avatarColor} />
      <div className="flex-1 min-w-0">
        <p className={`font-semibold text-sm ${user.isMe ? 'text-blue-300' : ''}`}>
          {user.name} {user.isMe && <span className="text-xs text-blue-400">(you)</span>}
        </p>
        <p className="text-xs text-zinc-500">{user.uniqueCars} unique cars</p>
      </div>
      <div className="text-right flex-shrink-0">
        <p className="font-bold text-sm">{user.totalSpots}</p>
        <p className="text-xs text-zinc-500">spots</p>
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
    <div className="max-w-lg mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-1">Leaderboard</h1>
      <p className="text-zinc-400 text-sm mb-6">
        You are ranked #{myRank} · {board.find(u => u.isMe)?.totalSpots ?? 0} spots
      </p>

      {/* Period selector */}
      <div className="flex gap-2 mb-6">
        {([['alltime', 'All Time'], ['weekly', 'This Week'], ['daily', 'Today']] as [Period, string][]).map(([p, label]) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`flex-1 py-2 rounded-xl text-sm font-semibold border transition-colors
              ${period === p
                ? 'bg-blue-600 border-blue-500 text-white'
                : 'bg-zinc-900 border-zinc-700 text-zinc-400 hover:border-zinc-500'
              }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Rankings */}
      <div className="space-y-2">
        {board.map((user, i) => (
          <RankRow key={user.id} user={user} rank={i + 1} />
        ))}
      </div>
    </div>
  )
}
