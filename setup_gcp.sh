#!/bin/bash

# ================================================
# GetOdd GCP Instance Automated Setup Script
# ================================================
# This script automates the entire setup process for running
# the GetOdd scraper on a fresh GCP Ubuntu instance
# ================================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.10"
PROJECT_NAME="getodd"
WORKERS_DEFAULT=5
HANDICAPS_DEFAULT="+2.5,+3,+3.5"

# Function to print colored messages
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Header
echo "================================================"
echo "   GetOdd GCP Instance Setup Script"
echo "================================================"
echo ""

# Step 1: System Update
print_status "Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y
print_success "System updated successfully"

# Step 2: Install essential packages
print_status "Step 2: Installing essential packages..."
sudo apt install -y \
    git \
    curl \
    wget \
    build-essential \
    software-properties-common \
    ca-certificates \
    gnupg \
    lsb-release \
    htop \
    screen
print_success "Essential packages installed"

# Step 3: Verify Python and install pip/venv
print_status "Step 3: Checking Python and installing pip/venv..."
python3 --version

# Install pip and venv if needed
sudo apt install -y python3-pip python3-venv
python3 -m pip install --upgrade pip
print_success "Python environment ready"

# Step 4: Install Chromium and ChromeDriver
print_status "Step 4: Installing Chromium browser and ChromeDriver..."
sudo apt install -y \
    chromium-browser \
    chromium-chromedriver

# Install headless dependencies
sudo apt install -y \
    xvfb \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils

print_success "Chromium and dependencies installed"

# Verify installations
chromium-browser --version
chromedriver --version

# Step 5: Create swap file (optional but recommended)
print_status "Step 5: Setting up swap space..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    print_success "4GB swap space created"
else
    print_warning "Swap file already exists"
fi

# Step 6: Clone or upload project
print_status "Step 6: Setting up project directory..."
cd ~

if [ ! -d "$PROJECT_NAME" ]; then
    print_warning "Project directory not found."
    echo "Please upload your project files to ~/$PROJECT_NAME"
    echo "You can use: scp -r getodd/ username@gcp-instance-ip:~/"
    echo ""
    read -p "Press Enter once you've uploaded the files, or Ctrl+C to exit..."
fi

cd $PROJECT_NAME

# Step 7: Setup Python virtual environment
print_status "Step 7: Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# Step 8: Install Python dependencies
print_status "Step 8: Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install \
        selenium==4.15.2 \
        webdriver-manager==4.0.1 \
        pandas==2.1.3 \
        pytz==2023.3
fi
print_success "Python dependencies installed"

# Step 9: Verify installation
print_status "Step 9: Verifying installation..."
python -c "from getodd_module import scrape_match_and_odds; print('✓ Module import successful')" || {
    print_error "Module import failed. Please check your installation."
    exit 1
}

# Step 10: Create helper scripts
print_status "Step 10: Creating helper scripts..."

# Create test script
cat > test_scraper.sh << 'EOF'
#!/bin/bash
source .venv/bin/activate
xvfb-run -a python -m getodd_module \
    --test \
    --workers 1 \
    --handicaps "+2.5"
EOF
chmod +x test_scraper.sh

# Create run script for specific country
cat > run_country.sh << 'EOF'
#!/bin/bash
COUNTRY=${1:-switzerland}
WORKERS=${2:-5}
HANDICAPS=${3:-"+2.5,+3,+3.5"}

source .venv/bin/activate
xvfb-run -a python -m getodd_module \
    --input-dir "match_urls_complete/by_league/${COUNTRY}" \
    --output-dir "${COUNTRY}_odds_output" \
    --workers "${WORKERS}" \
    --handicaps "${HANDICAPS}"
EOF
chmod +x run_country.sh

# Create monitoring script
cat > monitor.sh << 'EOF'
#!/bin/bash
COUNTRY=${1:-switzerland}
OUTPUT_DIR="${COUNTRY}_odds_output"

if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Output directory $OUTPUT_DIR not found!"
    exit 1
fi

echo "Monitoring $OUTPUT_DIR..."
echo "Press Ctrl+C to stop"
echo ""

while true; do
    clear
    echo "=== GetOdd Progress Monitor ==="
    echo "Country: $COUNTRY"
    echo "Time: $(date)"
    echo ""
    
    if [ -f "$OUTPUT_DIR/processing_log.txt" ]; then
        echo "Recent activity:"
        tail -n 10 "$OUTPUT_DIR/processing_log.txt" | grep "✓" || echo "No recent successes"
        echo ""
        echo "Statistics:"
        echo "  Total processed: $(grep -c "✓" "$OUTPUT_DIR/processing_log.txt" 2>/dev/null || echo 0)"
        echo "  Total failed: $(grep -c "✗" "$OUTPUT_DIR/processing_log.txt" 2>/dev/null || echo 0)"
    fi
    
    if [ -f "$OUTPUT_DIR/checkpoint.json" ]; then
        echo ""
        echo "Checkpoint info:"
        cat "$OUTPUT_DIR/checkpoint.json" | python3 -m json.tool | head -20
    fi
    
    echo ""
    echo "Output files:"
    ls -lh "$OUTPUT_DIR"/*.csv 2>/dev/null | tail -5
    
    sleep 5
done
EOF
chmod +x monitor.sh

print_success "Helper scripts created"

# Step 11: System optimization
print_status "Step 11: Applying system optimizations..."
ulimit -n 4096
echo "* soft nofile 4096" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 8192" | sudo tee -a /etc/security/limits.conf
print_success "System optimizations applied"

# Final message
echo ""
echo "================================================"
echo "   Setup Complete!"
echo "================================================"
echo ""
print_success "GetOdd GCP setup completed successfully!"
echo ""
echo "Available commands:"
echo "  ./test_scraper.sh              - Run a quick test"
echo "  ./run_country.sh switzerland    - Run for Switzerland"
echo "  ./monitor.sh switzerland        - Monitor progress"
echo ""
echo "To run in background:"
echo "  nohup ./run_country.sh switzerland > scraping.log 2>&1 &"
echo ""
echo "To use screen:"
echo "  screen -S getodd"
echo "  ./run_country.sh switzerland"
echo "  (Press Ctrl+A, D to detach)"
echo ""
print_warning "Remember to activate the virtual environment:"
echo "  source .venv/bin/activate"
echo ""