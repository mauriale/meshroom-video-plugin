import os
import sys
import cv2
import argparse
import tempfile
import shutil
import subprocess
import re
import time
from pathlib import Path

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
    
    def extract_frames(self):
        """Extract frames from the video file"""
        print(f"Extracting frames from {self.video_path}...")
        
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
                # Save frame as a JPG file
                frame_path = os.path.join(self.temp_frames_dir, f"frame_{extracted:06d}.jpg")
                cv2.imwrite(frame_path, frame)
                extracted += 1
                
                # Print progress every 10 frames or when it's a multiple of 10%
                if extracted % 10 == 0 or (frames_to_extract > 0 and extracted * 100 // frames_to_extract % 10 == 0):
                    percent = (extracted * 100) // frames_to_extract if frames_to_extract > 0 else 0
                    print(f"[{percent}%] Extracted {extracted} frames...")
                    
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