import os
import sys
import cv2
import argparse
import tempfile
import shutil
import subprocess
import re
import time
import json
from pathlib import Path
try:
    import pyexiv2
    HAVE_PYEXIV2 = True
except ImportError:
    HAVE_PYEXIV2 = False

try:
    import ffmpeg
    HAVE_FFMPEG = True
except ImportError:
    HAVE_FFMPEG = False

class MeshroomVideoPlugin:
    """
    Plugin for Meshroom to process video files and generate 3D models.
    This plugin extracts frames from a video file and feeds them into Meshroom's photogrammetry pipeline.
    """
    
    def __init__(self, video_path, output_dir, frame_interval=1, quality='high', meshroom_bin=None):
        """
        Initialize the plugin with the given parameters.
        
        Args:
            video_path (str): Path to the input video file
            output_dir (str): Path to the output directory for the 3D model
            frame_interval (int): Extract a frame every N frames (default: 1)
            quality (str): Quality setting for the 3D model ('low', 'medium', 'high')
            meshroom_bin (str): Path to the Meshroom binary, if not in PATH
        """
        self.video_path = video_path
        self.output_dir = os.path.abspath(output_dir)  # Use absolute path
        self.frame_interval = frame_interval
        self.quality = quality
        
        # Try to find Meshroom binary
        if meshroom_bin:
            self.meshroom_bin = meshroom_bin
        else:
            # Try to find meshroom in PATH
            self.meshroom_bin = self._find_meshroom_binary()
            
        # Create temporary directory for extracted frames
        self.temp_frames_dir = tempfile.mkdtemp(prefix="meshroom_video_")
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Check for required dependencies
        if not HAVE_PYEXIV2:
            print("Warning: pyexiv2 library not found. Metadata extraction will be limited.")
            print("To enable full metadata support, install pyexiv2: pip install pyexiv2")

        if not HAVE_FFMPEG:
            print("Warning: ffmpeg-python library not found. Some metadata extraction features will be limited.")
            print("To enable full metadata support, install ffmpeg-python: pip install ffmpeg-python")

        # Try to find exiftool for advanced metadata extraction
        self.exiftool_path = self._find_exiftool_binary()
        if not self.exiftool_path:
            print("Warning: exiftool not found. Advanced metadata extraction will be limited.")
            print("To enable full metadata support, install exiftool: https://exiftool.org/")
        
    def _find_meshroom_binary(self):
        """Find Meshroom binary in common locations"""
        # Common locations for Meshroom binary
        common_locations = [
            "meshroom",  # If in PATH
            r"C:\Program Files\Meshroom\meshroom.exe",  # Windows
            r"C:\Program Files (x86)\Meshroom\meshroom.exe",  # Windows 32-bit
            r"C:\Program Files\AliceVision\Meshroom\meshroom.exe",  # Windows AliceVision
            "/usr/local/bin/meshroom",  # Linux
            "/Applications/Meshroom.app/Contents/MacOS/meshroom"  # macOS
        ]
        
        for location in common_locations:
            try:
                # Check if the binary exists and is executable
                if os.path.isfile(location) and os.access(location, os.X_OK):
                    return location
                # Try to run the command
                subprocess.run([location, "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return location
            except (FileNotFoundError, PermissionError, subprocess.SubprocessError):
                continue
                
        raise FileNotFoundError(
            "Meshroom binary not found. Please install Meshroom or provide the path to the binary."
        )

    def _find_exiftool_binary(self):
        """Find exiftool binary in common locations"""
        # Common locations for exiftool binary
        common_locations = [
            "exiftool",  # If in PATH
            r"C:\Program Files\exiftool\exiftool.exe",  # Windows
            r"C:\exiftool\exiftool.exe",  # Windows common install location
            "/usr/local/bin/exiftool",  # Linux
            "/usr/bin/exiftool",  # Linux
            "/opt/local/bin/exiftool",  # macOS Homebrew
            "/opt/homebrew/bin/exiftool",  # macOS Homebrew on Apple Silicon
        ]
        
        for location in common_locations:
            try:
                # Check if the binary exists and is executable
                if os.path.isfile(location) and os.access(location, os.X_OK):
                    return location
                # Try to run the command
                result = subprocess.run([location, "-ver"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode == 0:
                    return location
            except (FileNotFoundError, PermissionError, subprocess.SubprocessError):
                continue
                
        return None  # Return None if not found

    def _extract_video_metadata(self):
        """Extract metadata from video file"""
        print(f"Extracting metadata from video file: {self.video_path}")
        metadata = {}
        
        try:
            # Method 1: Use ffmpeg if available
            if HAVE_FFMPEG:
                try:
                    probe = ffmpeg.probe(self.video_path)
                    metadata['ffmpeg'] = probe
                    print(f"Successfully extracted ffmpeg metadata")
                except Exception as e:
                    print(f"Failed to extract ffmpeg metadata: {str(e)}")
            
            # Method 2: Use exiftool if available
            if self.exiftool_path:
                try:
                    cmd = [self.exiftool_path, "-j", "-g", self.video_path]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        exif_data = json.loads(result.stdout)
                        if exif_data and len(exif_data) > 0:
                            metadata['exiftool'] = exif_data[0]
                            print(f"Successfully extracted exiftool metadata")
                except Exception as e:
                    print(f"Failed to extract exiftool metadata: {str(e)}")
            
            # Method 3: Use OpenCV
            try:
                cap = cv2.VideoCapture(self.video_path)
                metadata['opencv'] = {
                    'fps': cap.get(cv2.CAP_PROP_FPS),
                    'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                    'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                }
                cap.release()
                print(f"Successfully extracted OpenCV metadata")
            except Exception as e:
                print(f"Failed to extract OpenCV metadata: {str(e)}")
                
            # Print summary of extracted metadata
            gps_info = self._extract_gps_from_metadata(metadata)
            if gps_info:
                print(f"Found GPS information in video: {gps_info}")
            else:
                print("No GPS information found in video metadata")
                
            return metadata
            
        except Exception as e:
            print(f"Warning: Failed to extract metadata from video: {str(e)}")
            return {}
            
    def _extract_gps_from_metadata(self, metadata):
        """Extract GPS information from metadata"""
        gps_info = {}
        
        # Try exiftool metadata first
        if 'exiftool' in metadata:
            exif = metadata['exiftool']
            
            # GPS data could be in different tags depending on video format
            if 'GPS' in exif:
                gps = exif['GPS']
                if 'GPSLatitude' in gps and 'GPSLongitude' in gps:
                    gps_info['latitude'] = gps['GPSLatitude']
                    gps_info['longitude'] = gps['GPSLongitude']
                    if 'GPSAltitude' in gps:
                        gps_info['altitude'] = gps['GPSAltitude']
            
            # Try composite data
            elif 'Composite' in exif:
                comp = exif['Composite']
                if 'GPSLatitude' in comp and 'GPSLongitude' in comp:
                    gps_info['latitude'] = comp['GPSLatitude']
                    gps_info['longitude'] = comp['GPSLongitude']
                    if 'GPSAltitude' in comp:
                        gps_info['altitude'] = comp['GPSAltitude']
                        
            # Try QuickTime metadata (for drone videos often)
            elif 'QuickTime' in exif:
                qt = exif['QuickTime']
                if 'GPSCoordinates' in qt:
                    coords = qt['GPSCoordinates']
                    if isinstance(coords, str):
                        # Format could be "lat, long, alt"
                        parts = coords.split(',')
                        if len(parts) >= 2:
                            gps_info['latitude'] = parts[0].strip()
                            gps_info['longitude'] = parts[1].strip()
                            if len(parts) >= 3:
                                gps_info['altitude'] = parts[2].strip()
        
        # Try ffmpeg metadata if available
        if not gps_info and 'ffmpeg' in metadata:
            probe = metadata['ffmpeg']
            if 'format' in probe and 'tags' in probe['format']:
                tags = probe['format']['tags']
                
                # Look for various GPS tag formats
                for key in tags:
                    if 'gps' in key.lower() or 'location' in key.lower():
                        gps_info['raw'] = tags[key]
                
                # Explicit checks for common tag names
                if 'location' in tags:
                    gps_info['raw_location'] = tags['location']
                    
                if 'com.apple.quicktime.location.ISO6709' in tags:
                    gps_info['apple_location'] = tags['com.apple.quicktime.location.ISO6709']
        
        return gps_info
    
    def _apply_metadata_to_image(self, image_path, frame_num, video_metadata, timestamp=None):
        """Apply video metadata to extracted image file"""
        if not HAVE_PYEXIV2:
            return False
            
        try:
            gps_info = self._extract_gps_from_metadata(video_metadata)
            if not gps_info:
                return False
                
            # Open the image for metadata editing
            img = pyexiv2.Image(image_path)
            
            # Create XMP metadata if needed
            xmp_metadata = {}
            
            # Add basic metadata
            xmp_metadata['Xmp.xmp.CreateDate'] = timestamp.isoformat() if timestamp else time.strftime("%Y-%m-%dT%H:%M:%S")
            xmp_metadata['Xmp.xmp.CreatorTool'] = "Meshroom Video Plugin"
            
            # Add GPS metadata if available
            if 'latitude' in gps_info and 'longitude' in gps_info:
                try:
                    # Convert latitude and longitude to the format required by Exiv2
                    latitude = float(gps_info['latitude'])
                    longitude = float(gps_info['longitude'])
                    
                    # EXIF GPS metadata
                    img.modify_exif({
                        'Exif.GPSInfo.GPSLatitudeRef': 'N' if latitude >= 0 else 'S',
                        'Exif.GPSInfo.GPSLatitude': abs(latitude),
                        'Exif.GPSInfo.GPSLongitudeRef': 'E' if longitude >= 0 else 'W',
                        'Exif.GPSInfo.GPSLongitude': abs(longitude),
                    })
                    
                    # XMP GPS metadata
                    xmp_metadata['Xmp.exif.GPSLatitude'] = abs(latitude)
                    xmp_metadata['Xmp.exif.GPSLongitude'] = abs(longitude)
                    
                    # Add altitude if available
                    if 'altitude' in gps_info:
                        try:
                            altitude = float(gps_info['altitude'])
                            img.modify_exif({
                                'Exif.GPSInfo.GPSAltitudeRef': '0' if altitude >= 0 else '1',
                                'Exif.GPSInfo.GPSAltitude': abs(altitude),
                            })
                            xmp_metadata['Xmp.exif.GPSAltitude'] = abs(altitude)
                        except (ValueError, TypeError):
                            pass
                except (ValueError, TypeError) as e:
                    print(f"Warning: Could not convert GPS coordinates to float: {str(e)}")
            
            # Apply XMP metadata
            if xmp_metadata:
                img.modify_xmp(xmp_metadata)
                
            # Close the image to save changes
            img.close()
            return True
            
        except Exception as e:
            print(f"Warning: Failed to apply metadata to image: {str(e)}")
            return False
    
    def extract_frames(self):
        """Extract frames from the video file"""
        print(f"Extracting frames from {self.video_path}...")
        
        # Extract metadata from video
        video_metadata = self._extract_video_metadata()
        
        # Open the video file
        video = cv2.VideoCapture(self.video_path)
        
        # Check if video opened successfully
        if not video.isOpened():
            raise ValueError(f"Could not open video file: {self.video_path}")
            
        # Get video properties
        frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = video.get(cv2.CAP_PROP_FPS)
        
        print(f"Video info: {frame_count} frames, {fps} FPS")
        
        # Calculate the total number of frames to extract
        frames_to_extract = frame_count // self.frame_interval
        
        print(f"Extracting approximately {frames_to_extract} frames...")
        
        # Extract frames
        count = 0
        extracted = 0
        while True:
            success, frame = video.read()
            if not success:
                break
                
            if count % self.frame_interval == 0:
                # Calculate timestamp for this frame
                timestamp = time.time() - ((frame_count - count) / fps) if fps > 0 else None
                
                # Save frame as a JPG file
                frame_path = os.path.join(self.temp_frames_dir, f"frame_{extracted:06d}.jpg")
                cv2.imwrite(frame_path, frame)
                
                # Apply metadata to the saved image
                metadata_applied = self._apply_metadata_to_image(frame_path, extracted, video_metadata, timestamp)
                
                extracted += 1
                
                # Print progress every 10 frames or when it's a multiple of 10%
                if extracted % 10 == 0 or (frames_to_extract > 0 and extracted * 100 // frames_to_extract % 10 == 0):
                    percent = (extracted * 100) // frames_to_extract if frames_to_extract > 0 else 0
                    meta_status = "with metadata" if metadata_applied else "without metadata"
                    print(f"[{percent}%] Extracted {extracted} frames {meta_status}...")
                    
            count += 1
            
        # Release video
        video.release()
        
        print(f"[100%] Extracted {extracted} frames in total.")
        return extracted
        
    def run_meshroom(self):
        """Run Meshroom on the extracted frames"""
        print(f"Running Meshroom on extracted frames...")
        print(f"This may take a long time depending on your computer and the quality settings.")
        print(f"Quality setting: {self.quality}")
        print(f"Output directory: {self.output_dir}")
        
        # Get output project path
        output_project = os.path.join(self.output_dir, "project.mg")
        
        # Construct the command based on Meshroom CLI
        cmd = [
            self.meshroom_bin,
            "-i", self.temp_frames_dir,  # Import images
            "-s", output_project         # Save project
        ]
        
        # Add pipeline/quality settings
        if self.quality == 'low':
            pipeline = "photogrammetryDraft"
        elif self.quality == 'medium':
            pipeline = "photogrammetry"
        else:  # high
            pipeline = "photogrammetryAndCameraTracking"
            
        cmd.extend(["-p", pipeline])
        
        # Run Meshroom
        print(f"Running command: {' '.join(cmd)}")
        print("-" * 60)
        print(f"Starting Meshroom processing pipeline: {pipeline}")
        print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            
            # Status patterns to detect progress
            stage_pattern = re.compile(r"Processing node: (\w+)")
            percent_pattern = re.compile(r"(\d+)%")
            feature_pattern = re.compile(r"Features: (\d+)/(\d+)")
            task_pattern = re.compile(r"\[([^\]]+)\]")
            
            current_stage = "Initializing"
            current_percent = 0
            start_time = time.time()
            last_update_time = start_time
            
            # Print output in real-time with progress estimation
            for line in process.stdout:
                # Update stage if found
                stage_match = stage_pattern.search(line)
                if stage_match:
                    current_stage = stage_match.group(1)
                    print(f"\n[{time.strftime('%H:%M:%S')}] Stage: {current_stage}")
                
                # Update percent if found
                percent_match = percent_pattern.search(line)
                if percent_match:
                    new_percent = int(percent_match.group(1))
                    if new_percent != current_percent:
                        current_percent = new_percent
                        elapsed = time.time() - start_time
                        time_per_percent = elapsed / max(current_percent, 1)
                        remaining = time_per_percent * (100 - current_percent)
                        
                        # Format time remaining
                        if remaining > 3600:
                            time_str = f"{int(remaining/3600)}h {int((remaining%3600)/60)}m"
                        elif remaining > 60:
                            time_str = f"{int(remaining/60)}m {int(remaining%60)}s"
                        else:
                            time_str = f"{int(remaining)}s"
                            
                        print(f"[{current_stage}] Progress: {current_percent}% - Est. remaining: {time_str}")
                
                # Check for feature extraction progress
                feature_match = feature_pattern.search(line)
                if feature_match:
                    done = int(feature_match.group(1))
                    total = int(feature_match.group(2))
                    if total > 0:
                        percent = (done * 100) // total
                        print(f"[Feature extraction] {done}/{total} images ({percent}%)")
                
                # Check for task information
                task_match = task_pattern.search(line)
                if task_match:
                    task = task_match.group(1).strip()
                    if "error" in task.lower() or "warning" in task.lower():
                        print(f"\n[!] {line.strip()}")
                    
                # Print informative lines
                if "error" in line.lower() or "warning" in line.lower() or "exception" in line.lower():
                    print(f"\n[!] {line.strip()}")
                elif ("creating" in line.lower() or "computing" in line.lower() or 
                      "processing" in line.lower() or "starting" in line.lower()):
                    print(line.strip())
                
                # Periodically check for new cache directories
                current_time = time.time()
                if current_time - last_update_time > 30:  # Check every 30 seconds
                    self._check_output_directories()
                    last_update_time = current_time
                
            # Wait for process to complete
            process.wait()
            
            if process.returncode != 0:
                stderr = process.stderr.read()
                raise subprocess.SubprocessError(f"Meshroom failed with error: {stderr}")
            
            elapsed_time = time.time() - start_time
            hours, remainder = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            print("-" * 60)
            print(f"Meshroom processing completed in {int(hours)}h {int(minutes)}m {int(seconds)}s")
            print(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 60)
                
        except Exception as e:
            raise RuntimeError(f"Failed to run Meshroom: {str(e)}")
    
    def _check_output_directories(self):
        """Check for Meshroom cache directories and output files"""
        cache_dir = os.path.join(self.output_dir, "MeshroomCache")
        
        if os.path.exists(cache_dir):
            stages = [d for d in os.listdir(cache_dir) if os.path.isdir(os.path.join(cache_dir, d))]
            if stages:
                print(f"\n[Output] Found {len(stages)} processing stages in MeshroomCache:")
                for stage in stages:
                    print(f"  - {stage}")
    
    def cleanup(self):
        """Clean up temporary files"""
        print(f"Cleaning up temporary files...")
        try:
            shutil.rmtree(self.temp_frames_dir)
            print(f"Temporary files removed: {self.temp_frames_dir}")
        except Exception as e:
            print(f"Warning: Could not clean up temporary files: {str(e)}")
        
    def process(self):
        """Process the video and generate 3D model"""
        try:
            # Extract frames
            extracted_count = self.extract_frames()
            
            if extracted_count == 0:
                raise ValueError("No frames were extracted from the video.")
                
            # Run Meshroom
            self.run_meshroom()
            
            # Check for output files
            print("\nLooking for output files...")
            
            # Potential locations for output files
            meshroom_cache = os.path.join(self.output_dir, "MeshroomCache")
            texturing_dir = None
            
            # Look for the Texturing directory
            if os.path.exists(meshroom_cache):
                texturing_dirs = [d for d in os.listdir(meshroom_cache) if "texturing" in d.lower()]
                if texturing_dirs:
                    # Get the most recent Texturing directory
                    texturing_base = texturing_dirs[0]
                    texturing_path = os.path.join(meshroom_cache, texturing_base)
                    
                    # Look for specific texturing run in subdirectories
                    if os.path.isdir(texturing_path):
                        subdirs = [d for d in os.listdir(texturing_path) if os.path.isdir(os.path.join(texturing_path, d))]
                        if subdirs:
                            # Sort by modification time (newest first)
                            sorted_dirs = sorted(subdirs, key=lambda d: os.path.getmtime(os.path.join(texturing_path, d)), reverse=True)
                            texturing_dir = os.path.join(texturing_path, sorted_dirs[0])
            
            # Look for model files
            output_files = []
            
            if texturing_dir and os.path.isdir(texturing_dir):
                # Look for model files in the Texturing output
                output_files = [f for f in os.listdir(texturing_dir) if f.endswith(('.obj', '.mtl', '.abc', '.ply'))]
                if output_files:
                    print(f"\nFound {len(output_files)} model files in {texturing_dir}:")
                    for file in output_files:
                        file_path = os.path.join(texturing_dir, file)
                        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
                        print(f"  - {file} ({file_size:.2f} MB)")
                    
                    # Return the main model file path
                    model_file = next((f for f in output_files if f.endswith('.obj')), None)
                    if model_file:
                        output_path = os.path.join(texturing_dir, model_file)
                        print(f"\n3D model successfully generated: {output_path}")
                        return output_path
            
            # If no specific model files found, check project file
            project_file = os.path.join(self.output_dir, "project.mg")
            if os.path.exists(project_file):
                print(f"\nMeshroom project file created: {project_file}")
                print(f"You can open this file in Meshroom UI to view the results or continue processing.")
                return project_file
            
            # If nothing specific found
            print(f"\nProcessing completed, but no specific output files were identified.")
            print(f"Check the output directory for results: {self.output_dir}")
            return self.output_dir
                
        finally:
            # Clean up temporary files
            self.cleanup()


def main():
    """Main function for command-line interface"""
    parser = argparse.ArgumentParser(description="Meshroom Video Plugin - Process videos to create 3D models")
    
    parser.add_argument("video", help="Path to input video file")
    parser.add_argument("output", help="Path to output directory")
    
    parser.add_argument("--frame-interval", type=int, default=15,
                        help="Extract a frame every N frames (default: 15)")
    parser.add_argument("--quality", choices=["low", "medium", "high"], default="high",
                        help="Quality setting for 3D model (default: high)")
    parser.add_argument("--meshroom-bin", help="Path to Meshroom binary")
    parser.add_argument("--keep-metadata", action="store_true", 
                        help="Preserve metadata from video in extracted frames (requires pyexiv2)")
    
    args = parser.parse_args()
    
    try:
        plugin = MeshroomVideoPlugin(
            args.video,
            args.output,
            frame_interval=args.frame_interval,
            quality=args.quality,
            meshroom_bin=args.meshroom_bin
        )
        
        plugin.process()
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
        
    sys.exit(0)
    

if __name__ == "__main__":
    main()