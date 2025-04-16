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
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed metadata information")
    
    args = parser.parse_args()
    
    try:
        plugin = MeshroomVideoPlugin(
            args.video,
            args.output,
            frame_interval=args.frame_interval,
            quality=args.quality,
            meshroom_bin=args.meshroom_bin,
            verbose=args.verbose
        )
        
        plugin.process()
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
        
    sys.exit(0)
    

if __name__ == "__main__":
    main()