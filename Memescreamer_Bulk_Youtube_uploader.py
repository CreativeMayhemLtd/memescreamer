#!/usr/bin/env python3
"""
Memescreamer Youtube Bulk Uploader
Copyright (c) 2025 Creative Mayhem Ltd. All rights reserved.

DUAL LICENSE TERMS

NON-COMMERCIAL LICENSE:
This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 
International (CC BY-NC-SA 4.0) for non-commercial use.

You are free to:
- Share: copy and redistribute the material in any medium or format
- Adapt: remix, transform, and build upon the material

Under the following terms:
- Attribution: You must give appropriate credit to Creative Mayhem Ltd
- NonCommercial: You may not use the material for commercial purposes
- ShareAlike: If you remix, transform, or build upon the material, you must distribute 
  your contributions under the same license as the original

COMMERCIAL LICENSE:
Commercial use of this software requires a separate paid license from Creative Mayhem Ltd.
Commercial use includes but is not limited to:
- Use in any business or commercial environment
- Use that generates revenue or monetary benefit
- Integration into commercial products or services
- Use by organizations with annual revenue exceeding $10,000

For commercial licensing inquiries, contact:
Creative Mayhem Ltd
Website: http://www.memescreamer.com
Email: licensing@memescreamer.com

DISCLAIMER:
This software is provided "as is" without warranty of any kind, express or implied.
Creative Mayhem Ltd shall not be liable for any damages arising from the use of this software.

--------------------------------------------------------------------------------

SpiderCat YouTube Uploader CLI Tool
Uses SpiderCat JSON sidecar metadata to create algorithm-optimized YouTube content
Specifically designed for SpiderCat *-audio.mp4 files with corresponding JSON metadata

Usage:
    python spidercat_youtube_uploader_cli.py [video_file_or_directory] [options]
    
Examples:
    # Upload single SpiderCat audio video with metadata
    python spidercat_youtube_uploader_cli.py "output/250825/250825022229_00001-audio.mp4"
    
    # Bulk upload directory with SpiderCat *-audio.mp4 files
    python spidercat_youtube_uploader_cli.py "output/250825/video/" --bulk
    
    # Dry run to preview uploads (recommended first)
    python spidercat_youtube_uploader_cli.py "output/250825/video/" --bulk --dry-run
    
    # Industrial mode: bulk upload with 10-minute scheduling
    python spidercat_youtube_uploader_cli.py "output/250825/video/" -X
    
    # Upload with custom scheduled spreading
    python spidercat_youtube_uploader_cli.py "output/250825/video/" --bulk --auto-spread --schedule-delay 15 --schedule-start "14:30"

Note: This tool specifically looks for *-audio.mp4 files (ignores regular *.mp4 files)
Each video requires a corresponding JSON file with SpiderCat ai_commentary metadata.
"""

import os, sys, io, locale
os.environ.setdefault("PYTHONUTF8", "1")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    sys.stdout = io.TextIOWrapper(getattr(sys, "stdout", sys.__stdout__).buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(getattr(sys, "stderr", sys.__stderr__).buffer, encoding="utf-8", errors="replace")

import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
import time
import threading
import signal
import re
import unicodedata
import hashlib
import random

# YouTube API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    HAS_YOUTUBE_API = True
    print("✅ YouTube API libraries loaded")
except ImportError:
    HAS_YOUTUBE_API = False
    print("❌ YouTube API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)

# Use local timezone instead of forcing UTC
import datetime as dt
LOCAL_TZ = dt.datetime.now().astimezone().tzinfo
UTC = timezone.utc

def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)

def _file_key(p: Path) -> str:
    st = p.stat()
    raw = f"{str(p.resolve())}|{st.st_size}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def rfc3339(dt):
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def _safe_read_json(path: Path) -> dict | None:
    try:
        with open(path, 'r', encoding='utf-8', errors='strict') as f:
            data = f.read()
            if any(ord(c) < 32 and c not in '\t\n\r' for c in data):
                raise ValueError(f"Control characters found in {path}")
            return json.load(io.StringIO(data))
    except Exception as e:
        print(f"❌ Error reading JSON from {path}: {e}")
        return None

def _safe_write_json(path: Path, data: dict) -> bool:
    try:
        with open(path, 'w', encoding='utf-8', errors='replace') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error writing JSON to {path}: {e}")
        return False

args = None  # Global for console helper

def _console(s: str) -> str:
    global args
    return s.encode("ascii", "ignore").decode("ascii") if args and getattr(args, 'ascii_console', False) else s


class YouTubeUploader:
    """Direct YouTube uploader"""
    
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/youtube.upload']
        self.youtube_service = None
        
    def setup_youtube_service(self, credentials_path, token_path):
        """Setup YouTube API service"""
        if not HAS_YOUTUBE_API:
            return False, "YouTube API libraries not installed"
        
        creds = None
        token_file = Path(token_path)
        
        if token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_file), self.scopes)
            except Exception as e:
                print(f"❌ Error loading token: {e}")
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"❌ Error refreshing token: {e}")
                    creds = None
            
            if not creds:
                credentials_file = Path(credentials_path)
                if not credentials_file.exists():
                    return False, f"Credentials file not found: {credentials_path}"
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), self.scopes)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    return False, f"Authentication failed: {e}"
            
            try:
                with open(token_path, 'w', encoding='utf-8', errors='replace') as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"⚠️ Warning: Could not save token: {e}")
        
        try:
            self.youtube_service = build('youtube', 'v3', credentials=creds)
            return True, "YouTube API service initialized"
        except Exception as e:
            return False, f"Failed to build YouTube service: {e}"
    
    def upload_video(self, video_path, title, description, privacy_status="private", 
                    category_id="25", tags=None, scheduled_publish_time=None):
        """Upload video to YouTube"""
        try:
            if not self.youtube_service:
                return None, "YouTube service not initialized"
            
            # Validate and clean title - YouTube is VERY picky
            if not title or not title.strip():
                title = "AI Generated Content"
            
            title = str(title).strip()
            
            # Remove any characters that might be problematic
            # Keep only alphanumeric, spaces, and basic punctuation
            import string
            allowed_chars = string.ascii_letters + string.digits + ' .,!?-:()[]'
            title = ''.join(c for c in title if c in allowed_chars)
            title = ' '.join(title.split())  # Normalize whitespace
            
            # Ensure title is reasonable length (YouTube max is 100 chars)
            if len(title) > 100:
                title = title[:97] + "..."
            
            if not title or len(title) < 3:
                title = "AI Generated Content"
            
            body = {
                'snippet': {
                    'title': title,
                    'description': description or "Automated content",
                    'categoryId': str(category_id)
                },
                'status': {
                    'privacyStatus': privacy_status
                }
            }
            
            if tags:
                body['snippet']['tags'] = tags
            
            if scheduled_publish_time:
                try:
                    if isinstance(scheduled_publish_time, str):
                        publish_time = datetime.fromisoformat(scheduled_publish_time.replace('Z', '+00:00'))
                    else:
                        publish_time = scheduled_publish_time
                    
                    body['status']['publishAt'] = rfc3339(publish_time)
                    print(f"   🔍 DEBUG - Scheduling for: {publish_time}")
                    print(f"   🔍 DEBUG - RFC3339: {rfc3339(publish_time)}")
                    
                except Exception as schedule_error:
                    print(f"⚠️ Schedule parsing error: {schedule_error}")
                    print("⚠️ Uploading without schedule")
            else:
                print(f"   🔍 DEBUG - No scheduled_publish_time provided")
            
            media = MediaFileUpload(
                video_path,
                chunksize=1024*1024*8,
                resumable=True,
                mimetype='video/*'
            )
            
            request = self.youtube_service.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            response = None
            retry = 0
            
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        print(f"   📊 Upload progress: {int(status.progress() * 100)}%")
                except HttpError as e:
                    if e.resp.status in [403, 500, 502, 503, 504] and retry < 5:
                        retry += 1
                        backoff = min(120, (2 ** retry) + random.uniform(0, 1))
                        print(f"   ⏳ Rate limit/server error, retry {retry}/5 in {backoff:.1f}s")
                        time.sleep(backoff)
                        continue
                    else:
                        return None, f"HTTP error {e.resp.status}: {e}"
                except Exception as e:
                    return None, f"Upload error: {e}"
            
            if response and 'id' in response:
                return response['id'], "Upload successful"
            else:
                return None, "Upload failed - no video ID received"
                
        except Exception as e:
            return None, f"Upload failed: {e}"


class SpiderCatYouTubeUploaderCLI:
    """CLI wrapper for SpiderCat YouTube uploads with disclaimers"""
    
    def __init__(self):
        self.uploader = YouTubeUploader()
        self.uploaded_log = "spidercat_uploaded_videos.json"
        self.stats = {
            'found': 0,
            'already_uploaded': 0,
            'uploaded': 0,
            'failed': 0,
            'skipped': 0,
            'with_metadata': 0
        }
        self.stop_daemon = False
        self.credentials_path = "../youtube_config/credentials.json"
        self.token_path = "../youtube_config/token.json"
        self._auth_initialized = False
        self._metadata_cache = {}

    def get_disclaimer_template(self):
        """Get the standard disclaimer template that must be appended to all descriptions"""
        return """

📋 What's This?
An unsupervised AI hooked to the news, muttering into a microphone about what it sees,  with its own backing band.
100% Satire, NOT REAL NEWS, No humans. No edits. Just Doomscroll.fm's autonomous broadcast, riding the Memescreamer engine.

🤖 Signal Chain
• 100% AI-generated, zero human curation
• Fully automated Memescreamer production pipeline

🌐 Links
Website: https://doomscroll.fm
Generator: https://memescreamer.com
Contact: info@doomscroll.fm

📄 License & Attribution
License: CC BY-NC-SA 4.0
Company: CreativeMayhem, Ltd.
Generator: Memescreamer v0.5-dev

#AI #News #Satire #Entertainment"""

    def process_gpt_script(self, gpt_script):
        """
        Process GPT script to extract title and description
        - Line 1: Title 
        - Lines 2+: Description
        - Remove # symbols from lines 1-3
        """
        if not gpt_script:
            return "AI Generated Content", "Automated content from Doomscroll.FM"
            
        try:
            # Split into lines
            script_lines = gpt_script.strip().split('\n')
            
            if not script_lines:
                return "AI Generated Content", "Automated content from Doomscroll.FM"
                
            # Extract title from first line and remove # symbols
            title = script_lines[0].strip()
            title = re.sub(r'#', '', title).strip()
            
            # Replace problematic Unicode characters with ASCII equivalents
            title = title.replace('—', '-')  # em-dash to hyphen
            title = title.replace('–', '-')  # en-dash to hyphen
            title = title.replace('"', '"')  # smart quotes to regular quotes
            title = title.replace('"', '"')
            title = title.replace(''', "'")  # smart apostrophes
            title = title.replace(''', "'")
            
            title = _nfc(title)
            
            # Ensure title is not empty after processing
            if not title or len(title) < 3:
                title = "AI Generated Content"
            
            # Extract description from remaining lines
            if len(script_lines) > 1:
                description_lines = script_lines[1:]
                
                # Remove # symbols from lines 1-3 (which are now indices 0-2 in description_lines)
                for i in range(min(3, len(description_lines))):
                    description_lines[i] = re.sub(r'#', '', description_lines[i])
                
                description = '\n'.join(description_lines).strip()
                
                # Replace problematic Unicode in description too
                description = description.replace('—', '-')
                description = description.replace('–', '-')
                description = description.replace('"', '"')
                description = description.replace('"', '"')
                description = description.replace(''', "'")
                description = description.replace(''', "'")
                
                description = _nfc(description)
            else:
                description = "Automated content from Doomscroll.FM"
                
            # Ensure description is not empty
            if not description or len(description) < 10:
                description = "Automated content from Doomscroll.FM"
                
            return title, description
            
        except Exception as e:
            print(f"⚠️ Error processing GPT script: {e}")
            return "AI Generated Content", "Automated content from Doomscroll.FM"

    def generate_hashtags(self, title, description):
        """Generate hashtags from title and description content"""
        hashtags = []
        
        # Use custom specified hashtags
        core_hashtags = ['#AI', '#News', '#Satire', '#Entertainment']
        hashtags.extend(core_hashtags)
        
        # Extract keywords from title for additional hashtags
        if title:
            # Extract words that could be hashtags (4+ characters, alphabetic)
            title_words = re.findall(r'\b[A-Za-z]{4,}\b', title)
            for word in title_words[:3]:  # Limit to 3 additional hashtags from title
                if word.lower() not in ['news', 'update', 'latest', 'breaking', 'daily']:
                    hashtags.append(f"#{word.capitalize()}")
        
        return hashtags[:15]  # YouTube hashtag limit

    def ensure_authentication(self, credentials_path="", token_path=""):
        """Ensure authentication is setup once and reused"""
        if self._auth_initialized and self.uploader.youtube_service:
            return True, "Authentication already initialized"
        
        if not credentials_path:
            credentials_path = self.credentials_path
        if not token_path:
            token_path = self.token_path
        
        success, msg = self.uploader.setup_youtube_service(credentials_path, token_path)
        if success:
            self._auth_initialized = True
        
        return success, msg

    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n🛑 Received signal {signum}. Stopping daemon...")
        self.stop_daemon = True
    
    def parse_schedule_start(self, time_str):
        """Parse schedule start time in HH:MM format"""
        if not time_str:
            return datetime.now(LOCAL_TZ)
        
        try:
            hour, minute = map(int, time_str.split(':'))
            now = datetime.now(LOCAL_TZ)
            start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if start_time <= now:
                start_time += timedelta(days=1)
            
            return start_time
        except ValueError:
            print(f"⚠️ Invalid time format: {time_str}. Using current time.")
            return datetime.now(LOCAL_TZ)
    
    def bulk_upload(self, directory_path, privacy_status="private", algorithm_optimization="trending",
                   category_id="25", credentials_path="", token_path="", dry_run=False, auto_spread=False,
                   schedule_delay=10, schedule_start="", batch=False, auto_playlist=False, limit=None):
        """Bulk upload videos from directory with SpiderCat metadata"""
        
        directory = Path(directory_path)
        if not directory.exists():
            print(f"❌ Directory not found: {directory_path}")
            return False
        
        video_files = self.find_video_files(directory)
        if not video_files:
            print(f"📁 No video files found in {directory_path}")
            return False
        
        upload_history = self.load_upload_history(directory)
        
        pending_files = []
        for video_file in video_files:
            file_key = _file_key(Path(video_file))
            if file_key not in upload_history:
                pending_files.append(video_file)
        
        if not pending_files:
            print("✅ All files have been uploaded!")
            return
        
        if limit and len(pending_files) > limit:
            pending_files = pending_files[:limit]
            print(f"📊 Limited to first {limit} files")
        
        print(f"📹 Found {len(pending_files)} videos to upload")
        
        if auto_spread and schedule_start:
            start_time = self.parse_schedule_start(schedule_start)
            base_time = start_time
        else:
            # Add 2 minutes buffer to ensure scheduling is always in the future
            base_time = datetime.now(LOCAL_TZ) + timedelta(minutes=2)
        
        first_release = base_time
        last_release = base_time + timedelta(minutes=schedule_delay * (len(pending_files) - 1))
        
        print(_console(f"🕐 First release scheduled for: {first_release.strftime('%Y-%m-%d %H:%M:%S')}"))
        print(_console(f"🕐 Last release scheduled for: {last_release.strftime('%Y-%m-%d %H:%M:%S')}"))
        print()
        
        upload_count = 0
        for i, video_path in enumerate(pending_files):
            video_path = Path(video_path)
            release_time = base_time + timedelta(minutes=schedule_delay * i) if auto_spread else None
            
            # Ensure each release time is still in the future
            if release_time and release_time <= datetime.now(LOCAL_TZ):
                release_time = datetime.now(LOCAL_TZ) + timedelta(minutes=1)
            
            print(_console(f"🎬 Processing [{i+1}/{len(pending_files)}]: {video_path.name}"))
            
            if auto_spread:
                print(_console(f"📅 Scheduled release: {release_time.strftime('%Y-%m-%d %H:%M:%S')}"))
            
            metadata_path = self.find_metadata(video_path)
            
            if dry_run:
                # Process metadata to show what would be uploaded
                if metadata_path:
                    try:
                        metadata = _safe_read_json(Path(metadata_path))
                        if metadata:
                            # Extract GPT script from ai_commentary
                            ai_commentary = metadata.get('ai_commentary', {})
                            gpt_script = ai_commentary.get('script', "")
                            
                            if gpt_script:
                                title, description = self.process_gpt_script(gpt_script)
                                if title and description:
                                    # Add disclaimer to description
                                    final_description = description + self.get_disclaimer_template()
                                    hashtags = self.generate_hashtags(title, description)
                                    
                                    print(_console(f"   📝 Title: {title[:50]}..."))
                                    print(_console(f"   📄 Description: {description[:50]}..."))
                                    print(_console(f"   🏷️ Hashtags: {', '.join(hashtags[:5])}..."))
                                    print(_console(f"   ✅ Disclaimer: INCLUDED"))
                                else:
                                    print(_console(f"   ⚠️ Could not parse GPT script"))
                            else:
                                print(_console(f"   ⚠️ No GPT script found in metadata"))
                        
                    except Exception as e:
                        print(_console(f"   ❌ Failed to load metadata: {e}"))
                        print(_console(f"   🔄 Would use fallback content"))
                else:
                    print(_console(f"   ⚠️ No metadata found - would use fallback"))
                
                print(_console("   🧪 DRY RUN - Would upload to YouTube"))
                upload_count += 1
            else:
                # Actual upload - skip dry-run purity violations
                success, setup_msg = self.ensure_authentication(credentials_path, token_path)
                if not success:
                    print(_console(f"   ❌ YouTube setup failed: {setup_msg}"))
                    upload_count += 1
                    continue
                
                # Load and process metadata
                metadata = _safe_read_json(Path(metadata_path)) if metadata_path else None
                title = f"🎧 Daily signal leakage from Doomscroll.FM - {video_path.stem}"  # Default fallback
                final_description = "Automated AI content" + self.get_disclaimer_template()  # Default fallback
                
                if metadata:
                    # Extract GPT script from ai_commentary
                    ai_commentary = metadata.get('ai_commentary', {})
                    gpt_script = ai_commentary.get('script', "")
                    
                    if gpt_script:
                        processed_title, processed_description = self.process_gpt_script(gpt_script)
                        if processed_title and processed_description:
                            # Use processed content
                            title = processed_title
                            final_description = processed_description + self.get_disclaimer_template()
                
                # Generate hashtags based on final title
                hashtags = self.generate_hashtags(title, final_description)
                
                # Upload to YouTube
                video_id, upload_result = self.uploader.upload_video(
                    video_path=str(video_path),
                    title=title,
                    description=final_description,
                    privacy_status=privacy_status,
                    tags=[tag.replace('#', '') for tag in hashtags],  # Remove # for API
                    scheduled_publish_time=release_time
                )
                
                if video_id:
                    print(_console(f"   ✅ Success! Video ID: {video_id}"))
                    print(_console(f"   🔗 URL: https://www.youtube.com/watch?v={video_id}"))
                    file_key = _file_key(video_path)
                    upload_history[file_key] = {
                        'video_id': video_id,
                        'upload_time': datetime.now().isoformat(),
                        'scheduled_time': release_time.isoformat() if release_time else None,
                        'title': title,
                        'has_disclaimer': True,
                        'file_name': video_path.name,
                        'file_size': video_path.stat().st_size,
                        'sha256': file_key
                    }
                    self.stats['uploaded'] += 1
                else:
                    print(_console(f"   ❌ Upload failed: {upload_result}"))
                    self.stats['failed'] += 1
                
                upload_count += 1
        
        # Save upload history
        if not dry_run:
            _safe_write_json(Path(directory) / self.uploaded_log, upload_history)
        
        print("-" * 60)
        print(_console("📊 BATCH UPLOAD COMPLETE:"))
        print(_console(f"   📹 Videos processed: {len(pending_files)}"))
        print(_console(f"   ✅ Successful uploads: {self.stats['uploaded']}"))
        print(_console(f"   ❌ Failed uploads: {self.stats['failed']}"))
        if auto_spread:
            total_hours = (schedule_delay * (len(pending_files) - 1)) / 60
            print(_console(f"   🕐 Release schedule: Every {schedule_delay} minutes starting {first_release.strftime('%H:%M')}"))
            print(_console(f"   📅 Content will be published over {total_hours:.1f} hours"))
        
        return True
    
    def find_video_files(self, directory):
        """Find all video files in directory - specifically *-audio.mp4 files for SpiderCat"""
        video_files = []
        
        # Primary pattern: SpiderCat audio files (*-audio.mp4)
        audio_pattern = "*-audio.mp4"
        audio_files = list(directory.glob(audio_pattern))
        video_files.extend([str(f) for f in audio_files if f.is_file()])
        
        # Fallback: other video extensions if no -audio.mp4 files found
        if not video_files:
            other_extensions = ['.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
            for ext in other_extensions:
                pattern = f"*{ext}"
                files = list(directory.glob(pattern))
                video_files.extend([str(f) for f in files if f.is_file()])
            
            # Only include regular .mp4 files if no -audio.mp4 files exist
            if not video_files:
                mp4_pattern = "*.mp4"
                mp4_files = list(directory.glob(mp4_pattern))
                video_files.extend([str(f) for f in mp4_files if f.is_file() and not f.name.endswith('-audio.mp4')])
        
        return sorted(video_files)
    
    def find_metadata(self, video_path):
        """Find corresponding JSON metadata for video"""
        video_path = Path(video_path)
        
        # For *-audio.mp4 files, remove the -audio suffix to find the base name
        if video_path.stem.endswith('-audio'):
            base_stem = video_path.stem[:-6]  # Remove '-audio' suffix
        else:
            base_stem = video_path.stem
        
        # Try different naming patterns for SpiderCat JSON files
        possible_json_paths = [
            video_path.parent / f"{base_stem}.json",  # exact base name match
            video_path.with_suffix('.json'),  # same name, .json extension  
            video_path.parent / f"{video_path.stem}.json",  # explicit stem + .json
            video_path.parent / f"{video_path.name}.json",  # full name + .json
        ]
        
        # Check each path in order of preference
        for json_path in possible_json_paths:
            if json_path.exists():
                return str(json_path)
        
        return None
    
    def load_metadata_cached(self, metadata_path):
        """Load and cache metadata to avoid re-parsing JSON files"""
        if not metadata_path:
            return None
        
        cache_key = str(metadata_path)
        if cache_key in self._metadata_cache:
            return self._metadata_cache[cache_key]
        
        metadata = _safe_read_json(Path(metadata_path))
        if metadata:
            self._metadata_cache[cache_key] = metadata
        return metadata
    
    def load_upload_history(self, directory):
        """Load upload history"""
        log_path = Path(directory) / self.uploaded_log
        if log_path.exists():
            history = _safe_read_json(log_path)
            if history:
                return history
            else:
                log_path.unlink(missing_ok=True)
        return {}
    
    def save_upload_history(self, directory, history):
        """Save upload history"""
        log_path = Path(directory) / self.uploaded_log
        return _safe_write_json(log_path, history)
    
    def upload_single_video(self, video_path, privacy_status="private", algorithm_optimization="trending", 
                           category_id="25", custom_title="", custom_description="", custom_hashtags="",
                           credentials_path="", token_path="", dry_run=False, auto_playlist=False,
                           playlist_prefix="Uploaded Content", playlist_description="Automated content uploads"):
        """Upload a single video with SpiderCat metadata and disclaimers"""
        try:
            video_path = str(video_path)
            
            print(_console(f"🎬 Processing: {Path(video_path).name}"))
            
            metadata_path = self.find_metadata(video_path)
            if metadata_path:
                print(_console(f"   📄 Found metadata: {Path(metadata_path).name}"))
                self.stats['with_metadata'] += 1
            else:
                print(_console(f"   ⚠️  No metadata found"))
            
            print(_console(f"   🔒 Privacy: {privacy_status}"))
            print(_console(f"   🎯 Algorithm: {algorithm_optimization}"))
            
            if dry_run:
                # Preview what would be uploaded
                if metadata_path:
                    try:
                        metadata = _safe_read_json(Path(metadata_path))
                        if metadata:
                            # Extract GPT script from ai_commentary
                            ai_commentary = metadata.get('ai_commentary', {})
                            gpt_script = ai_commentary.get('script', "")
                            
                            if gpt_script and not custom_title:
                                title, description = self.process_gpt_script(gpt_script)
                                if title and description:
                                    # Preview with disclaimer
                                    final_description = description + self.get_disclaimer_template()
                                    hashtags = self.generate_hashtags(title, description)
                                    
                                    print(_console(f"   📝 Title: {title[:50]}..."))
                                    print(_console(f"   📄 Description: {description[:50]}..."))
                                    print(_console(f"   🏷️ Hashtags: {', '.join(hashtags[:5])}..."))
                                    print(_console(f"   ✅ Disclaimer: INCLUDED"))
                                else:
                                    print(_console(f"   ⚠️ Could not parse GPT script"))
                            else:
                                print(_console(f"   📝 Title: {custom_title or 'Video Content'}"))
                                print(_console(f"   📄 Description: {custom_description or 'Automated content'}"))
                                print(_console(f"   ✅ Disclaimer: INCLUDED"))
                        
                    except Exception as e:
                        print(_console(f"   ❌ Failed to load metadata: {e}"))
                        print(_console(f"   📝 Title: Fallback Title"))
                        print(_console(f"   📄 Description: Fallback Content"))
                        print(_console(f"   ✅ Disclaimer: INCLUDED"))
                
                print(_console("   🧪 DRY RUN - Would upload to YouTube"))
                return {
                    "success": True,
                    "video_id": "dry_run_video_id",
                    "upload_status": "🧪 Dry run successful",
                    "final_title": "Preview Title",
                    "final_description": "Preview Description with Disclaimer"
                }
            
            # Actual upload
            if not credentials_path:
                credentials_path = str(Path(__file__).parent / "youtube_config" / "credentials.json")
            if not token_path:
                token_path = str(Path(__file__).parent / "youtube_config" / "token.json")
            
            success, setup_msg = self.ensure_authentication(credentials_path, token_path)
            if not success:
                print(_console(f"   ❌ YouTube setup failed: {setup_msg}"))
                return False
            
            # Load and process metadata
            metadata = _safe_read_json(Path(metadata_path)) if metadata_path else None
            if metadata and not custom_title and not custom_description:
                # Extract GPT script from ai_commentary
                ai_commentary = metadata.get('ai_commentary', {})
                gpt_script = ai_commentary.get('script', "")
                
                if gpt_script:
                    title, description = self.process_gpt_script(gpt_script)
                    if title and description:
                        # ALWAYS append disclaimer to GPT content
                        final_description = description + self.get_disclaimer_template()
                        hashtags = self.generate_hashtags(title, description)
                    else:
                        # Fallback if GPT processing fails
                        title = f"🎧 Daily signal leakage from Doomscroll.FM"
                        final_description = "Automated AI content" + self.get_disclaimer_template()
                        hashtags = self.generate_hashtags(title, "")
                else:
                    # Fallback if no GPT script
                    title = f"🎧 Daily signal leakage from Doomscroll.FM"
                    final_description = "Automated AI content" + self.get_disclaimer_template()
                    hashtags = self.generate_hashtags(title, "")
            else:
                # Use custom content or fallback
                title = custom_title or f"🎧 Daily signal leakage from Doomscroll.FM"
                description = custom_description or "Automated AI content"
                # ALWAYS append disclaimer even to custom content
                final_description = description + self.get_disclaimer_template()
                hashtags = custom_hashtags.split(',') if custom_hashtags else self.generate_hashtags(title, description)
            
            print(_console(f"   📝 Using title: {title[:50]}..."))
            print(_console(f"   📄 Description length: {len(final_description)} chars"))
            print(_console(f"   ✅ Disclaimer: INCLUDED"))
            
            # Upload to YouTube
            video_id, upload_result = self.uploader.upload_video(
                video_path=video_path,
                title=title,
                description=final_description,
                privacy_status=privacy_status,
                tags=[tag.replace('#', '').strip() for tag in hashtags if tag.strip()]
            )
            
            if video_id:
                print(_console(f"   ✅ Success! Video ID: {video_id}"))
                print(_console(f"   🔗 URL: https://www.youtube.com/watch?v={video_id}"))
                return {
                    "success": True,
                    "video_id": video_id,
                    "upload_status": "✅ Upload successful",
                    "final_title": title,
                    "final_description": final_description[:100] + "..." if len(final_description) > 100 else final_description,
                    "has_disclaimer": True
                }
            else:
                print(_console(f"   ❌ Upload failed: {upload_result}"))
                return {
                    "success": False,
                    "video_id": None,
                    "upload_status": f"❌ {upload_result}",
                    "error": upload_result
                }
                
        except Exception as e:
            print(_console(f"   ❌ Error uploading: {e}"))
            return {
                "success": False,
                "video_id": None,
                "upload_status": f"❌ Error: {e}",
                "error": str(e)
            }


def main():
    global args
    parser = argparse.ArgumentParser(description='SpiderCat YouTube Uploader CLI Tool')
    parser.add_argument('path', help='Path to video file or directory')
    
    parser.add_argument('--bulk', action='store_true', help='Bulk upload mode for directories')
    parser.add_argument('--dry-run', action='store_true', help='Preview uploads without actually uploading')
    parser.add_argument('--limit', type=int, help='Maximum number of files to upload')
    
    parser.add_argument('--privacy', choices=['private', 'public', 'unlisted'], default='private',
                       help='Privacy setting for uploaded videos (default: private)')
    parser.add_argument('--category', default='25', help='YouTube category ID (default: 25 - News & Politics)')
    
    parser.add_argument('--credentials', default="../youtube_config/credentials.json",
                       help='Path to YouTube API credentials file')
    parser.add_argument('--token', default="../youtube_config/token.json",
                       help='Path to YouTube API token file')
    
    parser.add_argument('--batch', action='store_true', help='Non-interactive batch mode')
    parser.add_argument('--ascii-console', action='store_true', help='Strip non-ASCII from console output')
    
    parser.add_argument('-X', '--industrial', action='store_true', 
                       help='Industrial mode: enables --bulk --auto-spread --schedule-delay 10 --batch')
    
    parser.add_argument('--auto-spread', action='store_true', help='Automatically spread uploads over time')
    parser.add_argument('--schedule-delay', type=int, default=10, help='Minutes between uploads (default: 10)')
    parser.add_argument('--schedule-start', help='Start time for uploads in HH:MM format')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    
    parser.add_argument('--auto-playlist', action='store_true', help='Automatically assign videos to daily playlists')
    parser.add_argument('--playlist-prefix', default="Doomscroll.FM", help="Playlist name prefix")
    parser.add_argument('--playlist-description', default="AI-generated content from Doomscroll.FM", help='Playlist description')
    
    args = parser.parse_args()
    
    if args.industrial:
        args.bulk = True
        args.auto_spread = True
        args.schedule_delay = 10
        args.auto_playlist = False
        args.batch = True
        args.privacy = 'private'
        print("🏭 Industrial Mode Activated: bulk + auto-spread + 10min delay + batch + private uploads")
        print("🔒 Videos upload as PRIVATE and become PUBLIC on their scheduled release times")
        print("✅ All uploads will include standard Doomscroll.FM disclaimers")
    
    path = Path(args.path)
    if not path.exists():
        print(f"❌ Path not found: {args.path}", file=sys.stderr)
        sys.exit(1)
    
    uploader = SpiderCatYouTubeUploaderCLI()
    
    if path.is_file():
        result = uploader.upload_single_video(
            video_path=str(path),
            privacy_status=args.privacy,
            credentials_path=args.credentials,
            token_path=args.token,
            dry_run=args.dry_run,
            auto_playlist=args.auto_playlist,
            playlist_prefix=args.playlist_prefix,
            playlist_description=args.playlist_description
        )
        
        if result and result["success"]:
            print("✅ Upload completed successfully!")
            if result.get("has_disclaimer"):
                print("✅ Disclaimer properly included!")
        else:
            print("❌ Upload failed!", file=sys.stderr)
            sys.exit(1)
            
    elif path.is_dir():
        if not args.bulk:
            print("❌ Invalid usage:", file=sys.stderr)
            print("   - For single file: python spidercat_youtube_uploader_cli.py video.mp4", file=sys.stderr)
            print("   - For bulk upload: python spidercat_youtube_uploader_cli.py directory/ --bulk", file=sys.stderr)
            sys.exit(1)
        else:
            uploader.bulk_upload(
                directory_path=str(path),
                privacy_status=args.privacy,
                credentials_path=args.credentials,
                token_path=args.token,
                dry_run=args.dry_run,
                auto_spread=args.auto_spread,
                schedule_delay=args.schedule_delay,
                schedule_start=args.schedule_start,
                batch=args.batch,
                auto_playlist=args.auto_playlist,
                limit=args.limit
            )
    else:
        print(f"❌ Invalid path: {args.path}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
