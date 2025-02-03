import os
import ffmpeg
import requests
from services.file_management import download_file

# Set the default local storage directory
STORAGE_PATH = "/tmp/"

def process_conversion(media_url, job_id, bitrate='128k', webhook_url=None):
    """Convert media to MP3 format with specified bitrate."""
    input_filename = download_file(media_url, os.path.join(STORAGE_PATH, f"{job_id}_input"))
    file_size = os.path.getsize(input_filename)
    print(f"Downloaded file {input_filename} size: {file_size} bytes")
    if file_size == 0:
        raise ValueError(f"Downloaded file {input_filename} is empty!")
    output_filename = f"{job_id}.mp3"
    output_path = os.path.join(STORAGE_PATH, output_filename)

    try:
        # Convert media file to MP3 with specified bitrate
        (
            ffmpeg
            .input(input_filename)
            .output(output_path, acodec='libmp3lame', audio_bitrate=bitrate)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        os.remove(input_filename)
        print(f"Conversion successful: {output_path} with bitrate {bitrate}")

        # Ensure the output file exists locally before attempting upload
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output file {output_path} does not exist after conversion.")

        return output_path

    except Exception as e:
        print(f"Conversion failed: {str(e)}")
        raise

def process_video_combination(media_urls, job_id, webhook_url=None):
    """Combine multiple videos into one."""
    input_files = []
    output_filename = f"{job_id}.mp4"
    output_path = os.path.join(STORAGE_PATH, output_filename)

    try:
        # Download all media files
        for i, media_item in enumerate(media_urls):
            url = media_item['video_url']
            input_filename = download_file(url, os.path.join(STORAGE_PATH, f"{job_id}_input_{i}"))
            file_size = os.path.getsize(input_filename)
            print(f"Downloaded file {input_filename} size: {file_size} bytes")
            if file_size == 0:
                raise ValueError(f"Downloaded file {input_filename} is empty!")
            input_files.append(input_filename)

        # Re-mux input files to ensure proper MOOV atom placement using movflags=faststart
        fixed_input_files = []
        for file in input_files:
            try:
                probe = ffmpeg.probe(file)
                format_name = probe.get("format", {}).get("format_name", "unknown")
                print(f"Probe for {file}: format_name={format_name}")
            except Exception as probe_error:
                print(f"Failed to probe file {file}: {probe_error}")
            fixed_file = file + "_fixed.mp4"
            try:
                (
                    ffmpeg
                    .input(file)
                    .output(fixed_file, c='copy', movflags='faststart')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                fixed_input_files.append(fixed_file)
                os.remove(file)  # Remove the original file after successful re-muxing
            except Exception as e:
                print(f"Failed to fix file {file}: {e}")
                fixed_input_files.append(file)  # Fallback to original if fix fails

        # Print codec info for each file before concatenation
        print("Codec info for each file:")
        for input_file in fixed_input_files:
            try:
                probe = ffmpeg.probe(input_file)
                codec_info = {}
                for stream in probe.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        codec_info['video'] = stream.get('codec_name')
                    elif stream.get('codec_type') == 'audio':
                        codec_info['audio'] = stream.get('codec_name')
                print(f"File: {input_file}, Codecs: {codec_info}")
            except Exception as codec_err:
                print(f"Failed to probe codec info for {input_file}: {codec_err}")

        # Concatenate videos using filter concat method with re-encoding
        inputs = [ffmpeg.input(f) for f in fixed_input_files]
        if len(inputs) == 1:
            # Single video, re-encode directly
            (
                inputs[0]
                .output(output_path, vcodec='libx264', acodec='aac')
                .run(overwrite_output=True)
            )
        else:
            streams = []
            for inp in inputs:
                streams.append(inp.video)
                streams.append(inp.audio)
            concat_output = ffmpeg.concat(*streams, v=1, a=1).node
            v = concat_output[0]
            a = concat_output[1]
            ffmpeg.output(v, a, output_path, vcodec='libx264', acodec='aac').run(overwrite_output=True)

        # Clean up fixed input files
        for f in fixed_input_files:
            os.remove(f)
            
        print(f"Video combination successful: {output_path}")

        # Check if the output file exists locally before upload
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output file {output_path} does not exist after combination.")

        return output_path
    except Exception as e:
        print(f"Video combination failed: {str(e)}")
        raise 
