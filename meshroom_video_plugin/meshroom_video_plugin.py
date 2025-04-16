import os
import sys
import cv2
import argparse
import tempfile
import shutil
import subprocess
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
        self.output_dir = output_dir
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
                
                # Print progress every 100 frames
                if extracted % 100 == 0:
                    print(f"Extracted {extracted} frames...")
                    
            count += 1
            
        # Release video
        video.release()
        
        print(f"Extracted {extracted} frames in total.")
        return extracted
        
    def run_meshroom(self):
        """Run Meshroom on the extracted frames"""
        print(f"Running Meshroom on extracted frames...")
        
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
            cmd.extend(["-p", "photogrammetryDraft"])
        elif self.quality == 'medium':
            cmd.extend(["-p", "photogrammetry"])
        else:  # high
            cmd.extend(["-p", "photogrammetryAndCameraTracking"])
            
        # Run Meshroom
        print(f"Running command: {' '.join(cmd)}")
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Print output in real-time
            for line in process.stdout:
                print(line, end='')
                
            # Wait for process to complete
            process.wait()
            
            if process.returncode != 0:
                stderr = process.stderr.read()
                raise subprocess.SubprocessError(f"Meshroom failed with error: {stderr}")
                
        except Exception as e:
            raise RuntimeError(f"Failed to run Meshroom: {str(e)}")
            
        print(f"Meshroom processing completed successfully.")
        
    def cleanup(self):
        """Clean up temporary files"""
        print(f"Cleaning up temporary files...")
        shutil.rmtree(self.temp_frames_dir)
        
    def process(self):
        """Process the video and generate 3D model"""
        try:
            # Extract frames
            extracted_count = self.extract_frames()
            
            if extracted_count == 0:
                raise ValueError("No frames were extracted from the video.")
                
            # Run Meshroom
            self.run_meshroom()
            
            # Final output paths to check
            possible_outputs = [
                os.path.join(self.output_dir, "texturedMesh.obj"),
                os.path.join(self.output_dir, "meshes", "texturedMesh.obj"),
                os.path.join(self.output_dir, "project.mg")  # At minimum, project file should exist
            ]
            
            # Find the first existing output file
            output_path = None
            for path in possible_outputs:
                if os.path.exists(path):
                    output_path = path
                    break
            
            if output_path:
                print(f"Meshroom project/model generated: {output_path}")
                print(f"Output directory: {self.output_dir}")
                return output_path
            else:
                print("Warning: Expected output files not found at expected locations.")
                print(f"Check output directory: {self.output_dir}")
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