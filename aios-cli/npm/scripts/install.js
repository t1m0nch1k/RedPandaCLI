const fs = require('fs');
const path = require('path');
const os = require('os');
const axios = require('axios');
const extractZip = require('extract-zip');
const tar = require('tar');
const { promisify } = require('util');
const stream = require('stream');

const pipeline = promisify(stream.pipeline);

const REPO = 't1m0nch1k/RedPandaCLI';
const VERSION = 'v0.1.0'; // Will be dynamically matched or hardcoded for the npm version

async function downloadBinary() {
  const platform = os.platform();
  const arch = os.arch();

  let assetName = '';
  if (platform === 'win32') {
    assetName = `aios-cli-windows-amd64.zip`;
  } else if (platform === 'darwin') {
    assetName = arch === 'arm64' ? `aios-cli-darwin-arm64.tar.gz` : `aios-cli-darwin-amd64.tar.gz`;
  } else if (platform === 'linux') {
    assetName = `aios-cli-linux-amd64.tar.gz`;
  } else {
    console.error(`Unsupported platform: ${platform}`);
    process.exit(1);
  }

  const url = `https://github.com/${REPO}/releases/download/${VERSION}/${assetName}`;
  const binDir = path.join(__dirname, '..', 'bin');
  
  if (!fs.existsSync(binDir)) {
    fs.mkdirSync(binDir, { recursive: true });
  }

  const archivePath = path.join(binDir, assetName);

  console.log(`Downloading AIOS CLI for ${platform} ${arch}...`);
  console.log(`From: ${url}`);

  try {
    const response = await axios({
      method: 'GET',
      url: url,
      responseType: 'stream'
    });

    await pipeline(response.data, fs.createWriteStream(archivePath));
    console.log('Download complete. Extracting...');

    if (assetName.endsWith('.zip')) {
      await extractZip(archivePath, { dir: binDir });
    } else {
      await tar.x({
        file: archivePath,
        C: binDir
      });
    }

    // Cleanup archive
    fs.unlinkSync(archivePath);

    // Make executable on unix
    if (platform !== 'win32') {
      const exePath = path.join(binDir, 'aios');
      if (fs.existsSync(exePath)) {
        fs.chmodSync(exePath, '755');
      }
    }

    console.log('Installation complete!');
  } catch (error) {
    console.error('Failed to download or extract binary:', error.message);
    if (error.response && error.response.status === 404) {
      console.error(`Release ${VERSION} or asset ${assetName} not found.`);
      console.log('If you are developing locally, you can build the binary yourself using scripts/build_binaries.py');
    }
    // We don't want to exit 1 to break npm install if they are just doing local dev.
    // In production you might process.exit(1) here.
  }
}

downloadBinary();
