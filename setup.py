from setuptools import setup, find_packages

setup(
    name="meshroom_video_plugin",
    version="0.2.0",
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
    author="Maurice",
    author_email="maurice@example.com",
    description="Plugin para Meshroom que permite procesar videos y extraer frames con metadatos",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Video :: Conversion",
        "Topic :: Scientific/Engineering :: Image Processing",
    ],
)
