import json
from datetime import timedelta

def generate_srt(json_file, srt_file):
    """Converts AWS Transcribe output to .srt format."""
    with open(json_file, "r") as file:
        data = json.load(file)

    items = data["results"]["items"]
    srt_entries = []
    index = 1

    for i in range(0, len(items), 2):
        if i + 1 >= len(items):
            break

        word1 = items[i]
        word2 = items[i + 1]

        start_time = float(word1["start_time"])
        end_time = float(word2["end_time"])
        text = f"{word1['alternatives'][0]['content']} {word2['alternatives'][0]['content']}"

        start_time = str(timedelta(seconds=start_time)) + ",000"
        end_time = str(timedelta(seconds=end_time)) + ",000"

        srt_entries.append(f"{index}\n{start_time} --> {end_time}\n{text}\n")
        index += 1

    with open(srt_file, "w", encoding="utf-8") as file:
        file.writelines(srt_entries)
