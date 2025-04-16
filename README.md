# Meshroom Video Plugin

A plugin that allows Meshroom to process video files and generate 3D models through photogrammetry.

## How It Works

This plugin works by extracting frames from a video file at specified intervals and then feeding those frames into Meshroom's photogrammetry pipeline. Meshroom typically requires individual images as input, and this plugin bridges the gap between video files and Meshroom's image-based workflow.

### Process Flow

1. **Frame Extraction**: The plugin uses OpenCV to read the video file and extract frames at regular intervals.
2. **Metadata Preservation**: GPS and other metadata from the video file are extracted and transferred to each image.
3. **Temporary Storage**: Extracted frames are saved to a temporary directory.
4. **Meshroom Processing**: The plugin calls Meshroom's command-line interface to process the extracted frames.
5. **3D Model Generation**: Meshroom processes the frames through its photogrammetry pipeline to generate a 3D model.
6. **Cleanup**: Temporary files are removed after processing.

## Installation

### Prerequisites

- Python 3.6 or higher
- OpenCV (`pip install opencv-python`)
- Meshroom (must be installed separately)
- For GPS/metadata extraction (optional but recommended):
  - pyexiv2 (`pip install pyexiv2`)
  - ffmpeg-python (`pip install ffmpeg-python`)
  - exiftool (download from [exiftool.org](https://exiftool.org/))

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

## GPS and Metadata Support

For drone videos and other footage with geolocation data, the plugin will:

1. Extract GPS coordinates, altitude, and other metadata from the video
2. Apply this data to each extracted frame
3. Allow Meshroom to use these coordinates for more accurate 3D reconstruction

This feature requires:
- `pyexiv2` library
- `ffmpeg-python` library
- `exiftool` (optional, but provides more accurate metadata extraction)

## Troubleshooting

### Common Issues

- **Meshroom Not Found**: 
  ```
  Error: Meshroom binary not found
  ```
  Solution: Install Meshroom or specify the path with `--meshroom-bin`

- **Metadata Libraries Missing**:
  ```
  Warning: pyexiv2 library not found. Metadata extraction will be limited.
  ```
  Solution: Install required dependencies with `pip install pyexiv2 ffmpeg-python`

- **Long Processing Time**:
  Solution: Use 'low' or 'medium' quality settings, or extract fewer frames with higher `--frame-interval`

## License

MIT License