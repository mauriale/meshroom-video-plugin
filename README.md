# Meshroom Video Plugin

A plugin that allows Meshroom to process video files and generate 3D models through photogrammetry.

## How It Works

This plugin works by extracting frames from a video file at specified intervals and then feeding those frames into Meshroom's photogrammetry pipeline. Meshroom typically requires individual images as input, and this plugin bridges the gap between video files and Meshroom's image-based workflow.

### Process Flow

1. **Frame Extraction**: The plugin uses OpenCV to read the video file and extract frames at regular intervals.
2. **Temporary Storage**: Extracted frames are saved to a temporary directory.
3. **Meshroom Processing**: The plugin calls Meshroom's command-line interface to process the extracted frames.
4. **3D Model Generation**: Meshroom processes the frames through its photogrammetry pipeline to generate a 3D model.
5. **Cleanup**: Temporary files are removed after processing.

## Installation

### Prerequisites

- Python 3.6 or higher
- OpenCV (`pip install opencv-python`)
- Meshroom (must be installed separately)

### Step 1: Clone the Repository

```bash
git clone https://github.com/mauriale/meshroom-video-plugin.git
cd meshroom-video-plugin
```

### Step 2: Install the Plugin

Using pip (recommended):

```bash
pip install .
```

Or for development:

```bash
pip install -e .
```

## Usage

### Command Line Interface

After installation, you can use the plugin directly from the command line:

```bash
meshroom-video your_video.mp4 output_directory
```

Or if you haven't installed it:

```bash
python -m meshroom_video_plugin.meshroom_video_plugin your_video.mp4 output_directory
```

### Command Line Options

```
meshroom-video VIDEO_PATH OUTPUT_DIR [--frame-interval N] [--quality QUALITY] [--meshroom-bin PATH]
```

- `VIDEO_PATH`: Path to the input video file
- `OUTPUT_DIR`: Directory where the 3D model will be saved
- `--frame-interval`: Extract a frame every N frames (default: 15)
- `--quality`: Quality setting ('low', 'medium', 'high', default: 'high')
- `--meshroom-bin`: Path to Meshroom binary (optional if in PATH)

### Example

```bash
meshroom-video my_drone_footage.mp4 3d_model_output --frame-interval 30 --quality medium
```

### Using as a Python Module

You can also use the plugin programmatically in your Python code:

```python
from meshroom_video_plugin import MeshroomVideoPlugin

plugin = MeshroomVideoPlugin(
    video_path="my_video.mp4",
    output_dir="output_model",
    frame_interval=30,
    quality="high"
)

output_path = plugin.process()
print(f"Model generated at: {output_path}")
```

## Installation in Meshroom (Integration)

This is not a direct plugin that integrates with Meshroom's UI. Instead, it's a standalone Python tool that works alongside Meshroom. You don't need to "install" it into Meshroom itself.

However, to make it work seamlessly with Meshroom:

1. Ensure Meshroom is installed and its binary is in your system PATH, or specify its location using the `--meshroom-bin` parameter.

2. The plugin will automatically locate Meshroom if it's installed in a standard location. If not, you'll need to specify the path to the Meshroom binary.

## Tips for Better Results

### Video Capture Tips

1. **Camera Movement**: Move the camera slowly and steadily around the subject.
2. **Coverage**: Ensure you capture the subject from multiple angles (aim for 360° coverage).
3. **Overlap**: Make sure there's sufficient overlap between different views (at least 60%).
4. **Lighting**: Use consistent, diffuse lighting to avoid harsh shadows.
5. **Avoid Moving Objects**: Ensure the scene is static (no moving objects or people).

### Processing Tips

1. **Frame Interval**: For detailed models, use smaller intervals (more frames).
   - Fast-moving footage: 5-10 frames
   - Slow, steady footage: 15-30 frames

2. **Quality Settings**:
   - `low`: Faster processing, less detailed model
   - `medium`: Balanced processing time and detail
   - `high`: Slow processing, most detailed model

3. **Hardware Considerations**:
   - Photogrammetry is resource-intensive
   - 16GB+ RAM recommended for medium to high quality
   - GPU acceleration significantly improves processing time

## Troubleshooting

### Common Issues

- **Meshroom Not Found**: 
  ```
  Error: Meshroom binary not found
  ```
  Solution: Install Meshroom or specify the path with `--meshroom-bin`

- **Poor Quality Model**:
  Solution: Try decreasing the frame interval to extract more frames

- **Out of Memory Errors**:
  Solution: Use 'low' or 'medium' quality settings, or process fewer frames

- **Failed Reconstruction**:
  Solution: Ensure your video has good lighting, minimal motion blur, and captures the subject from multiple angles

- **Installation Errors**:
  If you encounter `setup.py install is deprecated` warnings or other installation errors, try using `pip install .` instead.

## Example Workflow

1. **Capture video**: Record a video moving around an object
2. **Process with plugin**: 
   ```
   meshroom-video my_object_video.mp4 my_3d_model --frame-interval 15
   ```
3. **View or edit the model**: The resulting 3D model will be in the output directory

## License

MIT License