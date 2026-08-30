#!/bin/bash
echo "Initializing Django Chatbot Project..."

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Making migrations..."
cd chatbot_project
python manage.py makemigrations
python manage.py migrate

echo "Creating superuser..."
python manage.py createsuperuser

echo "Starting development server..."
python manage.py runserver

echo "Project initialized successfully!"