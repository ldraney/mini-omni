from flask import Flask, request
from flask_socketio import SocketIO, emit
import base64
import tempfile
from inference import OmniInference
import torch

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
        self.temp_audio_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.audio_data = b""

    def process_audio(self):
        self.temp_audio_file.write(self.audio_data)
        self.temp_audio_file.flush()
        audio_generator = self.client.run_AT_batch_stream(self.temp_audio_file.name, stream_stride=4, max_tokens=1024)
        return audio_generator

omni_server = OmniChatServer()

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connection_response', {'data': 'Connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('audio_stream')
def handle_audio_stream(data):
    print(f"Received audio chunk, end of stream: {data.get('end_of_stream', False)}")
    audio_chunk = base64.b64decode(data['audio'])
    omni_server.audio_data += audio_chunk
    
    if data.get('end_of_stream', False):
        audio_response = omni_server.process_audio()
        for chunk in audio_response:
            emit('audio_response', {'audio': base64.b64encode(chunk).decode('utf-8')})
        omni_server.audio_data = b""
        omni_server.temp_audio_file.seek(0)
        omni_server.temp_audio_file.truncate()

@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "healthy", "message": "Server is running"}, 200

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=60808)