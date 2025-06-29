import { NavItem } from '@/types';

//Info: Simplified single-level navigation for Docaiche Admin Interface
export const navItems: NavItem[] = [
  {
    title: 'Dashboard',
    url: '/dashboard/analytics',
    icon: 'barChart',
    shortcut: ['d', 'a'],
    isActive: false,
    items: []
  },
  {
    title: 'AI Providers',
    url: '/dashboard/providers',
    icon: 'bot',
    isActive: false,
    shortcut: ['p', 'r'],
    items: []
  },
  {
    title: 'Documents',
    url: '/dashboard/documents',
    icon: 'fileText',
    isActive: false,
    shortcut: ['d', 'o'],
    items: []
  }
];

