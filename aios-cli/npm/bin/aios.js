#!/usr/bin/env node

const { spawnSync } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

const platform = os.platform();
const exeName = platform === 'win32' ? 'aios-cli.exe' : 'aios-cli';
const exePath = path.join(__dirname, exeName);

if (!fs.existsSync(exePath)) {
  console.error(`Error: AIOS CLI executable not found at ${exePath}`);
  console.error('The installation may have failed to download the binary.');
  process.exit(1);
}

const args = process.argv.slice(2);

const result = spawnSync(exePath, args, {
  stdio: 'inherit',
  env: process.env
});

if (result.error) {
  console.error('Failed to start AIOS CLI process:', result.error.message);
  process.exit(1);
}

process.exit(result.status !== null ? result.status : 1);
