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

  // Generate dates_index.json dynamically for Vercel
  const files = fs.readdirSync(destDataDir).filter(f => f.startsWith('universal_predictions_') && f.endsWith('.json'));
  const dates = [];
  
  for (const file of files) {
    const dateStr = file.replace('universal_predictions_', '').replace('.json', '');
    const content = JSON.parse(fs.readFileSync(path.join(destDataDir, file), 'utf-8'));
    
    let scored_count = 0;
    if (content.predictions) {
      scored_count = content.predictions.filter(p => p.actual_result != null).length;
    }
    
    dates.push({
      date: dateStr,
      total: content.total_predictions || 0,
      graded: content.grade_summary != null,
      graded_count: scored_count,
      grade_summary: content.grade_summary || null
    });
  }

  // Sort descending by date
  dates.sort((a, b) => b.date.localeCompare(a.date));

  fs.writeFileSync(path.join(destDataDir, 'dates_index.json'), JSON.stringify({ dates }, null, 2));
  console.log('✅ Generated dates_index.json dynamically.');
  
  console.log('✅ Synchronized all data files from root successfully.');
} catch (error) {
  console.error('❌ Failed to synchronize data:', error);
  process.exit(1);
}
