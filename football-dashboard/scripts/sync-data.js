import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Root directory is ncaa-api
const rootDir = path.resolve(__dirname, '..', '..');
const sports = ['football', 'basketball'];

console.log('Starting multi-sport data synchronization for Vercel build...');

for (const sport of sports) {
  const sourceDataDir = path.join(rootDir, 'data', sport);
  const destDataDir = path.join(__dirname, '..', 'public', 'data', sport);

  console.log(`\n--- Synchronizing ${sport} ---`);
  console.log(`Source: ${sourceDataDir}`);
  console.log(`Destination: ${destDataDir}`);

  try {
    // Ensure the destination exists
    fs.mkdirSync(destDataDir, { recursive: true });

    if (!fs.existsSync(sourceDataDir)) {
      console.log(`⚠️ Source for ${sport} does not exist, skipping...`);
      continue;
    }

    // Copy everything symmetrically (Node 16.7+)
    if (fs.cpSync) {
      fs.cpSync(sourceDataDir, destDataDir, { recursive: true });
    }

    // Generate dates_index.json dynamically
    const files = fs.readdirSync(destDataDir).filter(f => f.startsWith('universal_predictions_') && f.endsWith('.json'));
    const dates = [];
    
    for (const file of files) {
      const dateStr = file.replace('universal_predictions_', '').replace('.json', '');
      try {
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
      } catch (parseError) {
        console.warn(`⚠️ Skipping ${file} due to JSON parse error: ${parseError.message}`);
      }
    }

    // Sort descending by date
    dates.sort((a, b) => b.date.localeCompare(a.date));

    fs.writeFileSync(path.join(destDataDir, 'dates_index.json'), JSON.stringify({ dates }, null, 2));
    console.log(`✅ Generated ${sport} dates_index.json dynamically.`);
    
  } catch (error) {
    console.error(`❌ Failed to synchronize ${sport} data:`, error);
    process.exit(1);
  }
}

console.log('\n✅ All sports synchronized successfully.');
