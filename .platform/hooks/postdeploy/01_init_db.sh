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
cd $APP_DIR

# Activate the EB Python venv and run the init script
if source /var/app/venv/*/bin/activate; then
    if ! python -m app_init_db >> /var/log/app/init_db.log 2>&1; then
        log_message "ERROR: Failed to initialize database. See /var/log/app/init_db.log for details."
        exit 1
    fi
else
    log_message "ERROR: Could not activate EB Python virtual environment."
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