'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Key,
  Database,
  Layers,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Shield,
} from 'lucide-react'
import { logoutAction } from '@/app/actions/auth'

interface NavItem {
  name: string
  href: string
  icon: typeof Key
  badge?: string
}

const navItems: NavItem[] = [
  { name: 'Tokens & Credentials', href: '/', icon: Key },
  { name: 'Tenants (Organizations)', href: '/tenants', icon: Database },
  { name: 'Projects', href: '/projects', icon: Layers },
]

export function AdminSidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/' || pathname === '/tokens'
    }
    return pathname.startsWith(href)
  }

  return (
    <aside
      className={`relative flex flex-col border-r border-border bg-card/80 backdrop-blur transition-all duration-300 z-20 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-border">
        {!collapsed && (
          <div className="flex items-center space-x-2.5 overflow-hidden">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600/10 border border-blue-500/20 text-blue-400">
              <Shield className="h-4 w-4" />
            </div>
            <div className="flex flex-col truncate">
              <span className="font-bold text-xs tracking-tight text-white truncate">
                Harness Memory
              </span>
              <span className="text-[10px] text-gray-400 font-medium">Admin Console</span>
            </div>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition mx-auto"
          title={collapsed ? 'Expand menu' : 'Collapse menu'}
          aria-label={collapsed ? 'Expand menu' : 'Collapse menu'}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 space-y-1.5 p-3">
        {navItems.map((item) => {
          const active = isActive(item.href)
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                active
                  ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
              title={collapsed ? item.name : undefined}
            >
              <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-blue-400' : 'text-gray-400'}`} />
              {!collapsed && <span className="truncate">{item.name}</span>}
            </Link>
          )
        })}
      </nav>

      {/* Footer / Logout */}
      <div className="p-3 border-t border-border">
        <form action={logoutAction}>
          <button
            type="submit"
            className="flex w-full items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition"
            title={collapsed ? 'Sign Out' : undefined}
          >
            <LogOut className="h-4 w-4 shrink-0" />
            {!collapsed && <span>Sign Out</span>}
          </button>
        </form>
      </div>
    </aside>
  )
}
