// setup.js - Configuration setup only (no shebang needed)
import fs from 'fs';
import path from 'path';
import readline from 'readline';

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const CONFIG_PATH = path.join(process.env.HOME, '.hakken', 'config.json');

function askQuestion(query) {
  return new Promise(resolve => rl.question(query, resolve));
}

async function setup() {
  console.log('🤖 Hakken Setup\n');
  
  const config = {
    openaiApiKey: await askQuestion('OpenAI API Key: '),
    model: await askQuestion('Model (default: gpt-4): ') || 'gpt-4',
    tavilyApiKey: await askQuestion('Tavily API Key (optional): ') || ''
  };
  
  // Create config directory
  const configDir = path.dirname(CONFIG_PATH);
  if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
  }
  
  // Save config
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
  
  console.log('\n✅ Configuration saved to', CONFIG_PATH);
  
  rl.close();
}

setup();