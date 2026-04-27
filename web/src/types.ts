export type RarityTier = 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary'

export interface CarData {
  idx: number
  label: string
  make: string
  rarity: RarityTier
  rarityRank: number
  imageCount: number
}

export interface SpottedCar {
  id: string
  label: string
  idx: number
  confidence: number
  timestamp: string
  rarityTier: RarityTier
  photoDataUrl: string
  isFirstSpot: boolean
}

export interface UserProfile {
  name: string
  avatarColor: string
  joinDate: string
}

export type ChallengeKind =
  | 'spot_count'
  | 'unique_count'
  | 'rarity_min'

export interface ChallengeTemplate {
  id: string
  description: string
  kind: ChallengeKind
  target: number | RarityTier
  points: number
}

export interface ActiveChallenge {
  templateId: string
  description: string
  kind: ChallengeKind
  target: number | RarityTier
  points: number
  progress: number
  completedAt: string | null
}

export interface ChallengeState {
  daily: ActiveChallenge & { date: string }
  weekly: ActiveChallenge & { weekStart: string }
}

export interface InferenceResult {
  idx: number
  confidence: number
}

export interface MockUser {
  id: string
  name: string
  totalSpots: number
  uniqueCars: number
  avatarColor: string
  isMe?: boolean
}
