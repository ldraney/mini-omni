import eventlet
eventlet.monkey_patch()

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

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

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
        self.buffer_size = 16000 * 2  # 2 seconds of audio at 16kHz
        self.sample_rate = 16000
        self.sample_width = 2  # Assuming 16-bit audio
        self.model_initialized = False

    def initialize_model(self):
        if not self.model_initialized:
            self.client.model.set_kv_cache(batch_size=2)
            self.model_initialized = True

    def process_audio_chunk(self, audio_chunk):
        self.audio_buffer += audio_chunk
        if len(self.audio_buffer) >= self.buffer_size:
            try:
                self.initialize_model()
                
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
            except Exception as e:
                print(f"Error processing audio chunk: {str(e)}")
                return None
        return None

def process_audio_chunk(self, audio_chunk):
    try:
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
    except Exception as e:
        print(f"Error in process_audio_chunk: {str(e)}")
        return None
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
            try:
                for audio_chunk in response_generator:
                    emit('audio_response', {'audio': base64.b64encode(audio_chunk).decode('utf-8')})
            except Exception as e:
                print(f"Error generating audio response: {str(e)}")
                emit('error', {'message': 'An error occurred while generating the audio response'})
        
        if data.get('end_stream', False):
            # Process any remaining audio in the buffer
            response_generator = omni_server.process_audio_chunk(b'')
            if response_generator:
                try:
                    for audio_chunk in response_generator:
                        emit('audio_response', {'audio': base64.b64encode(audio_chunk).decode('utf-8')})
                except Exception as e:
                    print(f"Error generating final audio response: {str(e)}")
                    emit('error', {'message': 'An error occurred while generating the final audio response'})
            omni_server.audio_buffer = b""  # Reset the buffer after processing
    except Exception as e:
        print(f"Error processing audio stream: {str(e)}")
        emit('error', {'message': 'An error occurred while processing the audio stream'})

@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "healthy", "message": "Server is running"}, 200

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=60808)