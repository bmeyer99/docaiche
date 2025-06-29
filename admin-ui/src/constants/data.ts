import { NavItem } from '@/types';

//Info: Simplified single-level navigation for Docaiche Admin Interface
export const navItems: NavItem[] = [
  {
    title: 'AI Providers',
    url: '/dashboard/providers',
    icon: 'bot',
    isActive: false,
    shortcut: ['p', 'r'],
    items: []
  },
  {
    title: 'Analytics',
    url: '/dashboard/analytics',
    icon: 'barChart',
    shortcut: ['a', 'n'],
    isActive: false,
    items: []
  },
  {
    title: 'Documents',
    url: '/dashboard/documents',
    icon: 'fileText',
    isActive: false,
    shortcut: ['d', 'o'],
    items: []
  },
  {
    title: 'System Health',
    url: '/dashboard/health',
    icon: 'activity',
    shortcut: ['h', 'e'],
    isActive: false,
    items: []
  }
];

