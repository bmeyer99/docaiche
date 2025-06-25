import React from "react";
import { Card } from "../ui/Card";

export interface AdvancedSettingsTabProps {
  className?: string;
}

export const AdvancedSettingsTab: React.FC<AdvancedSettingsTabProps> = ({ className }) => (
  <Card className={className}>
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-text-primary mb-2">Advanced Settings</h3>
        <p className="text-text-secondary mb-4">
          Configure advanced system parameters, experimental features, and debugging options. 
          These settings require careful consideration and may impact system stability.
        </p>
      </div>
      <div className="bg-surface-secondary p-4 rounded-md">
        <h4 className="font-medium text-text-primary mb-2">Advanced Options:</h4>
        <ul className="text-sm text-text-secondary space-y-1">
          <li>• <strong>Content Processing:</strong> Chunking strategies and enrichment settings</li>
          <li>• <strong>Search Algorithms:</strong> Ranking and relevance scoring parameters</li>
          <li>• <strong>Debug Mode:</strong> Enhanced logging and development features</li>
          <li>• <strong>Experimental:</strong> Beta features and performance optimizations</li>
        </ul>
      </div>
    </div>
  </Card>
);