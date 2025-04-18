import os
import sys
import cv2
import argparse
import tempfile
import shutil
import subprocess
import json
import time
import re
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

class MeshroomVideoPlugin:
    """
    Plugin for Meshroom to process video files and generate 3D models.
    This plugin extracts frames from a video file and feeds them into Meshroom's photogrammetry pipeline.
    """
    
    def __init__(self, video_path, output_dir, frame_interval=1, quality='high', meshroom_bin=None, 
                 rotate='auto', verbose=False, extract_metadata=False, start_time=None, duration=None,
                 detect_blur=False, blur_threshold=100.0):
        """Initialize plugin with parameters."""
        self.video_path = video_path
        self.output_dir = output_dir
        self.frame_interval = frame_interval
        self.quality = quality
        self.rotate = rotate
        self.verbose = verbose
        self.extract_metadata = extract_metadata
        self.start_time = start_time
        self.duration = duration
        self.detect_blur = detect_blur
        self.blur_threshold = blur_threshold
        
        # Tools availability
        self.ffmpeg_available = self._check_tool_availability("ffmpeg", "-version")
        self.exiftool_available = self._check_tool_availability("exiftool", "-ver")
        
        if self.verbose:
            print(f"Tool availability:")
            print(f"  - FFmpeg: {'Available' if self.ffmpeg_available else 'Not found'}")
            print(f"  - ExifTool: {'Available' if self.exiftool_available else 'Not found'}")
            
        # Find Meshroom binary
        if meshroom_bin:
            self.meshroom_bin = meshroom_bin
        else:
            self.meshroom_bin = self._find_meshroom_binary()
            
        # Create temporary directory for extracted frames
        self.temp_frames_dir = tempfile.mkdtemp(prefix="meshroom_video_")
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Get video information
        self.video_info = self._get_video_info()
        
        if self.verbose:
            self._print_video_info()
            
    def _check_tool_availability(self, tool_name, check_arg):
        """Check if a tool is available in the system."""
        try:
            subprocess.run([tool_name, check_arg], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except (FileNotFoundError, subprocess.SubprocessError):
            return False
            
    def _find_meshroom_binary(self):
        """Find Meshroom binary in common locations"""
        common_locations = [
            "meshroom",  # If in PATH
            r"C:\Program Files\Meshroom\meshroom_batch.exe",  # Windows
            r"C:\Program Files (x86)\Meshroom\meshroom_batch.exe",  # Windows 32-bit
            "/usr/local/bin/meshroom_batch",  # Linux
            "/Applications/Meshroom.app/Contents/MacOS/meshroom_batch"  # macOS
        ]
        
        for location in common_locations:
            try:
                if os.path.isfile(location) and os.access(location, os.X_OK):
                    return location
                subprocess.run([location, "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return location
            except (FileNotFoundError, PermissionError, subprocess.SubprocessError):
                continue
                
        raise FileNotFoundError("Meshroom binary not found. Please install Meshroom or provide the path to the binary.")
    
    def _get_video_info(self):
        """Get information about the video file using FFmpeg or OpenCV."""
        info = {
            "fps": 0, "width": 0, "height": 0, "frame_count": 0,
            "duration": 0, "rotation": 0, "creation_time": None, "has_metadata": False
        }
        
        if self.ffmpeg_available:
            # Use FFmpeg (more reliable)
            cmd = ["ffmpeg", "-i", self.video_path, "-hide_banner"]
            process = subprocess.run(cmd, capture_output=True, text=True)
            ffmpeg_output = process.stderr
            
            # Extract info using regex
            rotation_match = re.search(r'rotate\s*:\s*(\d+)', ffmpeg_output)
            if rotation_match:
                info["rotation"] = int(rotation_match.group(1))
                
            duration_match = re.search(r'Duration:\s+(\d+):(\d+):(\d+\.\d+)', ffmpeg_output)
            if duration_match:
                hours, minutes, seconds = map(float, duration_match.groups())
                info["duration"] = hours * 3600 + minutes * 60 + seconds
                
            fps_match = re.search(r'(\d+(?:\.\d+)?)\s+fps', ffmpeg_output)
            if fps_match:
                info["fps"] = float(fps_match.group(1))
                
            dimension_match = re.search(r'(\d+)x(\d+)', ffmpeg_output)
            if dimension_match:
                info["width"] = int(dimension_match.group(1))
                info["height"] = int(dimension_match.group(2))
                
            # Calculate frame count
            if info["fps"] > 0 and info["duration"] > 0:
                info["frame_count"] = int(info["fps"] * info["duration"])
                
            # Check for creation time and GPS metadata
            if self.exiftool_available:
                try:
                    cmd = ["exiftool", "-j", "-g", self.video_path]
                    process = subprocess.run(cmd, capture_output=True, text=True)
                    metadata = json.loads(process.stdout)
                    
                    if metadata and len(metadata) > 0:
                        for key in metadata[0]:
                            if key.startswith("GPS") or "Location" in key:
                                info["has_metadata"] = True
                                break
                except:
                    pass
        
        # OpenCV fallback
        if info["fps"] == 0:
            cap = cv2.VideoCapture(self.video_path)
            if cap.isOpened():
                info["fps"] = cap.get(cv2.CAP_PROP_FPS)
                info["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                info["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                info["frame_count"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                info["duration"] = info["frame_count"] / info["fps"] if info["fps"] > 0 else 0
                cap.release()
        
        return info
        
    def _print_video_info(self):
        """Print detailed information about the video."""
        print("\nVideo Information:")
        print(f"  - File: {self.video_path}")
        print(f"  - Resolution: {self.video_info['width']}x{self.video_info['height']} pixels")
        print(f"  - Framerate: {self.video_info['fps']:.2f} fps")
        print(f"  - Duration: {self._format_duration(self.video_info['duration'])}")
        print(f"  - Total frames: {self.video_info['frame_count']}")
        
        # Show extraction plan
        frames_to_extract = self.video_info['frame_count'] // self.frame_interval
        print(f"\nExtraction Plan:")
        print(f"  - Frame interval: {self.frame_interval} (extracting 1 frame every {self.frame_interval} frames)")
        print(f"  - Frames to extract: approx. {frames_to_extract}")
        print(f"  - Output directory: {self.output_dir}")
        
        if self.detect_blur:
            print(f"  - Blur detection: Enabled (threshold: {self.blur_threshold})")
    
    def _format_duration(self, seconds):
        """Format duration in seconds to HH:MM:SS format."""
        return str(timedelta(seconds=int(seconds)))
    
    def _calculate_blur_score(self, frame):
        """Calculate blur score using Laplacian variance. Higher = sharper."""
        if frame is None:
            return 0.0
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.Laplacian(gray, cv2.CV_64F).var()
    
    def extract_frames_opencv(self):
        """Extract frames from video using OpenCV with blur detection."""
        if self.verbose:
            print("Extracting frames using OpenCV...")
            
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {self.video_path}")
        
        # Calculate start frame and frames to process
        start_frame = 0
        end_frame = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if self.start_time:
            h, m, s = map(int, self.start_time.split(':'))
            start_seconds = h * 3600 + m * 60 + s
            start_frame = int(start_seconds * self.video_info['fps'])
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
        if self.duration:
            h, m, s = map(int, self.duration.split(':'))
            duration_seconds = h * 3600 + m * 60 + s
            end_frame = min(end_frame, start_frame + int(duration_seconds * self.video_info['fps']))
            
        frames_to_process = end_frame - start_frame
        frames_to_extract = frames_to_process // self.frame_interval
        
        if self.verbose:
            print(f"Processing {frames_to_process} frames, extracting approximately {frames_to_extract} frames")
            
        # Extract frames
        count = 0
        extracted = 0
        skipped_blur = 0
        start_time = time.time()
        last_update_time = start_time
        
        while count < frames_to_process:
            ret, frame = cap.read()
            if not ret:
                break
                
            if count % self.frame_interval == 0:
                # Check for blur if enabled
                if self.detect_blur:
                    blur_score = self._calculate_blur_score(frame)
                    
                    if blur_score < self.blur_threshold:
                        if self.verbose:
                            print(f"\nDetected blurry frame (score: {blur_score:.2f})")
                            
                        # Look ahead for a better frame
                        look_ahead_limit = min(self.frame_interval // 2, 5)
                        best_frame = frame
                        best_score = blur_score
                        found_better = False
                        current_pos = cap.get(cv2.CAP_PROP_POS_FRAMES)
                        
                        for i in range(1, look_ahead_limit + 1):
                            ahead_ret, ahead_frame = cap.read()
                            if not ahead_ret:
                                break
                                
                            ahead_score = self._calculate_blur_score(ahead_frame)
                            
                            if ahead_score > best_score and ahead_score >= self.blur_threshold:
                                best_frame = ahead_frame
                                best_score = ahead_score
                                found_better = True
                                if self.verbose:
                                    print(f"  Found better frame {i} steps ahead (score: {best_score:.2f})")
                                break
                        
                        seek_pos = current_pos + (look_ahead_limit if not found_better else i)
                        cap.set(cv2.CAP_PROP_POS_FRAMES, seek_pos)
                        
                        frame = best_frame
                        if not found_better:
                            skipped_blur += 1
                
                # Apply rotation if needed
                if self.rotate == 'auto' and self.video_info['rotation'] != 0:
                    rotation = self.video_info['rotation']
                elif isinstance(self.rotate, (int, float)) and self.rotate != 0:
                    rotation = int(self.rotate)
                else:
                    rotation = 0
                    
                if rotation != 0:
                    if rotation == 90:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                    elif rotation == 180:
                        frame = cv2.rotate(frame, cv2.ROTATE_180)
                    elif rotation == 270:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                
                # Save the frame
                frame_path = os.path.join(self.temp_frames_dir, f"frame_{extracted:06d}.jpg")
                cv2.imwrite(frame_path, frame)
                extracted += 1
                
                # Show progress in verbose mode
                if self.verbose and (time.time() - last_update_time >= 1.0):
                    elapsed = time.time() - start_time
                    progress = (count + 1) / frames_to_process * 100
                    fps_processing = (count + 1) / elapsed if elapsed > 0 else 0
                    
                    print(f"\rProgress: {progress:.1f}% | Extracted: {extracted}/{frames_to_extract} frames", end="")
                    last_update_time = time.time()
            
            count += 1
            
        cap.release()
        
        if self.verbose:
            print(f"\nExtraction completed. Extracted {extracted} frames.")
            
        return extracted
        
    def extract_frames_ffmpeg(self):
        """Extract frames from video using FFmpeg."""
        if self.verbose:
            print("Extracting frames using FFmpeg...")
            
        if self.detect_blur:
            if self.verbose:
                print("Blur detection requested - switching to OpenCV")
            return self.extract_frames_opencv()
            
        # Build FFmpeg command
        output_pattern = os.path.join(self.temp_frames_dir, "frame_%06d.jpg")
        ffmpeg_cmd = ["ffmpeg", "-i", self.video_path]
        
        if self.start_time:
            ffmpeg_cmd.extend(["-ss", self.start_time])
        if self.duration:
            ffmpeg_cmd.extend(["-t", self.duration])
            
        if self.frame_interval > 1:
            output_fps = self.video_info['fps'] / self.frame_interval
            ffmpeg_cmd.extend(["-r", str(output_fps)])
            
        # Add rotation filter if needed
        vf_filters = []
        
        if self.rotate == 'auto' and self.video_info['rotation'] != 0:
            rotation = self.video_info['rotation']
        elif isinstance(self.rotate, (int, float)) and self.rotate != 0:
            rotation = int(self.rotate)
        else:
            rotation = 0
            
        if rotation != 0:
            if rotation == 90:
                vf_filters.append("transpose=1")
            elif rotation == 180:
                vf_filters.append("transpose=2,transpose=2")
            elif rotation == 270:
                vf_filters.append("transpose=2")
                
        if vf_filters:
            ffmpeg_cmd.extend(["-vf", ",".join(vf_filters)])
            
        # Set quality
        ffmpeg_cmd.extend(["-q:v", "2"])
        ffmpeg_cmd.append(output_pattern)
        
        if self.verbose:
            print(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
            
        # Run FFmpeg
        subprocess.run(ffmpeg_cmd, check=True, 
                      stdout=subprocess.PIPE if not self.verbose else None,
                      stderr=subprocess.PIPE if not self.verbose else None)
            
        # Count extracted frames
        extracted_frames = len([f for f in os.listdir(self.temp_frames_dir) 
                               if f.startswith("frame_") and f.endswith(".jpg")])
        
        if self.verbose:
            print(f"Extracted {extracted_frames} frames using FFmpeg.")
            
        return extracted_frames
        
    def extract_frames(self):
        """Extract frames from the video file using the best available method."""
        if self.ffmpeg_available and not self.detect_blur:
            return self.extract_frames_ffmpeg()
        else:
            return self.extract_frames_opencv()
            
    def extract_metadata(self):
        """Extract metadata from video and apply to frames."""
        if not self.extract_metadata or not self.exiftool_available:
            return False
        
        if self.verbose:
            print("Extracting and applying metadata to frames...")
            
        # Extract metadata from video
        cmd = ["exiftool", "-j", "-g", self.video_path]
        try:
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)
            video_metadata = json.loads(process.stdout)
            
            if not video_metadata or len(video_metadata) == 0:
                if self.verbose:
                    print("No metadata found in video file.")
                return False
                
            metadata = video_metadata[0]
            
            # Apply metadata to frames
            frames = sorted([f for f in os.listdir(self.temp_frames_dir) 
                           if f.startswith("frame_") and (f.endswith(".jpg") or f.endswith(".png"))])
            
            for i, frame_file in enumerate(frames):
                if self.verbose and (i % 10 == 0 or i == len(frames) - 1):
                    print(f"\rApplying metadata to frame {i+1}/{len(frames)} ({(i+1)/len(frames)*100:.1f}%)", end="")
                    
                frame_path = os.path.join(self.temp_frames_dir, frame_file)
                
                # Build ExifTool command to copy metadata
                exiftool_cmd = ["exiftool"]
                
                for key, value in metadata.items():
                    if (key.startswith("GPS") or key == "Location" or 
                        key in ["Make", "Model", "FocalLength", "FNumber", "ExposureTime"]):
                        exiftool_cmd.extend([f"-{key}={value}"])
                        
                exiftool_cmd.append(frame_path)
                
                subprocess.run(exiftool_cmd, check=True, capture_output=True)
                
                # Remove backup files
                backup_file = frame_path + "_original"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                    
            if self.verbose:
                print("\nMetadata application completed.")
                
            return True
                
        except Exception as e:
            if self.verbose:
                print(f"Error in metadata extraction: {str(e)}")
            return False
        
    def run_meshroom(self):
        """Run Meshroom on the extracted frames."""
        if self.verbose:
            print(f"Running Meshroom on extracted frames...")
            
        # Build the command
        cmd = [
            self.meshroom_bin,
            "--input", self.temp_frames_dir,
            "--output", self.output_dir
        ]
        
        if self.quality.lower() == 'low':
            cmd.extend(["--preset", "low"])
        elif self.quality.lower() == 'medium':
            cmd.extend(["--preset", "medium"])
        else:
            cmd.extend(["--preset", "high"])
            
        if self.verbose:
            print(f"Running Meshroom command: {' '.join(cmd)}")
            
        try:
            subprocess.run(cmd, check=True, capture_output=not self.verbose)
            return True
        except Exception as e:
            print(f"Error running Meshroom: {str(e)}")
            return False
            
    def cleanup(self):
        """Clean up temporary files."""
        if self.verbose:
            print(f"Cleaning up temporary files...")
        try:
            shutil.rmtree(self.temp_frames_dir)
            return True
        except Exception as e:
            print(f"Error cleaning up: {str(e)}")
            return False
            
    def process(self):
        """Process the video and generate 3D model."""
        try:
            # Extract frames
            extracted_count = self.extract_frames()
            
            if extracted_count == 0:
                print("Error: No frames were extracted from the video.")
                return False
                
            # Extract metadata if requested
            if self.extract_metadata:
                self.extract_metadata()
                
            # Run Meshroom
            success = self.run_meshroom()
            
            if not success:
                print("Error: Meshroom processing failed.")
                return False
                
            print(f"Success! 3D model generated in: {self.output_dir}")
            return True
            
        finally:
            # Clean up temporary files
            self.cleanup()


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(description="Meshroom Video Plugin - Process videos to create 3D models")
    
    parser.add_argument("video", help="Path to input video file")
    parser.add_argument("--output", "-o", help="Path to output directory (default: based on video filename)")
    
    parser.add_argument("--frame-interval", "-f", type=int, default=15,
                      help="Extract a frame every N frames (default: 15)")
    parser.add_argument("--quality", "-q", choices=["low", "medium", "high"], default="high",
                      help="Quality setting for 3D model (default: high)")
    parser.add_argument("--meshroom-bin", "-m", help="Path to Meshroom binary")
    parser.add_argument("--rotate", "-r", type=str, default="auto",
                      help="Rotation: 'auto', 0, 90, 180, or 270 degrees (default: auto)")
    parser.add_argument("--verbose", "-v", action="store_true",
                      help="Show detailed progress information")
    parser.add_argument("--extract-metadata", "-e", action="store_true",
                      help="Extract and apply metadata to frames")
    parser.add_argument("--start", "-s", help="Start time for extraction (format: HH:MM:SS)")
    parser.add_argument("--duration", "-d", help="Duration of segment to extract (format: HH:MM:SS)")
    parser.add_argument("--detect-blur", "-b", action="store_true",
                      help="Enable blur detection to improve frame quality")
    parser.add_argument("--blur-threshold", "-t", type=float, default=100.0,
                      help="Threshold for blur detection (default: 100.0, higher = more strict)")
    
    args = parser.parse_args()
    
    # Validate video path
    if not os.path.isfile(args.video):
        print(f"Error: Video file not found: {args.video}")
        return 1
        
    # Determine output directory
    if args.output:
        output_dir = args.output
    else:
        base_name = os.path.splitext(os.path.basename(args.video))[0]
        output_dir = os.path.join(os.getcwd(), f"{base_name}_model")
        
    # Process rotation argument
    rotate = args.rotate
    if rotate != "auto":
        try:
            rotate = int(rotate)
            if rotate not in [0, 90, 180, 270]:
                print("Warning: Invalid rotation value. Using 'auto' instead.")
                rotate = "auto"
        except ValueError:
            print("Warning: Invalid rotation value. Using 'auto' instead.")
            rotate = "auto"
    
    try:
        # Create plugin instance
        plugin = MeshroomVideoPlugin(
            video_path=args.video,
            output_dir=output_dir,
            frame_interval=args.frame_interval,
            quality=args.quality,
            meshroom_bin=args.meshroom_bin,
            rotate=rotate,
            verbose=args.verbose,
            extract_metadata=args.extract_metadata,
            start_time=args.start,
            duration=args.duration,
            detect_blur=args.detect_blur,
            blur_threshold=args.blur_threshold
        )
        
        # Process video
        success = plugin.process()
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
        

if __name__ == "__main__":
    sys.exit(main())