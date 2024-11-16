#!/bin/bash

# Project name
PROJECT_NAME="thought-collector-agent"

# Create directory structure
mkdir -p api lib

# Create empty Python files
touch api/__init__.py
touch api/sms_handler.py
touch api/transcription.py
touch api/chat.py
touch lib/__init__.py
touch lib/database.py
touch lib/openai_client.py
touch lib/twilio_client.py

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Create requirements.txt with updated versions
cat > requirements.txt << 'EOL'
python-dotenv==1.0.0
openai==1.12.0
twilio==9.3.6
supabase==2.3.1
pinecone-client==3.0.2
python-multipart==0.0.9
EOL

# Install requirements
pip install -r requirements.txt

# Create .env.example
cat > .env.example << 'EOL'
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_number

# OpenAI Configuration
OPENAI_API_KEY=your_openai_key

# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=your_pinecone_environment
EOL

# Copy .env.example to .env
cp .env.example .env

# Initialize git repository
git init

# Create .gitignore
cat > .gitignore << 'EOL'
# Environment variables
.env
!.env.example

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
EOL

# Pinecone Setup
pythonscripts/init_pinecone.py

echo "Project setup complete! Don't forget to:"
echo "1. Edit .env with your actual credentials"
echo "2. Make sure you're in the virtual environment (should be activated already"