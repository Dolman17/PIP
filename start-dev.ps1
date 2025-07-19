# Temporarily allow scripts in this PowerShell session
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Set Flask environment variables
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"  # enables debug mode and auto-reload

# Start the Flask development server
flask run
