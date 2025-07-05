// Mock for lucide-react icons
const React = require('react');

const createMockIcon = (name) => {
  return React.forwardRef((props, ref) => {
    return React.createElement('div', {
      ...props,
      ref,
      'data-testid': `${name.toLowerCase()}-icon`
    }, name);
  });
};

module.exports = {
  Users: createMockIcon('Users'),
  Database: createMockIcon('Database'),
  Bot: createMockIcon('Bot'),
  Globe: createMockIcon('Globe'),
  HardDrive: createMockIcon('HardDrive'),
  BarChart3: createMockIcon('BarChart3'),
  Settings: createMockIcon('Settings'),
  Save: createMockIcon('Save'),
  X: createMockIcon('X'),
  Loader2: createMockIcon('Loader2'),
  AlertCircle: createMockIcon('AlertCircle'),
  AlertTriangle: createMockIcon('AlertTriangle'),
  Info: createMockIcon('Info'),
  CheckCircle: createMockIcon('CheckCircle'),
  ExternalLink: createMockIcon('ExternalLink'),
  Sparkles: createMockIcon('Sparkles'),
};