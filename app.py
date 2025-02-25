import os
import boto3
import time
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

# Initialize AWS clients
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION,
)

transcribe_client = boto3.client(
    "transcribe",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION,
)

UPLOAD_FOLDER = "uploads"
SUBTITLE_FOLDER = "subtitles"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SUBTITLE_FOLDER, exist_ok=True)


def extract_audio(video_path, audio_path):
    """Extracts audio from the given video file."""
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path, codec="pcm_s16le")


@app.route("/upload", methods=["POST"])
def upload_video():
    """Handles video upload and starts transcription."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = file.filename
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    audio_path = video_path.replace(".mp4", ".wav")

    file.save(video_path)
    extract_audio(video_path, audio_path)

    s3_client.upload_file(audio_path, S3_BUCKET_NAME, filename)

    job_name = f"transcription-{int(time.time())}"
    job_uri = f"s3://{S3_BUCKET_NAME}/{filename}"

    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": job_uri},
        MediaFormat="wav",
        LanguageCode="en-US",
    )

    return jsonify({"message": "Transcription started", "job_name": job_name})


@app.route("/get_subtitle/<job_name>", methods=["GET"])
def get_subtitle(job_name):
    """Checks the transcription status and generates the .srt file."""
    response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
    status = response["TranscriptionJob"]["TranscriptionJobStatus"]

    if status == "IN_PROGRESS":
        return jsonify({"message": "Transcription in progress"}), 202

    if status == "FAILED":
        return jsonify({"error": "Transcription failed"}), 500

    transcript_url = response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
    transcript_file = f"{SUBTITLE_FOLDER}/{job_name}.json"

    os.system(f"wget -O {transcript_file} {transcript_url}")

    srt_file = f"{SUBTITLE_FOLDER}/{job_name}.srt"
    generate_srt(transcript_file, srt_file)

    return send_file(srt_file, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
