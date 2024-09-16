import pyaudio
import wave
import requests
import base64
import io
import threading
import time
import argparse

# Audio parameters
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 60  # Simulate a 1-minute call

# Server URL
URL = "https://60808-01j7xtj1w8q48sah617zmkznth.cloudspaces.litng.ai/chat"

def send_audio_chunk(audio_data):
    buf = io.BytesIO()
    wf = wave.open(buf, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(audio_data)
    wf.close()

    audio_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    payload = {
        "audio": audio_base64,
        "stream_stride": 4,
        "max_tokens": 1024
    }

    response = requests.post(URL, json=payload, stream=True)

    if response.status_code == 200:
        print("Received response from server")
        # In a real application, you might want to play this audio or process it further
        # For now, we'll just save it to a file
        with open("response.wav", "wb") as f:
            f.write(response.content)
        print("Response saved as response.wav")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def stream_from_mic():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* Recording from microphone")

    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        send_audio_chunk(data)

    print("* Done recording")

    stream.stop_stream()
    stream.close()
    p.terminate()

def stream_from_file(filename):
    print(f"* Streaming from file: {filename}")
    with wave.open(filename, 'rb') as wf:
        while True:
            data = wf.readframes(CHUNK)
            if not data:
                break
            send_audio_chunk(data)
            time.sleep(0.06)  # Simulate real-time streaming

    print("* Done streaming file")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio streaming client")
    parser.add_argument("--input", choices=["mic", "file"], default="mic", help="Input source: mic or file")
    parser.add_argument("--file", help="Path to WAV file (required if input is 'file')")
    args = parser.parse_args()

    if args.input == "mic":
        stream_from_mic()
    elif args.input == "file":
        if not args.file:
            print("Error: --file argument is required when input is 'file'")
        else:
            stream_from_file(args.file)
