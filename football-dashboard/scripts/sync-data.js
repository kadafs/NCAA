import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Root directory is ncaa-api
const rootDir = path.resolve(__dirname, '..', '..');
const sourceDataDir = path.join(rootDir, 'data', 'football');
const destDataDir = path.join(__dirname, '..', 'public', 'data', 'football');

console.log('Starting data synchronization for Vercel build...');
console.log(`Source: ${sourceDataDir}`);
console.log(`Destination: ${destDataDir}`);

try {
  // Ensure the destination exists
  fs.mkdirSync(destDataDir, { recursive: true });

  // Copy everything symmetrically (Node 16.7+)
  if (fs.cpSync) {
    fs.cpSync(sourceDataDir, destDataDir, { recursive: true });
  } else {
    // Fallback for older Node versions (though Vercel uses 18+)
    console.log("cpSync not available, skipping copy (requires Node 16.7+)");
  }

  console.log('✅ Synchronized all data files from root successfully.');
} catch (error) {
  console.error('❌ Failed to synchronize data:', error);
  process.exit(1);
}
