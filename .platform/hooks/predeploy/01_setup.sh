#!/bin/bash

# Create required directories
sudo mkdir -p /var/app/current/instance
sudo mkdir -p /var/app/current/uploads/teeth
sudo mkdir -p /var/log/app

# Set permissions
sudo chown -R webapp:webapp /var/app/current
sudo chown -R webapp:webapp /var/app/current/instance
sudo chown -R webapp:webapp /var/app/current/uploads
sudo chown -R webapp:webapp /var/log/app

# Set directory permissions
sudo chmod 755 /var/app/current
sudo chmod 755 /var/app/current/instance
sudo chmod 755 /var/app/current/uploads
sudo chmod 755 /var/app/current/uploads/teeth
sudo chmod 755 /var/log/app
