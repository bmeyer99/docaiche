module.exports = {
  preset: 'jest-puppeteer',
  testMatch: ['**/*.e2e.test.js'],
  testTimeout: 30000,
  setupFilesAfterEnv: ['<rootDir>/jest-puppeteer.config.js'],
  testEnvironment: 'jest-environment-puppeteer',
  transform: {
    '^.+\\.jsx?$': 'babel-jest',
  },
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  }
};