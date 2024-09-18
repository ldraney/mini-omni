import traceback
from flask import Flask, request
from flask_socketio import SocketIO, emit
import base64
import tempfile
from inference import OmniInference
import torch
import logging
import io
import soundfile as sf
import numpy as np
import wave

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

class OmniChatServer:
    def __init__(self, ckpt_dir='./checkpoint', device='cpu'):
        if torch.cuda.is_available() and torch.cuda.get_device_properties(0).total_memory > 6 * 1024 * 1024 * 1024:
            device = 'cuda:0'
        else:
            device = 'cpu'
        print(f"Using device: {device}")
        
        self.client = OmniInference(ckpt_dir, device)
        self.client.warm_up()
        self.audio_buffer = b""
        self.min_buffer_size = 16000  # Minimum buffer size (1 second)
        self.audio_buffer = b""
        self.buffer_size = 16000 * 2  # 2 seconds of audio at 16kHz
        self.sample_rate = 16000
        self.sample_width = 2  # Assuming 16-bit audio

    def adjust_buffer_size(self, processing_time):
        self.processing_times.append(processing_time)
        if len(self.processing_times) > 10:
            self.processing_times.pop(0)
        
        avg_processing_time = sum(self.processing_times) / len(self.processing_times)
        
        if avg_processing_time > 1.0:  # If processing is slow, increase buffer size
            self.buffer_size = min(self.buffer_size * 1.2, self.max_buffer_size)
        elif avg_processing_time < 0.5:  # If processing is fast, decrease buffer size
            self.buffer_size = max(self.buffer_size * 0.8, self.min_buffer_size)
        
        logger.info(f"Adjusted buffer size to {self.buffer_size}")

    def process_audio_chunk(self, audio_chunk):
        self.audio_buffer += audio_chunk
        if len(self.audio_buffer) >= self.buffer_size:
            # Convert the audio buffer to a numpy array
            audio_data = np.frombuffer(self.audio_buffer[:self.buffer_size], dtype=np.int16)
            
            # Create a temporary WAV file in memory
            with io.BytesIO() as wav_buffer:
                with wave.open(wav_buffer, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono audio
                    wav_file.setsampwidth(self.sample_width)
                    wav_file.setframerate(self.sample_rate)
                    wav_file.writeframes(audio_data.tobytes())
                
                wav_buffer.seek(0)
                
                # Create a temporary file on disk
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                    temp_wav.write(wav_buffer.getvalue())
                    temp_wav_path = temp_wav.name
                
                # Use the run_AT_batch_stream method directly
                response_generator = self.client.run_AT_batch_stream(temp_wav_path)
            
            # Clear the processed audio from the buffer
            self.audio_buffer = self.audio_buffer[self.buffer_size:]
            
            return response_generator
        return None

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connection_response', {'data': 'Connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

omni_server = OmniChatServer()  # Make sure this is defined at the module level

@socketio.on('audio_stream')
def handle_audio_stream(data):
    try:
        print(f"Received audio chunk, end of stream: {data.get('end_stream', False)}")
        audio_chunk = base64.b64decode(data['audio'])
        response_generator = omni_server.process_audio_chunk(audio_chunk)
        if response_generator:
            for audio_chunk in response_generator:
                emit('audio_response', {'audio': base64.b64encode(audio_chunk).decode('utf-8')})
        
        if data.get('end_stream', False):
            # Process any remaining audio in the buffer
            response_generator = omni_server.process_audio_chunk(b'')
            if response_generator:
                for audio_chunk in response_generator:
                    emit('audio_response', {'audio': base64.b64encode(audio_chunk).decode('utf-8')})
            omni_server.audio_buffer = b""  # Reset the buffer after processing
    except Exception as e:
        print(f"Error processing audio stream: {str(e)}")
        emit('error', {'message': 'An error occurred while processing the audio stream'})

@app.route('/health', methods=['GET'])

def health_check():
    return {"status": "healthy", "message": "Server is running"}, 200

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=60808)