import React from 'react';
import { SidebarTrigger } from '../ui/sidebar';
import { Separator } from '../ui/separator';
import { Breadcrumbs } from '../breadcrumbs';
import SearchInput from '../search-input';
import { ThemeSelector } from '../theme-selector';
import { ModeToggle } from './ThemeToggle/theme-toggle';
import { Badge } from '../ui/badge';
import { ConnectionStatusIndicator } from '@/components/providers/api-health-provider';

export default function Header() {
  return (
    <header className='flex h-16 shrink-0 items-center justify-between gap-2 transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12'>
      <div className='flex items-center gap-2 px-4'>
        <SidebarTrigger className='-ml-1' />
        <Separator orientation='vertical' className='mr-2 h-4' />
        <Breadcrumbs />
      </div>

      <div className='flex items-center gap-2 px-4'>
        <div className='hidden md:flex'>
          <SearchInput />
        </div>
        <ConnectionStatusIndicator />
        <Separator orientation='vertical' className='h-4' />
        <Badge variant="secondary" className="text-xs">
          Lab Environment
        </Badge>
        <ModeToggle />
        <ThemeSelector />
      </div>
    </header>
  );
}
