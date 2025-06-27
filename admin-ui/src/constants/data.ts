import { NavItem } from '@/types';

export type Product = {
  photo_url: string;
  name: string;
  description: string;
  created_at: string;
  price: number;
  id: number;
  category: string;
  updated_at: string;
};

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

export interface SaleUser {
  id: number;
  name: string;
  email: string;
  amount: string;
  image: string;
  initials: string;
}

export const recentSalesData: SaleUser[] = [
  {
    id: 1,
    name: 'Olivia Martin',
    email: 'olivia.martin@email.com',
    amount: '+$1,999.00',
    image: 'https://api.slingacademy.com/public/sample-users/1.png',
    initials: 'OM'
  },
  {
    id: 2,
    name: 'Jackson Lee',
    email: 'jackson.lee@email.com',
    amount: '+$39.00',
    image: 'https://api.slingacademy.com/public/sample-users/2.png',
    initials: 'JL'
  },
  {
    id: 3,
    name: 'Isabella Nguyen',
    email: 'isabella.nguyen@email.com',
    amount: '+$299.00',
    image: 'https://api.slingacademy.com/public/sample-users/3.png',
    initials: 'IN'
  },
  {
    id: 4,
    name: 'William Kim',
    email: 'will@email.com',
    amount: '+$99.00',
    image: 'https://api.slingacademy.com/public/sample-users/4.png',
    initials: 'WK'
  },
  {
    id: 5,
    name: 'Sofia Davis',
    email: 'sofia.davis@email.com',
    amount: '+$39.00',
    image: 'https://api.slingacademy.com/public/sample-users/5.png',
    initials: 'SD'
  }
];
