'use client';

import { navItems } from '@/constants/data';
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { useRouter } from 'next/navigation';
import { useState, useEffect, useMemo } from 'react';
import { useTheme } from 'next-themes';

interface CommandPaletteProps {
  children: React.ReactNode;
}

export default function CommandPalette({ children }: CommandPaletteProps) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const { setTheme } = useTheme();

  // Toggle command palette with Cmd+K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  // Generate navigation actions
  const navigationActions = useMemo(() => {
    return navItems.flatMap((navItem) => {
      const actions = [];

      // Add base action if it has a real URL
      if (navItem.url !== '#') {
        actions.push({
          id: `nav-${navItem.title.toLowerCase()}`,
          title: navItem.title,
          subtitle: `Go to ${navItem.title}`,
          section: 'Navigation',
          action: () => {
            router.push(navItem.url);
            setOpen(false);
          }
        });
      }

      // Add child actions
      if (navItem.items) {
        navItem.items.forEach(childItem => {
          actions.push({
            id: `nav-${childItem.title.toLowerCase()}`,
            title: childItem.title,
            subtitle: `Go to ${childItem.title}`,
            section: navItem.title,
            action: () => {
              router.push(childItem.url);
              setOpen(false);
            }
          });
        });
      }

      return actions;
    });
  }, [router]);

  // Theme actions
  const themeActions = [
    {
      id: 'theme-light',
      title: 'Light Theme',
      subtitle: 'Switch to light mode',
      section: 'Theme',
      action: () => {
        setTheme('light');
        setOpen(false);
      }
    },
    {
      id: 'theme-dark',
      title: 'Dark Theme',
      subtitle: 'Switch to dark mode',
      section: 'Theme',
      action: () => {
        setTheme('dark');
        setOpen(false);
      }
    },
    {
      id: 'theme-system',
      title: 'System Theme',
      subtitle: 'Use system preference',
      section: 'Theme',
      action: () => {
        setTheme('system');
        setOpen(false);
      }
    }
  ];

  const allActions = [...navigationActions, ...themeActions];

  // Group actions by section
  const groupedActions = allActions.reduce((acc, action) => {
    if (!acc[action.section]) {
      acc[action.section] = [];
    }
    acc[action.section].push(action);
    return acc;
  }, {} as Record<string, typeof allActions>);

  return (
    <>
      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder="Type a command or search..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          {Object.entries(groupedActions).map(([section, actions]) => (
            <CommandGroup key={section} heading={section}>
              {actions.map((action) => (
                <CommandItem
                  key={action.id}
                  onSelect={() => action.action()}
                  className="flex flex-col items-start"
                >
                  <div className="font-medium">{action.title}</div>
                  <div className="text-sm text-muted-foreground">{action.subtitle}</div>
                </CommandItem>
              ))}
            </CommandGroup>
          ))}
        </CommandList>
      </CommandDialog>
      {children}
    </>
  );
}