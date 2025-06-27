import { NavItem } from '@/types';

//Info: Navigation items for Docaiche Admin Interface
export const navItems: NavItem[] = [
  {
    title: 'Overview',
    url: '/dashboard/overview',
    icon: 'dashboard',
    isActive: false,
    shortcut: ['d', 'o'],
    items: []
  },
  {
    title: 'System Health',
    url: '/dashboard/health',
    icon: 'heartHandshake',
    shortcut: ['h', 'h'],
    isActive: false,
    items: []
  },
  {
    title: 'Configuration',
    url: '#',
    icon: 'settings',
    isActive: true,
    shortcut: ['c', 'c'],
    items: [
      {
        title: 'AI Providers',
        url: '/dashboard/config/providers',
        icon: 'bot',
        shortcut: ['c', 'p']
      },
      {
        title: 'System Settings',
        url: '/dashboard/config/system',
        icon: 'settings2',
        shortcut: ['c', 's']
      },
      {
        title: 'Cache Management',
        url: '/dashboard/config/cache',
        icon: 'database',
        shortcut: ['c', 'm']
      }
    ]
  },
  {
    title: 'Content Management',
    url: '#',
    icon: 'fileText',
    isActive: false,
    shortcut: ['c', 'o'],
    items: [
      {
        title: 'Content Search',
        url: '/dashboard/content/search',
        icon: 'search',
        shortcut: ['c', 'r']
      },
      {
        title: 'Collections',
        url: '/dashboard/content/collections',
        icon: 'folder',
        shortcut: ['c', 'l']
      },
      {
        title: 'Upload Content',
        url: '/dashboard/content/upload',
        icon: 'upload',
        shortcut: ['c', 'u']
      }
    ]
  },
  {
    title: 'Analytics',
    url: '/dashboard/analytics',
    icon: 'barChart',
    shortcut: ['a', 'a'],
    isActive: false,
    items: []
  }
];

