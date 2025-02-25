import json
from datetime import timedelta

def format_timestamp(seconds):
    """Converts seconds to SRT time format (HH:MM:SS,ms)"""
    millisec = int((seconds % 1) * 1000)
    time_str = str(timedelta(seconds=int(seconds))) + f",{millisec:03d}"
    return time_str

def generate_srt(json_file, srt_file):
    """Converts AWS Transcribe JSON output to SRT format with proper sentence grouping"""
    with open(json_file, "r") as file:
        data = json.load(file)

    items = data["results"]["items"]
    srt_entries = []
    index = 0
    sentence = []
    start_time, end_time = None, None

    for item in items:
        if item["type"] == "pronunciation":
            word = item["alternatives"][0]["content"]
            word_start = float(item["start_time"])
            word_end = float(item["end_time"])

            # Set start time for the first word in a sentence
            if start_time is None:
                start_time = word_start

            end_time = word_end
            sentence.append(word)

        elif item["type"] == "punctuation":
            # Add punctuation to the sentence
            sentence.append(item["alternatives"][0]["content"])

            # Create an SRT entry
            if sentence:
                srt_entries.append(f"{index}\n{format_timestamp(start_time)} --> {format_timestamp(end_time)}\n{' '.join(sentence)}\n\n")
                index += 1
                sentence = []
                start_time, end_time = None, None  # Reset for next sentence

    # Handle any remaining words as a final subtitle block
    if sentence:
        srt_entries.append(f"{index}\n{format_timestamp(start_time)} --> {format_timestamp(end_time)}\n{' '.join(sentence)}\n")

    # Write to SRT file
    with open(srt_file, "w", encoding="utf-8") as file:
        file.writelines(srt_entries)
