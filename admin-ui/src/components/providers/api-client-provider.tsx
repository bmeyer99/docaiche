'use client'

import React, { useEffect, useMemo } from 'react'
import { DocaicheApiClient } from '@/lib/utils/api-client'
import { ApiClientContext } from '@/lib/hooks/use-api-client'
import { useToast } from '@/hooks/use-toast'

interface ApiClientProviderProps {
  children: React.ReactNode
}

export function ApiClientProvider({ children }: ApiClientProviderProps) {
  const { error, warning, info, dismiss } = useToast()
  const client = useMemo(() => new DocaicheApiClient(), [])

  useEffect(() => {
    // Set up toast callbacks for the API client
    client.setToastCallbacks({
      showToast: (message: string, type: 'info' | 'error' | 'warning', options?: { id?: string; duration?: number }) => {
        const toastId = options?.id || `${type}-${Date.now()}`
        const duration = options?.duration || (type === 'warning' ? 35000 : 5000)
        
        if (type === 'error') {
          return error('Connection Error', message, { duration, id: toastId })
        } else if (type === 'warning') {
          return warning('Connection Issue', message, { duration, id: toastId })
        } else {
          return info('Connection Status', message, { duration, id: toastId })
        }
      },
      updateToast: (id: string, message: string, type: 'info' | 'error' | 'warning') => {
        // Sonner supports updating toasts by ID!
        const title = type === 'error' ? 'Connection Error' : 
                     type === 'warning' ? 'Connection Issue' : 
                     'Connection Status'
        
        if (type === 'error') {
          return error(title, message, { id })
        } else if (type === 'warning') {
          return warning(title, message, { id })
        } else {
          return info(title, message, { id })
        }
      },
      dismissToast: (id: string) => {
        // Sonner supports dismissing toasts by ID
        dismiss(id)
      }
    })
  }, [client, error, warning, info, dismiss])

  return (
    <ApiClientContext.Provider value={client}>
      {children}
    </ApiClientContext.Provider>
  )
}