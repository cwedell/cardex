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
  { to: '/',            label: 'Home',       Icon: LayoutDashboard },
  { to: '/spot',        label: 'Spot',       Icon: Camera          },
  { to: '/collection',  label: 'Collection', Icon: Grid3X3         },
  { to: '/challenges',  label: 'Challenges', Icon: Trophy          },
  { to: '/leaderboard', label: 'Ranks',      Icon: BarChart2       },
  { to: '/profile',     label: 'Profile',    Icon: User            },
] as const

function DesktopNavLink({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `font-display font-bold text-[10px] tracking-[2.5px] uppercase px-3.5 transition-colors
         ${isActive ? 'text-rally-red' : 'text-rally-muted hover:text-rally-cream'}`
      }
    >
      {label}
    </NavLink>
  )
}

function MobileNavLink({ to, label, Icon }: { to: string; label: string; Icon: LucideIcon }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `flex flex-col items-center gap-0.5 px-2 py-2 transition-colors
         ${isActive ? 'text-rally-red' : 'text-rally-muted hover:text-rally-cream'}`
      }
    >
      <Icon size={20} />
      <span className="text-[9px] font-display font-bold tracking-[2px] uppercase">{label}</span>
    </NavLink>
  )
}

export function Layout() {
  return (
    <div className="min-h-screen bg-rally-cream text-rally-dark flex flex-col">
      {/* Top bar */}
      <header className="sticky top-0 z-30">
        <nav className="bg-rally-dark flex items-center px-8 h-[52px]">
          <span className="font-display font-black text-[18px] text-rally-cream tracking-[6px] uppercase mr-auto">
            CARDEX
          </span>
          <div className="flex items-center">
            {NAV_ITEMS.map(item => (
              <DesktopNavLink key={item.to} to={item.to} label={item.label} />
            ))}
          </div>
        </nav>
        <div className="h-[2px] bg-rally-red" />
        <div className="h-[1px] bg-rally-gold mt-[2px]" />
      </header>

      {/* Page content */}
      <main className="flex-1 pb-20 md:pb-0">
        <Outlet />
      </main>

      {/* Bottom bar — mobile only */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-30 flex justify-around items-center
                      bg-rally-dark border-t-2 border-rally-red
                      px-2 py-2 safe-area-inset-bottom">
        {NAV_ITEMS.map(item => (
          <MobileNavLink key={item.to} to={item.to} label={item.label} Icon={item.Icon} />
        ))}
      </nav>
    </div>
  )
}
