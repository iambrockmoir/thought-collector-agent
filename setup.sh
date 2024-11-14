# Create root level files
touch .env.example .gitignore README.md requirements.txt

# Create src directory and its files
mkdir -p src
touch src/__init__.py src/main.py src/config.py

# Create services directory and its files
mkdir -p src/services
touch src/services/__init__.py
touch src/services/audio_service.py
touch src/services/chat_service.py
touch src/services/firebase_service.py
touch src/services/pinecone_service.py

# Create handlers directory and its files
mkdir -p src/handlers
touch src/handlers/__init__.py
touch src/handlers/sms_handler.py
touch src/handlers/thought_handler.py

# Create utils directory and its files
mkdir -p src/utils
touch src/utils/__init__.py
touch src/utils/helpers.py

# Create tests directory and its files
mkdir -p tests
touch tests/__init__.py
touch tests/test_handlers.py

# Make it a git repository
git init

echo "Project structure created successfully!"