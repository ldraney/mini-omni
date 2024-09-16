import flask
import base64
import tempfile
import traceback
from flask import Flask, Response, stream_with_context, jsonify
from inference import OmniInference
import torch
import io
import soundfile as sf

class OmniChatServer:
    def __init__(self, ip='0.0.0.0', port=60808, run_app=True,
                 ckpt_dir='./checkpoint', device='cpu') -> None:
        server = Flask(__name__)
        
        if torch.cuda.is_available() and torch.cuda.get_device_properties(0).total_memory > 6 * 1024 * 1024 * 1024:  # 6 GB
            device = 'cuda:0'
        else:
            device = 'cpu'
        print(f"Using device: {device}")
        
        self.client = OmniInference(ckpt_dir, device)
        self.client.warm_up()

        server.route("/chat", methods=["POST"])(self.chat)
        server.route("/health", methods=["GET"])(self.health_check)

        if run_app:
            server.run(host=ip, port=port, threaded=False)
        else:
            self.server = server

    def chat(self) -> Response:
        req_data = flask.request.get_json()
        try:
            data_buf = req_data["audio"].encode("utf-8")
            data_buf = base64.b64decode(data_buf)
            stream_stride = req_data.get("stream_stride", 4)
            max_tokens = req_data.get("max_tokens", 1024)

            # Convert the audio data to a format that can be processed by the model
            with io.BytesIO(data_buf) as buf:
                audio_data, sample_rate = sf.read(buf)

            # Process the audio data with the model
            audio_generator = self.client.run_AT_batch_stream(audio_data, stream_stride, max_tokens)
            return Response(stream_with_context(audio_generator), mimetype="audio/wav")
        except Exception as e:
            print(f"Error in chat endpoint: {str(e)}")
            print(f"Request data: {req_data}")
            print(traceback.format_exc())
            return Response(f"An error occurred: {str(e)}\n{traceback.format_exc()}", status=500)

    def health_check(self):
        return jsonify({"status": "healthy", "message": "Server is running"}), 200

def serve(ip='0.0.0.0', port=60808):
    OmniChatServer(ip, port=port, run_app=True)

if __name__ == "__main__":
    import fire
    fire.Fire(serve)
