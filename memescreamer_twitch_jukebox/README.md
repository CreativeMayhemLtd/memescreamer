# 🎵 Memescreamer Twitch Jukebox

**A Twitch chat bot that lets viewers request videos/music and streams them to your channel!**

Your viewers type `!request <video link>` in chat → the bot downloads it → streams it live on your channel.

---

## 📋 Table of Contents

1. [What You Need Before Starting](#-what-you-need-before-starting)
2. [Step 1: Install Docker Desktop](#-step-1-install-docker-desktop)
3. [Step 2: Get Your Twitch Credentials](#-step-2-get-your-twitch-credentials)
4. [Step 3: Download This Project](#-step-3-download-this-project)
5. [Step 4: Configure Your Settings](#-step-4-configure-your-settings)
6. [Step 5: Build and Run](#-step-5-build-and-run)
7. [Testing It Works](#-testing-it-works)
8. [Commands Reference](#-commands-reference)
9. [Stopping and Restarting](#-stopping-and-restarting)
10. [Troubleshooting](#-troubleshooting)
11. [Optional: GPU Acceleration](#-optional-gpu-acceleration-nvidia-only)
12. [Features Deep Dive](#-features-deep-dive)

---

## 🔧 What You Need Before Starting

| Requirement | Why You Need It |
|-------------|-----------------|
| **Windows 10/11** (64-bit) | Docker Desktop runs on Windows 10/11 |
| **8GB RAM minimum** | Docker needs memory to run containers |
| **10GB free disk space** | For Docker, the bot, and downloaded media |
| **Twitch Account** | Obviously! You're streaming to Twitch |
| **Internet Connection** | For downloading videos and streaming |

---

## 📦 Step 1: Install Docker Desktop

**What is Docker?** Think of it as a "box" that contains everything the bot needs to run. You don't need to install Python, FFmpeg, or anything else—Docker handles it all!

### Windows Installation

1. **Download Docker Desktop:**
   - Go to: https://www.docker.com/products/docker-desktop/
   - Click the big **"Download for Windows"** button
   - Save the installer (about 500MB)

2. **Run the Installer:**
   - Double-click `Docker Desktop Installer.exe`
   - When asked, make sure **"Use WSL 2"** is checked ✅
   - Click **Install**
   - Wait for it to finish (takes 2-5 minutes)

3. **Restart Your Computer:**
   - Docker will ask you to restart—do it!
   - This is required for WSL 2 (Windows Subsystem for Linux)

4. **First Launch:**
   - After restart, Docker Desktop should start automatically
   - If not, search for "Docker Desktop" in Start menu and open it
   - You'll see a whale icon 🐳 in your system tray (bottom-right near the clock)
   - Wait until it says **"Docker Desktop is running"**

5. **Accept the Terms:**
   - First time you open Docker Desktop, accept the license agreement
   - Skip the tutorial if you want

### ✅ How to Know Docker is Working

Open **Command Prompt** or **PowerShell** and type:
```
docker --version
```

You should see something like:
```
Docker version 24.0.6, build ed223bc
```

If you see an error, Docker isn't installed correctly. Try restarting your computer or reinstalling Docker Desktop.

---

## 🔑 Step 2: Get Your Twitch Credentials

You need TWO things from Twitch:

### A. Bot Token (for reading/writing chat)

1. Go to: https://twitchtokengenerator.com/
2. Click **"Bot Chat Token"**
3. Click **"Authorize"** (login to your Twitch account if needed)
4. You'll get an **Access Token** that looks like: `abc123def456ghi789...`
5. **COPY THIS TOKEN** - you'll need it in Step 4
   
   ⚠️ **Keep this secret!** Anyone with this token can control your bot.

### B. Stream Key (for streaming video to your channel)

1. Go to your Twitch Dashboard: https://dashboard.twitch.tv/
2. Click **Settings** → **Stream**
3. Find **Primary Stream key**
4. Click **Copy** to copy it
   
   ⚠️ **Keep this secret!** Anyone with this key can stream to your channel.

### Summary: What You Should Have Now

| Credential | Looks Like | Where to Get It |
|------------|------------|-----------------|
| Bot Token | `abc123def456ghi789jkl...` | twitchtokengenerator.com |
| Stream Key | `live_123456789_AbCdEfGh...` | Twitch Dashboard → Settings → Stream |

---

## 📥 Step 3: Download This Project

### Option A: Download as ZIP (Easiest)

1. Click the green **"Code"** button on GitHub
2. Click **"Download ZIP"**
3. Extract the ZIP to a folder, like `C:\memescreamer_twitch_jukebox`

### Option B: Use Git (if you have it installed)

```
git clone https://github.com/CreativeMayhemLtd/memescreamer.git
cd memescreamer/memescreamer_twitch_jukebox
```

---

## ⚙️ Step 4: Configure Your Settings

1. **Open the project folder** in File Explorer

2. **Find the file** called `.env.example`

3. **Make a copy** of it and rename the copy to `.env`
   - Right-click `.env.example` → Copy
   - Right-click in empty space → Paste  
   - Right-click the copy → Rename → change to `.env`
   
   ⚠️ **Note:** The file must be named exactly `.env` (with the dot, no extension)

4. **Open `.env` in Notepad** (right-click → Open with → Notepad)

5. **Fill in your credentials:**

```ini
# Your bot's access token from twitchtokengenerator.com
TWITCH_BOT_TOKEN=paste_your_bot_token_here

# Your Twitch username (lowercase)
TWITCH_BOT_NICK=your_twitch_username

# Which channel(s) to join (comma-separated, no spaces)
TWITCH_CHANNELS=your_channel_name

# Your stream key from Twitch Dashboard
TWITCH_STREAM_KEY=live_123456789_YourStreamKeyHere

# Where to stream (don't change unless you know what you're doing)
TWITCH_RTMP_URL=rtmp://live.twitch.tv/app

# Video settings (safe defaults - don't change unless needed)
MAX_DURATION_SECONDS=600
MAX_FILE_SIZE_MB=500
NSFW_THRESHOLD=0.5
```

### Example of a filled-in .env file:

```ini
TWITCH_BOT_TOKEN=abc123def456ghi789jklmnop
TWITCH_BOT_NICK=coolstreamer
TWITCH_CHANNELS=coolstreamer
TWITCH_STREAM_KEY=live_123456789_AbCdEfGhIjKlMn
TWITCH_RTMP_URL=rtmp://live.twitch.tv/app
MAX_DURATION_SECONDS=600
MAX_FILE_SIZE_MB=500
NSFW_THRESHOLD=0.5
```

6. **Save the file** (Ctrl+S) and close Notepad

---

## 🚀 Step 5: Build and Run

### Open PowerShell in the Project Folder

1. Open File Explorer and navigate to your project folder
2. Click in the address bar, type `powershell`, and press Enter
   
   **OR**
   
   Hold Shift + Right-click in the folder → "Open PowerShell window here"

### Build the Docker Container (First Time Only)

This downloads and sets up everything the bot needs. Takes 5-15 minutes depending on your internet.

```powershell
docker-compose build
```

You'll see lots of text scrolling by—that's normal! Wait until you see:
```
Successfully built xxxxxxxx
Successfully tagged memescreamer_twitch_jukebox:latest
```

### Start the Bot

```powershell
docker-compose up
```

You should see output like:
```
Creating memescreamer_twitch_jukebox ... done
Attaching to memescreamer_twitch_jukebox
memescreamer_twitch_jukebox  | INFO - Starting memescreamer_twitch_jukebox Bot
memescreamer_twitch_jukebox  | INFO - Database initialized at /app/data/queue.db
memescreamer_twitch_jukebox  | INFO - Stream worker started
```

**The bot is now running!** 🎉

### Run in Background (Optional)

If you want to close the PowerShell window and keep the bot running:

```powershell
docker-compose up -d
```

The `-d` means "detached" (runs in background).

---

## ✅ Testing It Works

1. **Go to your Twitch chat** (your channel or another channel you joined)

2. **Type a request:**
   ```
   !request https://www.youtube.com/watch?v=dQw4w9WgXcQ
   ```

3. **The bot should respond** with something like:
   ```
   @YourName ⚠️ NOTICE: By submitting content, you confirm you have rights...
   @YourName ✅ Added to queue: "Rick Astley - Never Gonna Give You Up" (position 1)
   ```

4. **The video should start streaming** to your Twitch channel!

### Test Commands

| Type This | What Happens |
|-----------|--------------|
| `!request <youtube link>` | Adds video to queue |
| `!queue` | Shows what's coming up |
| `!np` | Shows what's playing now |

---

## 🎮 Commands Reference

### For Everyone

| Command | Example | Description |
|---------|---------|-------------|
| `!request <url>` | `!request https://youtube.com/watch?v=xxx` | Add a video to the queue |
| `!request <url> <promo>` | `!request https://clips.twitch.tv/xxx https://youtube.com/c/mychannel` | Add video with "Hear more at:" link |
| `!queue` | `!queue` | See next 5 videos in queue |
| `!np` | `!np` | See what's playing now |

### For Moderators Only

| Command | Description |
|---------|-------------|
| `!skip` | Skip the current video |

### For Broadcaster Only

| Command | Description |
|---------|-------------|
| `!clear` | Clear the entire queue |

### Supported Video Sources

- ✅ YouTube videos and playlists
- ✅ Twitch clips and VODs  
- ✅ Direct MP4/MP3 URLs
- ✅ Many other sites (powered by yt-dlp)

---

## ⏹️ Stopping and Restarting

### To Stop the Bot

If running in foreground: Press `Ctrl+C` in the PowerShell window

If running in background:
```powershell
docker-compose down
```

### To Restart the Bot

```powershell
docker-compose up
```

Or if in background:
```powershell
docker-compose restart
```

### To See Logs (if running in background)

```powershell
docker-compose logs -f
```

Press `Ctrl+C` to stop watching logs (doesn't stop the bot).

---

## 🔧 Troubleshooting

### "Docker is not recognized"

Docker Desktop isn't installed or isn't running.
- Make sure Docker Desktop is running (whale icon in system tray 🐳)
- Try restarting your computer

### "Cannot connect to the Docker daemon"

Docker Desktop is installed but not running.
- Open Docker Desktop from the Start menu
- Wait for the whale icon to appear and say "running"

### "Invalid or unauthorized Access Token"

Your bot token is wrong or expired.
- Go back to https://twitchtokengenerator.com/
- Generate a new token
- Update your `.env` file
- Restart the bot: `docker-compose down` then `docker-compose up`

### "Error: port is already allocated"

Another program is using port 1935.
- Stop any other streaming software
- Or change the port in `docker-compose.yml`

### "no matching manifest for windows"

Docker is in Windows container mode, but we need Linux mode.
- Right-click the Docker whale icon in system tray
- Click "Switch to Linux containers..."

### Video Won't Play / No Stream Output

1. Check your stream key is correct
2. Make sure no other streaming software is streaming (OBS, Streamlabs, etc.)
3. Check the logs: `docker-compose logs -f`

### Bot Doesn't Respond in Chat

1. Make sure the bot joined the right channel (check `TWITCH_CHANNELS` in `.env`)
2. Make sure `TWITCH_BOT_NICK` is your username in lowercase
3. Check if bot token has chat permissions

### NSFW Filter Rejecting Everything

The threshold might be too strict.
- Edit `.env` and change `NSFW_THRESHOLD=0.5` to `NSFW_THRESHOLD=0.7`
- Restart the bot

### Build Fails with "network timeout"

Your internet connection dropped during download.
- Make sure you have stable internet
- Run `docker-compose build` again

### "No space left on device"

Docker ran out of disk space.
- Open Docker Desktop → Settings → Resources
- Increase the "Disk image size"
- Or run `docker system prune` to clean up unused images

---

## 🎮 Optional: GPU Acceleration (NVIDIA Only)

This makes NSFW scanning faster. **Skip this if you don't have an NVIDIA GPU!**

### Requirements

- NVIDIA GPU (GTX 1060 or better recommended)
- NVIDIA Driver version 530 or newer
- Windows with WSL2

### Step 1: Install NVIDIA Drivers

Download from: https://www.nvidia.com/drivers

### Step 2: Enable GPU in docker-compose.yml

Open `docker-compose.yml` in Notepad and find these lines:
```yaml
    # Uncomment for GPU support:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]
```

Remove the `#` symbols to make it look like:
```yaml
    # Uncomment for GPU support:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Step 3: Rebuild and Restart

```powershell
docker-compose down
docker-compose build
docker-compose up
```

---

## 📚 Features Deep Dive

### Promo Links

When viewers request a video, they can optionally include a promo link:
```
!request https://youtube.com/watch?v=xxx https://soundcloud.com/mymusic
```

The stream will show: **"Hear more at: soundcloud.com/mymusic"**

Supported promo domains:
- YouTube, SoundCloud, Spotify, Bandcamp
- Twitter/X, Instagram

### NSFW Content Filtering

All videos are automatically scanned for inappropriate content using AI. 

- Uses the [Hotdog_NotHotdog](https://github.com/CreativeMayhemLtd/memescreamer_Hotdog_NotHotdog) CLIP-based classifier
- Scans video frames for nudity, explicit content, etc.
- Rejected videos won't be added to the queue
- Adjust sensitivity with `NSFW_THRESHOLD` (0.0 = strict, 1.0 = permissive)

### Stream Overlay

When a video plays, viewers see:
- 🎬 **Title** of the video
- 👤 **Requested by:** username
- 🔗 **Hear more at:** promo link (if provided)

### Persistent Queue

The queue survives restarts! If the bot crashes or you restart it, pending requests are still there.

Queue data is stored in: `./data/queue.db`

---

## 📁 Folder Structure

After running, your folder will look like:

```
memescreamer_twitch_jukebox/
├── .env                    ← Your configuration (KEEP SECRET!)
├── .env.example            ← Template for .env
├── docker-compose.yml      ← Docker configuration
├── Dockerfile              ← How to build the container
├── requirements.txt        ← Python dependencies
├── data/                   ← Database (created automatically)
│   └── queue.db
├── logs/                   ← Log files (created automatically)
│   └── bot.log
└── media/                  ← Downloaded videos (created automatically)
    └── (video files)
```

---

## 🆘 Getting Help

If you're stuck:

1. **Read the error message** - it often tells you what's wrong
2. **Check Troubleshooting section** above
3. **Look at the logs**: `docker-compose logs -f`
4. **Search the error** on Google
5. **Ask on GitHub Issues** if all else fails

---

## 📄 License Notes

### This Bot
MIT License - free for any use.

### Hotdog_NotHotdog (NSFW Filter)
- **Personal/Non-commercial use**: Free
- **Commercial use**: Requires license from Creative Mayhem Ltd
  - Contact: info@creativemayhem.ltd  
  - Starting at $9/year per user

---

**Happy streaming! 🎉**
