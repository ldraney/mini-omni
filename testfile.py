import requests
import base64

# Replace with your actual server URL
url = "https://60808-01j7xtj1w8q48sah617zmkznth.cloudspaces.litng.ai/chat"

# Replace with the path to your audio file
audio_file_path = "gettysburg.wav"

with open(audio_file_path, "rb") as audio_file:
    audio_content = audio_file.read()
    audio_base64 = base64.b64encode(audio_content).decode('utf-8')

payload = {
    "audio": audio_base64,
    "stream_stride": 4,
    "max_tokens": 1024
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    # Save the response audio
    with open("response.wav", "wb") as f:
        f.write(response.content)
    print("Response saved as response.wav")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
