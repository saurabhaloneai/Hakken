#!/bin/bash
echo "Building Hakken..."

# Create dist directory
mkdir -p dist/src

# Compile TypeScript files
echo "Compiling TypeScript..."
npx tsc src/ui.tsx --outDir dist/src --target es2020 --module esnext --moduleResolution node --jsx react --allowSyntheticDefaultImports --esModuleInterop --skipLibCheck

# Copy JS files
cp src/index.js dist/src/
cp src/setup.js dist/src/

# Copy Python files
cp src/bridge.py dist/src/
cp -r src/python dist/src/

# Make index.js executable
chmod +x dist/src/index.js

echo "✅ Build complete!"
echo "Files created:"
ls -la dist/src/
