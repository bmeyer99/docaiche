type LogLevel = 'error' | 'warn' | 'info' | 'debug';
type LogCategory = 'api' | 'user' | 'state' | 'validation' | 'performance' | 'error';

interface LogOptions {
  category?: LogCategory;
  redactKeys?: string[];
  [key: string]: any;
}

const REDACTED = '[REDACTED]';

function redactSensitive(obj: any, keys: string[]): any {
  if (!obj || typeof obj !== 'object') return obj;
  const clone = Array.isArray(obj) ? [...obj] : { ...obj };
  for (const key in clone) {
    if (keys.includes(key)) {
      clone[key] = REDACTED;
    } else if (typeof clone[key] === 'object') {
      clone[key] = redactSensitive(clone[key], keys);
    }
  }
  return clone;
}

function formatMessage(level: LogLevel, category: LogCategory, message: string, meta?: any) {
  const base = `[${level.toUpperCase()}][${category}] ${message}`;
  if (meta) {
    return `${base} | ${JSON.stringify(meta)}`;
  }
  return base;
}

function isProduction() {
  return process.env.NODE_ENV === 'production';
}

export class Logger {
  static log(level: LogLevel, message: string, options: LogOptions = {}) {
    const { category, redactKeys = [], ...meta } = options;
    if (!category) {
      throw new Error('Logger: category is required in LogOptions');
    }
    const safeMeta = redactSensitive(meta, redactKeys);

    if (isProduction()) {
      // Structured JSON for production
      const logObj = {
        timestamp: new Date().toISOString(),
        level,
        category,
        message,
        ...safeMeta,
      };
      // eslint-disable-next-line no-console
      console.log(JSON.stringify(logObj));
    } else {
      // Human-readable for development
      const formatted = formatMessage(level, category, message, safeMeta);
      // eslint-disable-next-line no-console
      switch (level) {
        case 'error':
          console.error(formatted);
          break;
        case 'warn':
          console.warn(formatted);
          break;
        case 'info':
          console.info(formatted);
          break;
        default:
          console.debug(formatted);
      }
    }
  }

  static error(message: string, options: LogOptions = {}) {
    Logger.log('error', message, options);
  }

  static warn(message: string, options: LogOptions = {}) {
    Logger.log('warn', message, options);
  }

  static info(message: string, options: LogOptions = {}) {
    Logger.log('info', message, options);
  }

  static debug(message: string, options: LogOptions = {}) {
    Logger.log('debug', message, options);
  }
}