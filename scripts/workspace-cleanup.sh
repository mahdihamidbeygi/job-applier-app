#!/bin/bash

echo "🧹 Workspace Cleanup Script"
echo "=========================="

# Clean Next.js build cache
if [ -d ".next" ]; then
    echo "Cleaning Next.js build cache..."
    rm -rf .next
    echo "✅ Next.js cache cleaned"
fi

# Clean node_modules and reinstall if requested
read -p "Do you want to clean and reinstall node_modules? (y/N) " clean_modules
if [[ $clean_modules =~ ^[Yy]$ ]]; then
    echo "Cleaning node_modules..."
    rm -rf node_modules
    rm -f package-lock.json
    echo "Installing dependencies..."
    npm install
    echo "✅ Dependencies reinstalled"
fi

# Clean git objects and optimize repo
echo "Optimizing git repository..."
git gc --aggressive --prune=now
echo "✅ Git repository optimized"

# Remove any temp files
echo "Removing temporary files..."
find . -type f -name "*.tmp" -delete
find . -type f -name "*.log" -delete
echo "✅ Temporary files removed"

# Create documentation directory if it doesn't exist
if [ ! -d "docs" ]; then
    echo "Creating documentation directory..."
    mkdir -p docs/chat-summaries
    echo "✅ Documentation directory created"
fi

echo "
=========================="
echo "✨ Cleanup complete!"
echo "Tips for better performance:"
echo "1. Start new conversations for new topics"
echo "2. Save important chat content to docs/chat-summaries"
echo "3. Close unused editor tabs"
echo "4. Run this script periodically" 