from setuptools import setup, find_packages

setup(
    name="meshroom_video_plugin",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "opencv-python>=4.5.0",
        "numpy>=1.19.0",
    ],
    entry_points={
        'console_scripts': [
            'meshroom-video=meshroom_video_plugin:main',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A plugin for Meshroom to process video files and generate 3D models",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
)