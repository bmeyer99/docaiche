'use client'

import React from 'react'
import { ProgressTrackerProps } from '../types'
import { cn } from '@/lib/utils'
import { Check } from 'lucide-react'

/**
 * ProgressTracker - Visual indicator of configuration progress
 * 
 * Shows the current step in the provider configuration flow and
 * allows navigation between completed steps.
 */
export function ProgressTracker({
  activeStep,
  completedSteps,
  onStepClick
}: ProgressTrackerProps) {
  const steps = [
    { id: 'select', label: 'Select Provider' },
    { id: 'configure', label: 'Configure' },
    { id: 'test', label: 'Test Connection' },
    { id: 'models', label: 'Choose Models' }
  ] as const
  
  return (
    <div className="flex items-center justify-between mb-8">
      {steps.map((step, index) => {
        const isActive = activeStep === step.id
        const isCompleted = completedSteps.has(step.id)
        const isClickable = isCompleted || isActive
        
        return (
          <React.Fragment key={step.id}>
            <div className="flex items-center">
              <button
                onClick={() => isClickable && onStepClick(step.id)}
                disabled={!isClickable}
                className={cn(
                  "flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all progress-step",
                  isActive && "border-primary bg-primary text-primary-foreground",
                  isCompleted && !isActive && "border-primary bg-background text-primary",
                  !isActive && !isCompleted && "border-muted-foreground text-muted-foreground",
                  isClickable && "cursor-pointer hover:shadow-md",
                  !isClickable && "cursor-not-allowed opacity-50"
                )}
              >
                {isCompleted ? (
                  <Check className="w-5 h-5" />
                ) : (
                  <span className="text-sm font-medium">{index + 1}</span>
                )}
              </button>
              <span className={cn(
                "ml-2 text-sm font-medium",
                isActive && "text-primary",
                isCompleted && !isActive && "text-primary",
                !isActive && !isCompleted && "text-muted-foreground"
              )}>
                {step.label}
              </span>
            </div>
            
            {/* Connector line */}
            {index < steps.length - 1 && (
              <div className={cn(
                "flex-1 h-0.5 mx-4 progress-connector",
                completedSteps.has(steps[index + 1].id) ? "bg-primary" : "bg-muted"
              )} />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}