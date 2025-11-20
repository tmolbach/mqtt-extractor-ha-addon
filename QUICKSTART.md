# Quick Start Guide

Get the MQTT Extractor add-on running in 5 minutes!

## Prerequisites Checklist

- [ ] Home Assistant OS running (VirtualBox VM or physical)
- [ ] MQTT broker available (Home Assistant's Mosquitto add-on or external)
- [ ] Cognite Data Fusion account with OAuth credentials
- [ ] Network access from Home Assistant to CDF

## Step 1: Copy Add-on Files (2 minutes)

**Using Samba (Easiest):**
1. Enable "Samba share" add-on in Home Assistant
2. Open `\\homeassistant.local` in Windows File Explorer
3. Copy `mqtt-extractor` folder to `\\homeassistant.local\config\addons\`

**Using SSH:**
```powershell
scp -r mqtt-extractor root@homeassistant.local:/config/addons/
```

## Step 2: Install Add-on (1 minute)

1. Restart Home Assistant (Settings → System → Restart)
2. Go to Settings → Add-ons
3. Find "MQTT to Cognite Data Fusion Extractor"
4. Click "Install"
5. Wait for installation (~2-3 minutes)

## Step 3: Configure (2 minutes)

Go to the **Configuration** tab and fill in:

### MQTT Settings
```json
{
  "mqtt_hostname": "homeassistant.local",
  "mqtt_port": 1883,
  "mqtt_topics": ["*"]
}
```

### CDF Settings
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

Click **Save**.

## Step 4: Start (30 seconds)

1. Go to **Info** tab
2. Toggle **Start on boot** (recommended)
3. Click **Start**
4. Check **Log** tab - you should see:
   ```
   Connected to homeassistant.local:1883 (1 subscriptions)
   ```

## Step 5: Test (30 seconds)

1. Go to Developer Tools → MQTT
2. Publish:
   - Topic: `test/temperature`
   - Payload: `22.5`
   - Click "Publish"
3. Check add-on logs - should see message processing
4. Check CDF - search for time series `mqtt:test_temperature`

## Common Issues

**Add-on not appearing?**
- Verify files are in `/config/addons/mqtt-extractor/`
- Restart Home Assistant
- Check file permissions: `chmod +x run.sh`

**Can't connect to MQTT?**
- Verify Mosquitto add-on is running
- Check hostname: use `core-mosquitto` if using HA's broker
- Verify port: `1883` for non-TLS

**CDF authentication fails?**
- Double-check all CDF credentials
- Verify URL format: `https://<cluster>.cognitedata.com`
- Check token URL format: `https://login.microsoftonline.com/<tenant>/oauth2/v2.0/token`

## Next Steps

- **Customize topics**: Change `mqtt_topics` to specific topics you need
- **Enable data model**: Set `enable_data_model: true` and configure instance space
- **Adjust logging**: Set `log_level: DEBUG` for detailed logs
- **Monitor**: Check logs regularly to ensure data is flowing

## Getting Help

- Check **Log** tab for error messages
- Review **README.md** for detailed documentation
- Check **INSTALLATION.md** for troubleshooting
- Verify configuration matches examples in **README.md**

## Configuration Examples

### Subscribe to Specific Topics
```json
{
  "mqtt_topics": ["home/sensor/temperature", "home/sensor/humidity"]
}
```

### Subscribe with Wildcards
```json
{
  "mqtt_topics": ["home/sensor/#", "home/device/+/status"]
}
```

### Enable Data Model
```json
{
  "enable_data_model": true,
  "instance_space": "ha_instances",
  "data_model_space": "sp_enterprise_schema_space"
}
```

That's it! Your MQTT data is now flowing to Cognite Data Fusion! 🎉

