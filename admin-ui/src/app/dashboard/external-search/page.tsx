/**
 * External Search Management Page
 * 
 * This page provides a comprehensive interface for managing MCP (Model Context Protocol)
 * external search providers, configuration, and performance monitoring.
 */

'use client';

import React from 'react';
import PageContainer from '@/components/layout/page-container';
import { Breadcrumbs } from '@/components/breadcrumbs';
import { ExternalSearchLayout } from '@/features/external-search/components/external-search-layout';

export default function ExternalSearchPage() {
  const breadcrumbItems = [
    { title: 'Dashboard', href: '/dashboard' },
    { title: 'External Search', href: '/dashboard/external-search' }
  ];

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-3xl font-bold tracking-tight">External Search</h1>
            <p className="text-muted-foreground">
              Manage external search providers and enhance search results with web content
            </p>
          </div>
        </div>
        
        <Breadcrumbs />
        
        <ExternalSearchLayout />
      </div>
    </PageContainer>
  );
}