#!/bin/bash

# Function to output file content with a header
output_file_content() {
	    echo "==== File: $1 ===="
	        echo
		    cat "$1"
		        echo
			    echo "==== End of $1 ===="
			        echo
			}

		# Main server file
		output_file_content "server.py"

		# Utility files that might handle audio
		output_file_content "utils/vad.py"
		output_file_content "utils/snac_utils.py"

		# Model and inference files
		output_file_content "litgpt/model.py"
		output_file_content "inference.py"

		# Any configuration files
		if [ -f "config.py" ]; then
			    output_file_content "config.py"
		fi

		# WebUI files (they might contain relevant WebSocket setup)
		output_file_content "webui/omni_streamlit.py"
		output_file_content "webui/omni_gradio.py"

		# Client file (might show how audio is sent to the server)
		output_file_content "client.py"

		# Requirements file (to see any audio-related dependencies)
		output_file_content "requirements.txt"
