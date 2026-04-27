import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  Camera,
  Grid3X3,
  Trophy,
  BarChart2,
  User,
  type LucideIcon,
} from 'lucide-react'

const NAV_ITEMS = [
  { to: '/',           label: 'Home',       Icon: LayoutDashboard },
  { to: '/spot',       label: 'Spot',       Icon: Camera          },
  { to: '/collection', label: 'Collection', Icon: Grid3X3         },
  { to: '/challenges', label: 'Challenges', Icon: Trophy          },
  { to: '/leaderboard',label: 'Ranks',      Icon: BarChart2       },
  { to: '/profile',    label: 'Profile',    Icon: User            },
] as const

function NavItem({ to, label, Icon }: { to: string; label: string; Icon: LucideIcon }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `flex flex-col items-center gap-0.5 px-2 py-2 rounded-xl transition-colors
         md:flex-row md:gap-2 md:px-3 md:py-2
         ${isActive
           ? 'text-blue-400'
           : 'text-zinc-500 hover:text-zinc-300'
         }`
      }
    >
      <Icon size={20} />
      <span className="text-[10px] md:text-sm font-medium">{label}</span>
    </NavLink>
  )
}

export function Layout() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col">
      {/* Top bar — desktop */}
      <header className="hidden md:flex items-center justify-between px-6 py-3 border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-30">
        <span className="text-xl font-bold tracking-tight text-white">
          Car<span className="text-blue-400">dex</span>
        </span>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map(item => (
            <NavItem key={item.to} {...item} />
          ))}
        </nav>
      </header>

      {/* Page content */}
      <main className="flex-1 pb-20 md:pb-0">
        <Outlet />
      </main>

      {/* Bottom bar — mobile */}
      <nav className="fixed bottom-0 inset-x-0 z-30 flex justify-around items-center
                      bg-zinc-900/95 backdrop-blur border-t border-zinc-800
                      px-2 py-2 safe-area-inset-bottom md:hidden">
        {NAV_ITEMS.map(item => (
          <NavItem key={item.to} {...item} />
        ))}
      </nav>
    </div>
  )
}
