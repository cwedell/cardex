import type { RarityTier } from '../types'
import { RARITY_LABEL } from '../lib/rarity'

const RARITY_HEX: Record<RarityTier, string> = {
  common:    '#6b7280',
  uncommon:  '#22c55e',
  rare:      '#3b82f6',
  epic:      '#a855f7',
  legendary: '#f59e0b',
}

interface Props {
  tier: RarityTier
  size?: 'sm' | 'md'
}

export function RarityBadge({ tier, size = 'md' }: Props) {
  const fontSize = size === 'sm' ? '14px' : '15px'
  const dotSize  = size === 'sm' ? 6 : 8
  const color    = RARITY_HEX[tier]

  return (
    <span
      className="inline-flex items-center gap-1 font-display font-bold uppercase"
      style={{ fontSize, color, letterSpacing: '1.5px' }}
    >
      <span
        className="rounded-full flex-shrink-0"
        style={{ width: dotSize, height: dotSize, backgroundColor: color }}
      />
      {RARITY_LABEL[tier]}
    </span>
  )
}
