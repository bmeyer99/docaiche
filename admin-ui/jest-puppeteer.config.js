module.exports = {
  launch: {
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    slowMo: process.env.SLOWMO ? parseInt(process.env.SLOWMO) : 0,
  },
  browserContext: 'incognito',
  server: {
    command: 'npm run dev',
    port: 3000,
    launchTimeout: 30000,
    debug: true,
  },
};