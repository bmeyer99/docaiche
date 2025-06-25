import React from "react";
import { Card } from "../ui/Card";

export interface LLMProvidersTabProps {
  className?: string;
}

export const LLMProvidersTab: React.FC<LLMProvidersTabProps> = ({ className }) => (
  <Card className={className}>
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-text-primary mb-2">LLM Providers Configuration</h3>
        <p className="text-text-secondary mb-4">
          Configure language model providers for text generation and embedding services. 
          Set up API connections to Ollama, OpenAI, or custom LLM endpoints.
        </p>
      </div>
      <div className="bg-surface-secondary p-4 rounded-md">
        <h4 className="font-medium text-text-primary mb-2">Available Providers:</h4>
        <ul className="text-sm text-text-secondary space-y-1">
          <li>• <strong>Ollama:</strong> Local LLM server for self-hosted models</li>
          <li>• <strong>OpenAI:</strong> GPT-3.5, GPT-4, and embedding models</li>
          <li>• <strong>Custom:</strong> Configure any OpenAI-compatible API endpoint</li>
        </ul>
      </div>
    </div>
  </Card>
);