#!/bin/bash
set -x
echo "Starting DB init at $(date)" >> /tmp/init_db.log 2>&1
source /var/app/venv/*/bin/activate >> /tmp/init_db.log 2>&1
cd /var/app/current >> /tmp/init_db.log 2>&1
python3 -c "from app import app, init_db; print('Initializing database...'); init_db(); print('Database initialization complete.')" >> /tmp/init_db.log 2>&1
echo "DB init finished at $(date)" >> /tmp/init_db.log 2>&1 