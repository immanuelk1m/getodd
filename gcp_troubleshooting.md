# GCP GetOdd Troubleshooting Guide

## 🔴 Common Issues and Solutions

### 1. Chrome/Chromium Issues

#### Error: "Chrome not reachable"
```bash
# Solution 1: Kill all Chrome processes
pkill -f chrome
pkill -f chromium

# Solution 2: Check if Chrome is installed
which chromium-browser || which google-chrome

# Solution 3: Reinstall Chrome
sudo apt remove --purge chromium-browser chromium-chromedriver
sudo apt update
sudo apt install -y chromium-browser chromium-chromedriver

# Solution 4: Check ChromeDriver permissions
sudo chmod +x /usr/bin/chromedriver
ls -la /usr/bin/chromedriver
```

#### Error: "session not created: Chrome version must be..."
```bash
# Check versions match
chromium-browser --version
chromedriver --version

# Update both to latest
sudo apt update
sudo apt upgrade chromium-browser chromium-chromedriver
```

### 2. Xvfb Display Issues

#### Error: "cannot connect to X server"
```bash
# Solution 1: Install Xvfb
sudo apt install -y xvfb

# Solution 2: Start Xvfb manually
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

# Solution 3: Use xvfb-run wrapper
xvfb-run -a python -m getodd_module --test
```

#### Error: "Xvfb failed to start"
```bash
# Check if Xvfb is already running
ps aux | grep Xvfb

# Kill existing Xvfb processes
pkill Xvfb

# Start with specific display number
xvfb-run --server-num=100 python -m getodd_module --test
```

### 3. Memory Issues

#### Error: "Cannot allocate memory"
```bash
# Check memory usage
free -h
htop

# Add swap space if needed
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Reduce workers
python -m getodd_module --workers 2  # Instead of 5

# Kill memory-hungry processes
pkill -f chrome
```

#### Browser crashes frequently
```python
# Edit getodd_module/scraper.py to disable images
options.add_experimental_option("prefs", {
    "profile.managed_default_content_settings.images": 2  # Disable images
})
```

### 4. Network Issues

#### Error: "Connection timeout"
```bash
# Check network connectivity
ping -c 4 oddsportal.com
curl -I https://www.oddsportal.com

# Check DNS
nslookup oddsportal.com
cat /etc/resolv.conf

# Use Google DNS
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
```

#### Rate limiting / 429 errors
```bash
# Reduce workers
--workers 2

# Add delays between requests
# Edit getodd_module/config.py
WAIT_DELAY = 3  # Increase from 1
```

### 5. Python Environment Issues

#### Error: "ModuleNotFoundError: No module named 'getodd_module'"
```bash
# Check current directory
pwd
ls -la

# Ensure you're in the right directory
cd ~/getodd

# Activate virtual environment
source .venv/bin/activate

# Reinstall module
pip install -e .
```

#### Error: "ImportError: cannot import name..."
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Reinstall dependencies
pip uninstall -y selenium pandas pytz
pip install -r requirements.txt
```

### 6. File Permission Issues

#### Error: "Permission denied"
```bash
# Fix file permissions
chmod -R 755 ~/getodd
chmod +x run_*.sh

# Fix output directory permissions
mkdir -p switzerland_odds_output
chmod 777 switzerland_odds_output
```

### 7. Process Management Issues

#### Script stops when SSH disconnects
```bash
# Use nohup
nohup xvfb-run -a python -m getodd_module \
    --input-dir match_urls_complete/by_league/switzerland \
    --output-dir switzerland_odds_output \
    --workers 5 \
    > scraping.log 2>&1 &

# Or use screen
screen -S getodd
# Run your command
# Detach: Ctrl+A, D
# Reattach: screen -r getodd

# Or use tmux
tmux new -s getodd
# Run your command
# Detach: Ctrl+B, D
# Reattach: tmux attach -t getodd
```

#### Can't kill stuck process
```bash
# Find process
ps aux | grep getodd
ps aux | grep python

# Kill by PID
kill -9 <PID>

# Kill all Python processes
pkill -9 python

# Kill all Chrome processes
pkill -9 -f chrome
```

### 8. Disk Space Issues

#### Error: "No space left on device"
```bash
# Check disk usage
df -h

# Find large files
du -sh /* 2>/dev/null | sort -h

# Clean up
sudo apt clean
sudo apt autoremove

# Remove old logs
rm -rf ~/getodd/*_odds_output/processing_log.txt.old
```

### 9. GCP-Specific Issues

#### Instance becomes unresponsive
```bash
# SSH with verbose mode
ssh -vvv username@instance-ip

# Reset instance from GCP Console
gcloud compute instances reset instance-name

# Increase machine type if needed
gcloud compute instances set-machine-type instance-name \
    --machine-type n1-standard-2
```

#### Firewall blocking connections
```bash
# Check firewall rules
gcloud compute firewall-rules list

# Allow SSH
gcloud compute firewall-rules create allow-ssh \
    --allow tcp:22 \
    --source-ranges 0.0.0.0/0
```

## 🔍 Debugging Commands

### Check system status
```bash
# System resources
free -h
df -h
htop

# Network
netstat -tulpn
ss -tulpn

# Processes
ps aux | grep -E "python|chrome|xvfb"

# Logs
tail -f switzerland_odds_output/processing_log.txt
journalctl -xe
dmesg | tail
```

### Test individual components
```bash
# Test Chrome
chromium-browser --headless --dump-dom https://www.google.com

# Test Python import
python -c "from getodd_module import scraper; print('OK')"

# Test Selenium
python -c "from selenium import webdriver; print('OK')"

# Test single URL
python -c "
from getodd_module.scraper import scrape_match_and_odds
url = 'https://www.oddsportal.com/football/belgium/jupiler-league-2020-2021/anderlecht-club-brugge-kv-dYjWaEPo/'
result = scrape_match_and_odds(url, ['+2.5'], headless=True)
print(f'Got {len(result)} entries')
"
```

## 📊 Performance Optimization

### Optimize for low-memory instances
```bash
# Use fewer workers
--workers 2

# Process in smaller batches
--batch-size 5

# Disable images in Chrome
# Already configured in scraper.py

# Use swap space
sudo swapon -s  # Check current swap
```

### Optimize for speed
```bash
# Use more workers (if memory allows)
--workers 10

# Larger batch sizes
--batch-size 20

# Disable unnecessary Chrome features
# Already optimized in scraper.py
```

## 🆘 Emergency Recovery

### Resume interrupted scraping
```bash
# Check checkpoint
cat switzerland_odds_output/checkpoint.json

# Resume from checkpoint
python -m getodd_module \
    --input-dir match_urls_complete/by_league/switzerland \
    --output-dir switzerland_odds_output \
    --workers 5 \
    --handicaps "+2.5,+3,+3.5" \
    --resume
```

### Backup partial results
```bash
# Create backup
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz switzerland_odds_output/

# Copy to Cloud Storage
gsutil cp backup_*.tar.gz gs://your-bucket/backups/
```

### Complete system reset
```bash
# Stop all processes
pkill -9 python
pkill -9 chrome
pkill -9 Xvfb

# Clear temporary files
rm -rf /tmp/.X*
rm -rf ~/.cache/chromium

# Restart services
sudo systemctl restart systemd-resolved

# Reactivate environment
cd ~/getodd
source .venv/bin/activate

# Test with single URL
./test_scraper.sh
```

## 📞 Getting Help

When reporting issues, include:
1. Error message (full traceback)
2. System info: `uname -a`
3. Chrome version: `chromium-browser --version`
4. Python version: `python --version`
5. Recent logs: `tail -100 switzerland_odds_output/processing_log.txt`
6. Memory status: `free -h`
7. Disk status: `df -h`

### Log locations
- Application logs: `{country}_odds_output/processing_log.txt`
- System logs: `/var/log/syslog`
- Chrome crashes: `/var/log/messages`
- Python errors: Check terminal output or nohup.out