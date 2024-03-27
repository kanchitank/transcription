from flask import Flask, render_template, request, flash, redirect, send_file
import whisper
import torch
import ffmpeg
import os
import shutil
import zipfile
from datetime import timedelta

app = Flask(__name__)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(device)

@app.route('/')
def upload_file():
    return render_template('upload.html')

@app.route('/transcribe', methods=['POST'])
def transcribe_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            transcription_data = []
            video_path = 'uploads/' + file.filename
            file.save(video_path)
            model = whisper.load_model("base", device=device)
            result = model.transcribe(video_path, verbose=True)

            snapshots_dir = 'static/snapshots'
            if not os.path.exists(snapshots_dir):
                os.makedirs(snapshots_dir)
            else:
                shutil.rmtree(snapshots_dir)
                os.makedirs(snapshots_dir)

            transcription_file_path = 'transcription.txt'
            # Open the transcription file for writing
            with open(transcription_file_path, 'w', encoding='utf-8') as f:
                for segment in result["segments"]:
                    start_seconds = segment["start"]
                    end_seconds = segment["end"]
                    transcription_segment = segment["text"]

                    # Format the timestamps
                    start_time = str(timedelta(seconds=start_seconds))
                    end_time = str(timedelta(seconds=end_seconds))

                    # Ensure the format has milliseconds .sss
                    start_time = f"{start_time.split('.')[0]}.{int(start_seconds % 1 * 1000):03d}"
                    end_time = f"{end_time.split('.')[0]}.{int(end_seconds % 1 * 1000):03d}"

                    # Write the formatted timestamp and transcription to the file
                    f.write(f"[{start_time} --> {end_time}] {transcription_segment}\n")

                    timestamp = f"{start_seconds}-{end_seconds}"
                    frame_filename = f"{snapshots_dir}/{timestamp}.jpg"
                    ffmpeg.input(video_path, ss=start_seconds).output(frame_filename, vframes=1).run(capture_stdout=True, capture_stderr=True)

                    snapshot_filename = os.path.join('snapshots', f"{timestamp}.jpg").replace('\\', '/')

                    transcription_data.append({
                        'start': start_time,
                        'end': end_time,
                        'transcription': transcription_segment,
                        'snapshot_filename': snapshot_filename
                    })

            snapshots_zip_path = 'snapshots.zip'
            with zipfile.ZipFile(snapshots_zip_path, 'w') as zipf:
                for root, dirs, files in os.walk(snapshots_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), arcname=file)

            return render_template('result.html', transcription_data=transcription_data)


@app.route('/download_transcription')
def download_transcription():
    transcription_file_path = 'transcription.txt'
    return send_file(transcription_file_path, as_attachment=True)


@app.route('/download_snapshots')
def download_snapshots():
    snapshots_zip_path = 'snapshots.zip'
    return send_file(snapshots_zip_path, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)