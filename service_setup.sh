# chmod +x setup_service.sh
# ./setup_service.sh "Flask APScheduler Service" "flask_scheduler" "/home/ec2-user/ec2-scedular-service/app.py" "ec2-scedular-service"

#!/bin/bash

# Read input parameters
APP_DESCRIPTION="$1"
SERVICE_NAME="$2"
FLASK_APP_PATH="$3"
PROJECT_NAME="$4"

APP_DIR=$(dirname "$FLASK_APP_PATH")
FLASK_APP=$(basename "$FLASK_APP_PATH")
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
PYTHON_EXEC="/usr/bin/python3.11"
PORT=5000

echo "🚀 Starting Flask Service Setup..."

# Validate input parameters
if [[ -z "$APP_DESCRIPTION" || -z "$SERVICE_NAME" || -z "$FLASK_APP_PATH" || -z "$PROJECT_NAME" ]]; then
    echo "❌ Error: Missing arguments."
    echo "Usage: $0 \"<Service Description>\" \"<Service Name>\" \"<Path to Flask App.py>\" \"<Project Name>\""
    exit 1
fi

# Update system packages
echo "🔄 Updating system packages..."
sudo yum update -y
echo "✅ System packages updated."

# Install python3.11 and pip
echo "🔄 Installing python3.11 and pip..."
sudo yum install -y python3.11 python3.11-pip
echo "✅ python3.11 and pip installed."

# Ensure the application directory exists
if [ ! -d "$APP_DIR" ]; then
    echo "📂 Creating application directory at $APP_DIR..."
    mkdir -p "$APP_DIR"
    echo "✅ Application directory created."
fi

# Clone the GitHub repository
echo "🔄 Cloning GitHub repository..."
git clone "https://github.com/gaurav9969351313/$PROJECT_NAME.git" "$APP_DIR"
echo "✅ GitHub repository cloned."

# Install required Python packages
echo "🔄 Installing required Python packages..."
pip3 install -r "$APP_DIR/requirements.txt"
echo "✅ Python packages installed."

# Create a systemd service file
echo "📝 Creating systemd service file at $SERVICE_FILE..."
sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=$APP_DESCRIPTION
After=network.target

[Service]
User=ec2-user
WorkingDirectory=$APP_DIR
ExecStart=$PYTHON_EXEC $FLASK_APP_PATH
Restart=always

[Install]
WantedBy=multi-user.target
EOF"
echo "✅ Systemd service file created."

# Reload systemd
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "✅ Systemd daemon reloaded."

# Enable and start the service
echo "🔄 Enabling and starting Flask service..."
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME
echo "✅ Flask service started and enabled."

# Display service status
echo "🔍 Checking service status..."
sudo systemctl status $SERVICE_NAME --no-pager --lines=10

echo "🎉 Flask Service Setup Complete!"
echo "🌐 Access the application at: http://<EC2-PUBLIC-IP>:$PORT"
