#!/usr/bin/env node
// src/index.js - Main entry point
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CONFIG_PATH = path.join(process.env.HOME, '.hakken', 'config.json');

// Check if config exists
if (!fs.existsSync(CONFIG_PATH)) {
  console.log('⚠️  No configuration found. Running setup...\n');
  // Run setup
  const setupPath = path.join(__dirname, 'setup.js');
  const setup = spawn('node', [setupPath], { stdio: 'inherit' });
  setup.on('exit', (code) => {
    if (code === 0) {
      console.log('\n✅ Setup complete! Run "hakken" again to start.');
    }
    process.exit(code);
  });
} else {
  // Load config and start the agent
  const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  
  // Set environment variables
  process.env.OPENAI_API_KEY = config.openaiApiKey;
  process.env.OPENAI_MODEL = config.model;
  process.env.TAVILY_API_KEY = config.tavilyApiKey || '';
  
  // Import and start the UI
  import('./ui.js').then(module => {
    // Your UI module should export a default function
    if (module.default) {
      module.default();
    }
  }).catch(err => {
    console.error('Error starting Hakken:', err);
    process.exit(1);
  });
}