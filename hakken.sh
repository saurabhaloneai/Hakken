#!/bin/bash

# Navigate to Hakken directory
HAKKEN_DIR="/Users/saurabh/Hakken"

# Launch the React/Ink UI which bridges to Python
cd "$HAKKEN_DIR"
npx tsx terminal_ui/src/index.tsx "$@"
