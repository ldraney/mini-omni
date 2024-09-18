import socketio
import base64
import time

sio = socketio.Client()

@sio.event
def connect():
    print('Connection established')

@sio.event
def disconnect():
    print('Disconnected from server')

@sio.on('connection_response')
def on_connection_response(data):
    print(f"Server response: {data}")

import pyaudio

class AudioPlayer:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=24000,
                                  output=True)

    def play(self, audio_data):
        self.stream.write(audio_data)

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

audio_player = AudioPlayer()

@sio.on('audio_response')
def on_audio_response(data):
    audio_chunk = base64.b64decode(data['audio'])
    audio_player.play(audio_chunk)
    print(f"Played audio chunk of length: {len(audio_chunk)}")

def stream_audio(file_path, chunk_size=1024):
    with open(file_path, 'rb') as audio_file:
        while True:
            chunk = audio_file.read(chunk_size)
            if not chunk:
                sio.emit('audio_stream', {'audio': '', 'end_stream': True})
                break
            encoded_chunk = base64.b64encode(chunk).decode('utf-8')
            sio.emit('audio_stream', {'audio': encoded_chunk, 'end_stream': False})
            time.sleep(0.1)  # Simulate real-time streaming

if __name__ == '__main__':
    server_url = 'https://60808-01j7xtj1w8q48sah617zmkznth.cloudspaces.litng.ai'
    try:
        sio.connect(server_url, wait_timeout=10, transports=['websocket'])
        
        audio_file_path = 'gettysburg.wav'
        stream_audio(audio_file_path)
        
        sio.wait()
    except Exception as e:
        print(f"Connection failed: {e}")
    finally:
        audio_player.close()
