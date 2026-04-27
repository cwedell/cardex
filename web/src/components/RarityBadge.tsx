import type { RarityTier } from '../types'
import { RARITY_LABEL, RARITY_COLOR, RARITY_DOT } from '../lib/rarity'

interface Props {
  tier: RarityTier
  size?: 'sm' | 'md'
}

export function RarityBadge({ tier, size = 'md' }: Props) {
  const textSize  = size === 'sm' ? 'text-xs' : 'text-sm'
  const dotSize   = size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2'

  return (
    <span className={`inline-flex items-center gap-1.5 font-semibold ${textSize} ${RARITY_COLOR[tier]}`}>
      <span className={`rounded-full ${dotSize} ${RARITY_DOT[tier]}`} />
      {RARITY_LABEL[tier]}
    </span>
  )
}
