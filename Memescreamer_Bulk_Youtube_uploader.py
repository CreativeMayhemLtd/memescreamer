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

YouTube Uploader CLI Tool
Automated video uploads with metadata support

Usage:
    python youtube_uploader.py [video_file_or_directory] [options]
    
Examples:
    python youtube_uploader.py "video.mp4"
    python youtube_uploader.py "video_directory/" --bulk
    python youtube_uploader.py "video_directory/" --bulk --dry-run
    python youtube_uploader.py "video_directory/" -X --limit 10
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import time
import threading
import signal

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
                with open(token_path, 'w') as token:
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
            
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'categoryId': category_id
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
                    
                    body['status']['publishAt'] = publish_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                    
                except Exception as schedule_error:
                    print(f"⚠️ Schedule parsing error: {schedule_error}")
                    print("⚠️ Uploading without schedule")
            
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
                    if e.resp.status in [500, 502, 503, 504] and retry < 3:
                        retry += 1
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


class YouTubeUploaderCLI:
    """CLI wrapper for YouTube uploads with metadata"""
    
    def __init__(self):
        self.uploader = YouTubeUploader()
        self.uploaded_log = "uploaded_videos.json"
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
            return datetime.now()
        
        try:
            hour, minute = map(int, time_str.split(':'))
            now = datetime.now()
            start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if start_time <= now:
                start_time += timedelta(days=1)
            
            return start_time
        except ValueError:
            print(f"⚠️ Invalid time format: {time_str}. Using current time.")
            return datetime.now()
    
    def bulk_upload(self, directory_path, privacy_status="private", algorithm_optimization="trending",
                   category_id="25", credentials_path="", token_path="", dry_run=False, auto_spread=False,
                   schedule_delay=10, schedule_start="", batch=False, auto_playlist=False, limit=None):
        """Bulk upload videos from directory"""
        
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
            file_key = str(Path(video_file).name)
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
            base_time = datetime.combine(datetime.now().date(), start_time.time())
        else:
            base_time = datetime.now()
        
        first_release = base_time
        last_release = base_time + timedelta(minutes=schedule_delay * (len(pending_files) - 1))
        
        print(f"🕐 First release scheduled for: {first_release.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🕐 Last release scheduled for: {last_release.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        upload_count = 0
        for i, video_path in enumerate(pending_files):
            video_path = Path(video_path)
            release_time = base_time + timedelta(minutes=schedule_delay * i) if auto_spread else None
            
            print(f"🎬 Processing [{i+1}/{len(pending_files)}]: {video_path.name}")
            
            if auto_spread:
                print(f"📅 Scheduled release: {release_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            metadata_path = self.find_metadata(video_path)
            
            if dry_run:
                if metadata_path:
                    try:
                        metadata = self.load_metadata_cached(metadata_path)
                        if metadata:
                            metadata_content = metadata.get('content', {})
                            content_script = metadata_content.get('script', "")
                            
                            if content_script:
                                try:
                                    content_script = content_script.encode().decode('unicode_escape')
                                except:
                                    pass
                                
                                script_lines = content_script.strip().split('\n')
                                preview_title = script_lines[0].strip() if script_lines else f"Video - {video_path.stem}"
                                raw_description = '\n'.join(script_lines[1:]).strip() if len(script_lines) > 1 else ""
                                preview_description = raw_description.replace('#', '').strip()
                            else:
                                preview_title = f"Video - {video_path.stem}"
                                preview_description = "Automated video content"
                            
                            print(f"   📝 Title: {preview_title}")
                            print(f"   📄 Description: {preview_description[:100]}...")
                        
                    except Exception as e:
                        print(f"   🧪 DRY RUN - Would upload with scheduled release")
                        print(f"   ⚠️  Could not preview content: {e}")
                    
                    upload_count += 1
                else:
                    success, setup_msg = self.ensure_authentication(credentials_path, token_path)
                    if not success:
                        print(f"   ❌ YouTube setup failed: {setup_msg}")
                        upload_count += 1
                        continue
                        
                    metadata = self.load_metadata_cached(metadata_path)
                    if metadata:
                        metadata_content = metadata.get('content', {})
                        content_script = metadata_content.get('script', "")
                        
                        if content_script:
                            try:
                                content_script = content_script.encode().decode('unicode_escape')
                            except:
                                pass
                            
                            script_lines = content_script.strip().split('\n')
                            title = script_lines[0].strip() if script_lines else "Video Content"
                            raw_description = '\n'.join(script_lines[1:]).strip() if len(script_lines) > 1 else ""
                        else:
                            title = "Video Content"
                            raw_description = "Automated content upload"
                        
                        description = raw_description.replace('#', '').strip() if raw_description else raw_description
                        
                        # Add Memescreamer attribution
                        if description:
                            description += "\n\nUploaded by Memescreamer - http://www.memescreamer.com"
                        else:
                            description = "Uploaded by Memescreamer - http://www.memescreamer.com"
                    else:
                        title = "Daily AI Content"
                        description = "Automated content upload\n\nUploaded by Memescreamer - http://www.memescreamer.com"
                    
                    video_id, upload_result = self.uploader.upload_video(
                        video_path=str(video_path),
                        title=title,
                        description=description,
                        privacy_status=privacy_status,
                        scheduled_publish_time=release_time
                    )
                    
                    if video_id:
                        print(f"   ✅ Success! Video ID: {video_id}")
                        upload_history[video_path.name] = {
                            'video_id': video_id,
                            'upload_time': datetime.now().isoformat(),
                            'scheduled_time': release_time.isoformat() if release_time else None
                        }
                        self.stats['uploaded'] += 1
                    else:
                        print(f"   ❌ Upload failed: {upload_result}")
                        self.stats['failed'] += 1
                    
                    upload_count += 1
        
        self.save_upload_history(directory, upload_history)
        
        print("-" * 60)
        print("📊 BATCH UPLOAD COMPLETE:")
        print(f"   📹 Videos processed: {len(pending_files)}")
        if auto_spread:
            total_hours = (schedule_delay * (len(pending_files) - 1)) / 60
            print(f"   🕐 Release schedule: Every {schedule_delay} minutes starting {first_release.strftime('%H:%M')}")
            print(f"   📅 Content will be published over {total_hours:.1f} hours")
        
        return True
    
    def find_video_files(self, directory):
        """Find all video files in directory"""
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        video_files = []
        
        for ext in video_extensions:
            pattern = f"*{ext}"
            files = list(directory.glob(pattern))
            video_files.extend([str(f) for f in files if f.is_file()])
        
        return sorted(video_files)
    
    def find_metadata(self, video_path):
        """Find corresponding JSON metadata for video"""
        video_path = Path(video_path)
        
        video_stem = video_path.stem
        if "-audio" in video_stem:
            base_name = video_stem.replace("-audio", "")
        else:
            base_name = video_stem
        
        json_path = video_path.parent / f"{base_name}.json"
        if json_path.exists():
            return str(json_path)
        
        json_path = video_path.with_suffix('.json')
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
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                self._metadata_cache[cache_key] = metadata
                return metadata
        except Exception as e:
            print(f"❌ Error loading metadata from {metadata_path}: {e}")
            return None
    
    def load_upload_history(self, directory):
        """Load upload history"""
        log_path = Path(directory) / self.uploaded_log
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Could not load upload history: {e}")
                log_path.unlink(missing_ok=True)
        return {}
    
    def save_upload_history(self, directory, history):
        """Save upload history"""
        log_path = Path(directory) / self.uploaded_log
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Could not save upload history: {e}")
    
    def upload_single_video(self, video_path, privacy_status="private", algorithm_optimization="trending", 
                           category_id="25", custom_title="", custom_description="", custom_hashtags="",
                           credentials_path="", token_path="", dry_run=False, auto_playlist=False,
                           playlist_prefix="Uploaded Content", playlist_description="Automated content uploads"):
        """Upload a single video with metadata"""
        try:
            video_path = str(video_path)
            
            print(f"🎬 Processing: {Path(video_path).name}")
            
            metadata_path = self.find_metadata(video_path)
            if metadata_path:
                print(f"   📄 Found metadata: {Path(metadata_path).name}")
                self.stats['with_metadata'] += 1
            else:
                print(f"   ⚠️  No metadata found")
            
            print(f"   🔒 Privacy: {privacy_status}")
            print(f"   🎯 Algorithm: {algorithm_optimization}")
            
            if dry_run:
                try:
                    if metadata_path:
                        metadata = self.load_metadata_cached(metadata_path)
                        if metadata:
                            metadata_content = metadata.get('content', {})
                            content_script = metadata_content.get('script', "")
                            
                            if content_script and not custom_title:
                                try:
                                    content_script = content_script.encode().decode('unicode_escape')
                                except:
                                    pass
                                
                                script_lines = content_script.strip().split('\n')
                                preview_title = script_lines[0].strip() if script_lines else f"Video - {Path(video_path).stem}"
                            else:
                                preview_title = custom_title or f"Video - {Path(video_path).stem}"
                            
                            if content_script and not custom_description:
                                if 'unicode_escape' not in str(type(content_script)):
                                    try:
                                        content_script = content_script.encode().decode('unicode_escape')
                                    except:
                                        pass
                                
                                script_lines = content_script.strip().split('\n')
                                raw_description = '\n'.join(script_lines[1:]).strip() if len(script_lines) > 1 else ""
                                preview_description = raw_description.replace('#', '').strip()
                            else:
                                preview_description = custom_description or "Automated content upload"
                            
                            print(f"   📝 Title: {preview_title}")
                            print(f"   📄 Description: {preview_description[:100]}...")
                        
                except Exception as e:
                    print(f"   ❌ Failed to load metadata: {e}")
                    print(f"   📝 Title: Video - {Path(video_path).stem}")
                    print(f"   📄 Description: Automated content upload")
                
                print("   🧪 DRY RUN - Would upload to YouTube")
                return {
                    "success": True,
                    "video_id": "dry_run_video_id",
                    "upload_status": "🧪 Dry run successful",
                    "final_title": preview_title if 'preview_title' in locals() else "Episode",
                    "final_description": preview_description if 'preview_description' in locals() else "Automated content"
                }
            
            if not credentials_path:
                credentials_path = str(Path(__file__).parent / "youtube_config" / "credentials.json")
            if not token_path:
                token_path = str(Path(__file__).parent / "youtube_config" / "token.json")
            
            success, setup_msg = self.ensure_authentication(credentials_path, token_path)
            if not success:
                print(f"   ❌ YouTube setup failed: {setup_msg}")
                return False
                
            metadata = self.load_metadata_cached(metadata_path)
            if metadata:
                metadata_content = metadata.get('content', {})
                content_script = metadata_content.get('script', "")
                
                if content_script:
                    try:
                        content_script = content_script.encode().decode('unicode_escape')
                    except:
                        pass
                    
                    script_lines = content_script.strip().split('\n')
                    title = script_lines[0].strip() if script_lines else "Video Content"
                    raw_description = '\n'.join(script_lines[1:]).strip() if len(script_lines) > 1 else ""
                else:
                    title = "Video Content"
                    raw_description = "Automated content upload"
                
                description = raw_description.replace('#', '').strip() if raw_description else raw_description
                
                # Add Memescreamer attribution
                if description:
                    description += "\n\nUploaded by Memescreamer - http://www.memescreamer.com"
                else:
                    description = "Uploaded by Memescreamer - http://www.memescreamer.com"
            else:
                title = "Video Content"
                description = "Automated content upload\n\nUploaded by Memescreamer - http://www.memescreamer.com"
            
            video_id, upload_result = self.uploader.upload_video(
                video_path=video_path,
                title=title,
                description=description,
                privacy_status=privacy_status
            )
            
            if video_id:
                print(f"   ✅ Success! Video ID: {video_id}")
                return {
                    "success": True,
                    "video_id": video_id,
                    "upload_status": "✅ Upload successful",
                    "final_title": title,
                    "final_description": description[:100] + "..." if len(description) > 100 else description
                }
            else:
                print(f"   ❌ Upload failed: {upload_result}")
                return {
                    "success": False,
                    "video_id": None,
                    "upload_status": f"❌ {upload_result}",
                    "error": upload_result
                }
                
        except Exception as e:
            print(f"   ❌ Error uploading: {e}")
            return {
                "success": False,
                "video_id": None,
                "upload_status": f"❌ Error: {e}",
                "error": str(e)
            }


def main():
    parser = argparse.ArgumentParser(description='YouTube Uploader CLI Tool')
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
    
    parser.add_argument('-X', '--industrial', action='store_true', 
                       help='Industrial mode: enables --bulk --auto-spread --schedule-delay 10 --batch')
    
    parser.add_argument('--auto-spread', action='store_true', help='Automatically spread uploads over time')
    parser.add_argument('--schedule-delay', type=int, default=10, help='Minutes between uploads (default: 10)')
    parser.add_argument('--schedule-start', help='Start time for uploads in HH:MM format')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    
    parser.add_argument('--auto-playlist', action='store_true', help='Automatically assign videos to daily playlists')
    parser.add_argument('--playlist-prefix', default="Uploaded Content", help="Playlist name prefix")
    parser.add_argument('--playlist-description', default="Automated content uploads", help='Playlist description')
    
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
    
    path = Path(args.path)
    if not path.exists():
        print(f"❌ Path not found: {args.path}")
        sys.exit(1)
    
    uploader = YouTubeUploaderCLI()
    
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
        else:
            print("❌ Upload failed!")
            sys.exit(1)
            
    elif path.is_dir():
        if not args.bulk:
            print("❌ Invalid usage:")
            print("   - For single file: python youtube_uploader.py video.mp4")
            print("   - For bulk upload: python youtube_uploader.py directory/ --bulk")
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
        print(f"❌ Invalid path: {args.path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
