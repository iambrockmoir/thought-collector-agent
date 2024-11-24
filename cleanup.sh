#!/bin/bash

echo "Starting repository cleanup..."

mkdir -p docs
mkdir -p api/services

git rm -r --cached lib/ || true
git rm -r --cached app.py || true
git rm -r --cached __init__.py || true
git rm -r --cached pseudocode.py || true
git rm -r --cached project_specification.txt || true

rm -rf lib/
rm -f app.py
rm -f __init__.py

mv pseudocode.py docs/ || true
mv project_specification.txt docs/ || true

echo "Creating .gitignore entries for cleaned up files..."
cat >> .gitignore << EOL
lib/
app.py
__init__.py
EOL

echo "Committing changes..."
git add .
git commit -m "Repository cleanup: Remove unused files and reorganize structure"

echo "Cleanup complete! Please review changes before pushing." 