# Samba Share Access Troubleshooting

## Common Issues and Solutions

### Issue 1: Hostname Not Resolving

**Problem:** `\\homeassistant.local` doesn't work in Windows File Explorer

**Solutions:**

1. **Use IP Address Instead:**
   - Find your Home Assistant IP address:
     - Go to Home Assistant → Settings → System → Network
     - Or check your router's DHCP client list
     - Or ping from command prompt: `ping homeassistant.local`
   - Use: `\\<IP-ADDRESS>` instead of `\\homeassistant.local`
   - Example: `\\192.168.1.100`

2. **Add Hostname to Windows Hosts File:**
   - Open Notepad as Administrator
   - Open: `C:\Windows\System32\drivers\etc\hosts`
   - Add line: `<IP-ADDRESS> homeassistant.local`
   - Save and try again

### Issue 2: Windows Credentials

**Problem:** Windows doesn't prompt for credentials or rejects them

**Solutions:**

1. **Use Format: `\\IP-ADDRESS\sharename`:**
   - Example: `\\192.168.1.100\config`
   - Windows will prompt for credentials

2. **Enter Credentials Correctly:**
   - Username: `tmolbach@outlook.com` (exactly as configured)
   - Password: `S3cr3tH0m3@ss!st@nt99!`
   - Check "Remember my credentials" if desired

3. **Clear Stored Credentials:**
   - Open "Credential Manager" (search in Start menu)
   - Go to "Windows Credentials"
   - Remove any old entries for `homeassistant.local` or the IP address
   - Try connecting again

### Issue 3: SMB Protocol Version

**Problem:** Windows 10/11 might use SMB 3.x which needs specific settings

**Solutions:**

1. **Enable SMB 1.0 (if needed):**
   - Open "Turn Windows features on or off"
   - Check "SMB 1.0/CIFS File Sharing Support"
   - Restart if prompted

2. **Check Samba Compatibility Mode:**
   - Your config has `compatibility_mode: false` - try setting to `true`
   - Restart Samba add-on after change

### Issue 4: Network Discovery

**Problem:** Can't see Home Assistant in Network folder

**Solutions:**

1. **Enable Network Discovery:**
   - Open Network and Sharing Center
   - Change advanced sharing settings
   - Enable "Turn on network discovery"
   - Enable "Turn on file and printer sharing"

2. **Use Direct Path:**
   - Don't rely on Network discovery
   - Type path directly in File Explorer address bar

### Issue 5: Firewall

**Problem:** Windows Firewall blocking connection

**Solutions:**

1. **Check Windows Firewall:**
   - Ensure "File and Printer Sharing" is allowed
   - Or temporarily disable firewall to test

2. **Check Home Assistant Firewall:**
   - Ensure Samba ports are open (139, 445)

## Step-by-Step Access Guide

### Method 1: Using IP Address (Most Reliable)

1. **Find Home Assistant IP:**
   ```powershell
   ping homeassistant.local
   # Note the IP address from the response
   ```

2. **Open File Explorer:**
   - Press `Win + E`

3. **Type in Address Bar:**
   ```
   \\192.168.1.100\config
   ```
   (Replace with your actual IP)

4. **Enter Credentials:**
   - Username: `tmolbach@outlook.com`
   - Password: `S3cr3tH0m3@ss!st@nt99!`

5. **Navigate to addons folder:**
   ```
   \\192.168.1.100\config\addons\
   ```

### Method 2: Map Network Drive

1. **Open File Explorer**
2. **Right-click "This PC" → Map network drive**
3. **Choose drive letter** (e.g., Z:)
4. **Folder:** `\\192.168.1.100\config`
5. **Check "Connect using different credentials"**
6. **Click Finish**
7. **Enter credentials when prompted**

### Method 3: Using Command Line

```powershell
# Map drive
net use Z: \\192.168.1.100\config /user:tmolbach@outlook.com S3cr3tH0m3@ss!st@nt99!

# Access drive
cd Z:\addons

# Unmap when done
net use Z: /delete
```

## Testing Connection

### From PowerShell:

```powershell
# Test if Samba is accessible
Test-NetConnection -ComputerName 192.168.1.100 -Port 445

# List shares
net view \\192.168.1.100

# Try accessing share
net use \\192.168.1.100\config
```

### From Command Prompt:

```cmd
# Test connection
ping 192.168.1.100

# List shares
net view \\192.168.1.100

# Access share
net use \\192.168.1.100\config
```

## Verify Samba Configuration

1. **Check Samba Add-on Logs:**
   - Home Assistant → Settings → Add-ons → Samba share → Log
   - Look for errors or connection attempts

2. **Verify Shares are Enabled:**
   - Your config shows `addons` and `config` are enabled ✓
   - Make sure Samba add-on is running

3. **Check Network:**
   - Ensure Windows PC and Home Assistant are on same network
   - Your `allow_hosts` includes common private networks ✓

## Quick Fix Checklist

- [ ] Use IP address instead of hostname
- [ ] Enter credentials exactly as configured (case-sensitive)
- [ ] Try accessing specific share: `\\IP\config` or `\\IP\addons`
- [ ] Clear old Windows credentials
- [ ] Enable network discovery in Windows
- [ ] Check Samba add-on is running
- [ ] Verify both devices on same network
- [ ] Try mapping as network drive
- [ ] Check Samba logs for errors

## Alternative: Use SSH Instead

If Samba continues to have issues, use SSH:

1. **Enable SSH add-on** in Home Assistant
2. **Use WinSCP or FileZilla** to transfer files
3. **Or use PowerShell SCP:**
   ```powershell
   scp -r mqtt-extractor root@192.168.1.100:/config/addons/
   ```

## Still Not Working?

1. **Check Home Assistant Logs:**
   - Settings → System → Logs
   - Look for Samba-related errors

2. **Try Different Share:**
   - Test with `\\IP\share` (if enabled)
   - This helps isolate if it's a specific share issue

3. **Restart Samba Add-on:**
   - Stop and start the Samba add-on
   - Sometimes fixes connection issues

4. **Check Windows Event Viewer:**
   - Look for SMB-related errors
   - Can provide clues about what's failing

