#!/bin/bash

# Redirect all output to log file
exec 1> >(logger -s -t $(basename $0)) 2>&1

LOG_FILE="/var/log/eb-hooks.log"
APP_DIR="/var/app/current"
INSTANCE_DIR="$APP_DIR/instance"
UPLOADS_DIR="$APP_DIR/uploads"

# Error handling
set -e  # Exit on error
trap 'echo "Error on line $LINENO"' ERR

echo "Starting DB init at $(date)" | tee -a $LOG_FILE

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

# Create instance directory if it doesn't exist and set permissions
log_message "Creating instance directory..."
mkdir -p $INSTANCE_DIR
sudo chown webapp:webapp $INSTANCE_DIR
chmod 775 $INSTANCE_DIR

# Create uploads directory and set permissions
log_message "Creating uploads directory..."
mkdir -p $UPLOADS_DIR/teeth
sudo chown -R webapp:webapp $UPLOADS_DIR
chmod -R 775 $UPLOADS_DIR

# Initialize database
log_message "Initializing database..."
source /var/app/venv/*/bin/activate
cd $APP_DIR

# Try to initialize database with error handling
if ! python3 -c "from app import app, init_db; init_db()"; then
    log_message "ERROR: Failed to initialize database"
    exit 1
fi

# Set proper permissions for database file
DB_FILE="$INSTANCE_DIR/dental_clinic.db"
if [ -f "$DB_FILE" ]; then
    log_message "Database file created successfully at $DB_FILE"
    sudo chown webapp:webapp "$DB_FILE"
    sudo chmod 664 "$DB_FILE"
    
    # Verify permissions
    if [ ! -r "$DB_FILE" ] || [ ! -w "$DB_FILE" ]; then
        log_message "ERROR: Failed to set correct permissions on database file"
        exit 1
    fi
else
    log_message "ERROR: Database file not created at $DB_FILE"
    exit 1
fi

log_message "DB init finished successfully"