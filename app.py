import os
import time
import json
import boto3
from flask import Flask, request, jsonify, send_file
from moviepy.editor import VideoFileClip
from dotenv import load_dotenv
from srt_formatter import generate_srt

# Load AWS credentials
load_dotenv()
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Initialize Flask
app = Flask(__name__)

# Initialize AWS Clients
s3_client = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name=AWS_REGION)
transcribe_client = boto3.client("transcribe", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name=AWS_REGION)

UPLOAD_FOLDER = "uploads"
SUBTITLE_FOLDER = "subtitles"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SUBTITLE_FOLDER, exist_ok=True)


def extract_audio(video_path, audio_path):
    """Extracts audio from video using MoviePy."""
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path, codec="pcm_s16le")


# @app.route("/upload", methods=["POST"])
# def upload_video():
#     """Uploads video, extracts audio, uploads to S3, and starts transcription."""
#     if "file" not in request.files:
#         return jsonify({"error": "No file provided"}), 400

#     file = request.files["file"]
#     filename = file.filename
#     video_path = os.path.join(UPLOAD_FOLDER, filename)
#     audio_filename = filename.replace(".mp4", ".wav")
#     audio_path = os.path.join(UPLOAD_FOLDER, audio_filename)

#     # Save and extract audio
#     file.save(video_path)
#     extract_audio(video_path, audio_path)

#     # Upload to S3
#     s3_client.upload_file(audio_path, S3_BUCKET_NAME, audio_filename)

#     # Start Transcription Job
#     job_name = f"transcription-{int(time.time())}"
#     job_uri = f"s3://{S3_BUCKET_NAME}/{audio_filename}"

#     transcribe_client.start_transcription_job(
#         TranscriptionJobName=job_name,
#         Media={"MediaFileUri": job_uri},
#         MediaFormat="wav",
#         LanguageCode="en-US"
#     )

#     return jsonify({"message": "Transcription started", "job_name": job_name})

@app.route("/upload", methods=["POST"])
def upload_video():
    """Handles video upload and starts transcription."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = file.filename
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    audio_path = video_path.replace(".mp4", ".wav")

    # Save file locally
    file.save(video_path)
    extract_audio(video_path, audio_path)

    # Upload to S3
    s3_client.upload_file(audio_path, S3_BUCKET_NAME, filename)

    # Start AWS Transcribe Job with output bucket
    job_name = f"transcription-{int(time.time())}"
    job_uri = f"s3://{S3_BUCKET_NAME}/{filename}"
    output_uri = f"s3://{S3_BUCKET_NAME}/transcriptions/"  # Output location

    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": job_uri},
        MediaFormat="wav",
        LanguageCode="en-US",
        OutputBucketName=S3_BUCKET_NAME,  # Save transcript in S3
        OutputKey=f"transcriptions/{job_name}.json"  # Custom output file
    )

    return jsonify({"message": "Transcription started", "job_name": job_name})


# @app.route("/get_subtitle/<job_name>", methods=["GET"])
# def get_subtitle(job_name):
#     """Checks transcription job status, retrieves transcript, and generates SRT."""
#     response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
#     status = response["TranscriptionJob"]["TranscriptionJobStatus"]

#     if status == "IN_PROGRESS":
#         return jsonify({"message": "Transcription is still in progress"}), 202

#     if status == "FAILED":
#         return jsonify({"error": "Transcription job failed"}), 500

#     # Download the transcript file from AWS Transcribe
#     transcript_url = response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
#     transcript_file = os.path.join(SUBTITLE_FOLDER, f"{job_name}.json")

#     os.system(f"wget -O {transcript_file} {transcript_url}")

#     # Generate SRT file
#     srt_file = os.path.join(SUBTITLE_FOLDER, f"{job_name}.srt")
#     generate_srt(transcript_file, srt_file)

#     return send_file(srt_file, as_attachment=True)

@app.route("/get_subtitle/<job_name>", methods=["GET"])
def get_subtitle(job_name):
    """Fetches the transcription result and generates an SRT file."""
    response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
    status = response["TranscriptionJob"]["TranscriptionJobStatus"]

    if status == "IN_PROGRESS":
        return jsonify({"message": "Transcription in progress"}), 202

    if status == "FAILED":
        return jsonify({"error": "Transcription failed"}), 500

    # Get transcript file from S3
    transcript_s3_key = f"transcriptions/{job_name}.json"
    transcript_local_path = f"{SUBTITLE_FOLDER}/{job_name}.json"
    
    # Download transcript file from S3
    s3_client.download_file(S3_BUCKET_NAME, transcript_s3_key, transcript_local_path)

    # Convert JSON to SRT
    srt_file = f"{SUBTITLE_FOLDER}/{job_name}.srt"
    generate_srt(transcript_local_path, srt_file)

    return send_file(srt_file, as_attachment=True)



if __name__ == "__main__":
    app.run(debug=True)
