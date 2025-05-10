#!/bin/bash
set -x

echo "Starting DB init at $(date)" >> /tmp/init_db.log 2>&1

# Create instance directory if it doesn't exist and set permissions
mkdir -p /var/app/current/instance >> /tmp/init_db.log 2>&1
sudo chown webapp:webapp /var/app/current/instance >> /tmp/init_db.log 2>&1
chmod 775 /var/app/current/instance >> /tmp/init_db.log 2>&1

# Create uploads directory and set permissions
mkdir -p /var/app/current/uploads/teeth >> /tmp/init_db.log 2>&1
sudo chown -R webapp:webapp /var/app/current/uploads >> /tmp/init_db.log 2>&1
chmod -R 775 /var/app/current/uploads >> /tmp/init_db.log 2>&1

# Initialize database
source /var/app/venv/*/bin/activate >> /tmp/init_db.log 2>&1
cd /var/app/current >> /tmp/init_db.log 2>&1
python3 -c "from app import app, init_db; init_db()" >> /tmp/init_db.log 2>&1

# Set proper permissions for database file
if [ -f /var/app/current/instance/dental_clinic.db ]; then
    echo "Database file created successfully at /var/app/current/instance/dental_clinic.db" >> /tmp/init_db.log 2>&1
    sudo chown webapp:webapp /var/app/current/instance/dental_clinic.db >> /tmp/init_db.log 2>&1
    sudo chmod 664 /var/app/current/instance/dental_clinic.db >> /tmp/init_db.log 2>&1
else
    echo "ERROR: Database file not created at /var/app/current/instance/dental_clinic.db" >> /tmp/init_db.log 2>&1
fi

echo "DB init finished at $(date)" >> /tmp/init_db.log 2>&1