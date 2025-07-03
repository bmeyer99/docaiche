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
    title: 'Search Config',
    url: '/dashboard/search-config',
    icon: 'settings',
    isActive: false,
    shortcut: ['s', 'c'],
    items: []
  },
  {
    title: 'External Search',
    url: '/dashboard/external-search',
    icon: 'search',
    isActive: false,
    shortcut: ['e', 's'],
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
    title: 'Logs',
    url: '/dashboard/logs',
    icon: 'activity',
    isActive: false,
    shortcut: ['l', 'o'],
    items: []
  },
  {
    title: 'Monitoring',
    url: '/dashboard/monitoring',
    icon: 'barChart',
    isActive: false,
    shortcut: ['m', 'o'],
    items: []
  },
  {
    title: 'Grafana Dashboards',
    url: '/dashboard/grafana',
    icon: 'monitor',
    isActive: false,
    shortcut: ['g', 'd'],
    items: []
  }
];

