# Installation Guide - MQTT Extractor Home Assistant Add-on

This guide provides step-by-step instructions for installing the MQTT to Cognite Data Fusion extractor as a Home Assistant OS add-on.

## Prerequisites

- Home Assistant OS running (in VirtualBox VM or on physical hardware)
- Access to Home Assistant web interface
- MQTT broker (can be Home Assistant's built-in Mosquitto add-on)
- Cognite Data Fusion account with OAuth credentials

## Method 1: Local Add-on Installation (Recommended)

### Step 1: Transfer Add-on Files to Home Assistant

You need to copy the `mqtt-extractor` folder to your Home Assistant system. Choose one of these methods:

#### Option A: Using Samba Share (Easiest)

1. **Enable Samba Share add-on in Home Assistant:**
   - Go to Settings → Add-ons → Add-on Store
   - Search for "Samba share" and install it
   - Start the add-on and enable "Start on boot"

2. **Access the share from Windows:**
   - Open File Explorer
   - Navigate to `\\homeassistant.local` or `\\<HA-IP-ADDRESS>`
   - Enter your Home Assistant credentials
   - Navigate to `config/addons/` folder

3. **Copy the add-on folder:**
   - Copy the entire `mqtt-extractor` folder from your development machine
   - Paste it into `\\homeassistant.local\config\addons\mqtt-extractor`

#### Option B: Using SSH

1. **Enable SSH add-on in Home Assistant:**
   - Go to Settings → Add-ons → Add-on Store
   - Search for "SSH & Web Terminal" and install it
   - Configure and start it

2. **Transfer files using SCP (from Windows PowerShell):**
   ```powershell
   scp -r mqtt-extractor root@homeassistant.local:/config/addons/
   ```

3. **Or use WinSCP or similar GUI tool**

#### Option C: Using USB Drive

1. Copy `mqtt-extractor` folder to a USB drive
2. Plug USB drive into your Home Assistant system
3. Use SSH to mount and copy:
   ```bash
   # Find USB device
   lsblk
   # Mount USB (adjust device name)
   mount /dev/sda1 /mnt
   # Copy files
   cp -r /mnt/mqtt-extractor /config/addons/
   ```

### Step 2: Verify File Structure

SSH into Home Assistant and verify the structure:

```bash
ls -la /config/addons/mqtt-extractor/
```

You should see:
```
config.json
Dockerfile
run.sh
requirements.txt
extractor.py
mqtt_extractor/
```

### Step 3: Set Permissions

```bash
chmod +x /config/addons/mqtt-extractor/run.sh
```

### Step 4: Install via Home Assistant UI

1. **Restart Home Assistant** (to detect the new add-on)
   - Go to Settings → System → Restart

2. **Access the add-on:**
   - Go to Settings → Add-ons
   - You should see "MQTT to Cognite Data Fusion Extractor" in the list
   - If not, refresh the page or check the file structure

3. **Install the add-on:**
   - Click on the add-on
   - Click "Install"
   - Wait for installation to complete (this may take a few minutes)

### Step 5: Configure the Add-on

1. **Go to the Configuration tab**

2. **Fill in MQTT settings:**
   ```json
   {
     "mqtt_hostname": "homeassistant.local",
     "mqtt_port": 1883,
     "mqtt_username": "",
     "mqtt_password": "",
     "mqtt_topics": ["*"],
     "mqtt_qos": 1
   }
   ```

3. **Fill in CDF settings:**
   ```json
   {
     "cdf_url": "https://az-eastus-1.cognitedata.com",
     "cdf_project": "your-project-name",
     "idp_client_id": "your-client-id",
     "idp_token_url": "https://login.microsoftonline.com/your-tenant-id/oauth2/v2.0/token",
     "idp_client_secret": "your-client-secret",
     "idp_scopes": "https://az-eastus-1.cognitedata.com/.default"
   }
   ```

4. **Click "Save"**

### Step 6: Start the Add-on

1. **Go to the Info tab**
2. **Toggle "Start on boot"** (optional, recommended)
3. **Click "Start"**
4. **Check the Log tab** to verify it's running

## Method 2: Using a Custom Repository

If you want to host the add-on in a Git repository:

### Step 1: Create a Repository

1. Create a GitHub/GitLab repository
2. Push the `mqtt-extractor` folder to the repository
3. Note the repository URL

### Step 2: Add Repository in Home Assistant

1. Go to Settings → Add-ons → Add-on Store
2. Click the three dots (⋮) → Repositories
3. Click "Add"
4. Enter your repository URL
5. Click "Add"

### Step 3: Install and Configure

Follow Steps 4-6 from Method 1 above.

## Verification

### Check Add-on Status

1. Go to Settings → Add-ons → MQTT Extractor
2. Verify status shows "Started"
3. Check the Log tab for:
   ```
   Connected to homeassistant.local:1883 (1 subscriptions)
   MQTT to CDF Extractor - Starting
   ```

### Test MQTT Connection

1. Go to Developer Tools → MQTT
2. Publish a test message:
   - Topic: `test/sensor/temperature`
   - Payload: `22.5`
   - Click "Publish"
3. Check add-on logs - you should see the message being processed

### Verify CDF Connection

1. Check add-on logs for CDF connection messages
2. Log in to Cognite Data Fusion
3. Navigate to Time Series
4. Search for `mqtt:test_sensor_temperature`
5. Verify data points are being uploaded

## Troubleshooting Installation

### Add-on Not Appearing

- **Check file structure**: Ensure all files are in `/config/addons/mqtt-extractor/`
- **Check permissions**: Ensure `run.sh` is executable
- **Restart Home Assistant**: Sometimes needed to detect new add-ons
- **Check logs**: Look in Home Assistant logs for add-on detection errors

### Installation Fails

- **Check disk space**: `df -h` to verify available space
- **Check Docker**: Ensure Docker is running
- **Check logs**: Look at the add-on installation logs
- **Verify Python version**: The Dockerfile uses Python 3.11

### Build Errors

- **Check Dockerfile**: Ensure it's valid
- **Check requirements.txt**: Verify all packages are available
- **Check network**: Ensure the container can access the internet to download packages

## Next Steps

After successful installation:

1. **Configure subscriptions**: Adjust `mqtt_topics` to match your needs
2. **Set up data model** (optional): Enable data model integration if needed
3. **Monitor performance**: Check logs regularly
4. **Set up backups**: Include add-on configuration in your backups

## Uninstallation

To remove the add-on:

1. Go to Settings → Add-ons → MQTT Extractor
2. Click "Stop" (if running)
3. Click "Uninstall"
4. Optionally delete `/config/addons/mqtt-extractor` folder

