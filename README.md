# Panopto Video Downloader

A Python script to download videos from Panopto (Unibo).

Forked from [https://codeberg.org/matteomanuelli/reverse-engineering-panopto-unibo](https://codeberg.org/matteomanuelli/reverse-engineering-panopto-unibo).

## Features

- Download individual videos or entire folders
- Support for environment variables for credentials
- Batch processing from URL list files
- **Parallel downloads for multiple URLs (configurable)**
- Progress tracking with detailed status messages

## Usage

### 1. Environment Variables (Optional)

Set up your credentials using environment variables to avoid typing them each time:

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
nano .env

# No need to source - python-dotenv loads it automatically
```

Or export them directly:

```bash
export PANOPTO_EMAIL="your.email@unibo.it"
export PANOPTO_PASSWORD="your_password"
export MAX_PARALLEL_DOWNLOADS="3"  # Optional: number of parallel downloads (default: 3)
```

### 2. Single URL Download

```bash
python3 main.py
```

If environment variables are not set, you'll be prompted for credentials and URL.

### 3. Batch Download from File

Create a text file with URLs (one per line):

```bash
# Edit urls.txt and add your URLs
nano urls.txt

# Run with the URLs file
python3 main.py urls.txt
```

#### URLs File Format

```
# Comments start with #
# Individual video URL:
https://unibo.cloud.panopto.eu/Panopto/Pages/Viewer.aspx?id=video-id

# Folder URL:
https://unibo.cloud.panopto.eu/Panopto/Pages/Sessions/List.aspx#folderID="folder-id"

# Empty lines are ignored
```

## Installation

```bash
pip install -r requirements.txt
```

## Examples

```bash
# Interactive mode (prompts for everything)
python3 main.py

# Batch mode with environment credentials
export PANOPTO_EMAIL="your.email@unibo.it"
export PANOPTO_PASSWORD="your_password"
python3 main.py my_urls.txt

# Using .env file (automatic loading)
python3 main.py urls.txt

# Control parallel downloads
export MAX_PARALLEL_DOWNLOADS="5"  # Download up to 5 videos at once
python3 main.py urls.txt
```

## Configuration

### Environment Variables

- `PANOPTO_EMAIL`: Your Unibo email
- `PANOPTO_PASSWORD`: Your Unibo password
- `MAX_PARALLEL_DOWNLOADS`: Number of parallel downloads (default: 3, recommended: 2-5)
