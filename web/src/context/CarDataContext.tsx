import { createContext, useEffect, useState, type ReactNode } from 'react'
import type { CarData } from '../types'

interface CarDataContextValue {
  carData:  CarData[]
  loading:  boolean
  error:    string | null
}

export const CarDataContext = createContext<CarDataContextValue>({
  carData: [],
  loading: true,
  error:   null,
})

export function CarDataProvider({ children }: { children: ReactNode }) {
  const [carData, setCarData] = useState<CarData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  useEffect(() => {
    const url = `${import.meta.env.BASE_URL}car_data.json`
    fetch(url)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<CarData[]>
      })
      .then(data => { setCarData(data); setLoading(false) })
      .catch(err => {
        setError(
          `Could not load car_data.json: ${String(err)}.\n` +
          `Run scripts/assign_rarity.py to generate web/public/car_data.json`
        )
        setLoading(false)
      })
  }, [])

  return (
    <CarDataContext.Provider value={{ carData, loading, error }}>
      {children}
    </CarDataContext.Provider>
  )
}
