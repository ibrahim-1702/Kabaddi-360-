@echo off
echo ======================================================================
echo Kabaddi Ghost Trainer - Frontend Setup  
echo ======================================================================
echo.

echo Step 1: Installing backend dependencies...
cd backend
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo ✓ Dependencies installed
echo.

echo Step 2: Initializing database with "The Bonus" expert pose...
python init_database.py
if errorlevel 1 (
    echo ERROR: Database initialization failed
    pause
    exit /b 1
)
echo ✓ Database initialized
echo.

echo Step 3: Starting Flask backend server...
echo Server will start at http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ======================================================================
python app.py
