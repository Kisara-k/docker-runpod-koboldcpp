import time
import runpod
import requests
from requests.adapters import HTTPAdapter, Retry

# Setup session and retries
automatic_session = requests.Session()
retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[502, 503, 504])
automatic_session.mount('http://', HTTPAdapter(max_retries=retries))

# ---------------------------------------------------------------------------- #
#                              Automatic Functions                             #
# ---------------------------------------------------------------------------- #

def wait_for_service(url):
    '''
    Check if the service is ready to receive requests.
    '''
    while True:
        try:
            requests.get(url)
            return
        except requests.exceptions.RequestException:
            print("Service not ready yet. Retrying...")
        except Exception as err:
            print("Error: ", err)

        time.sleep(0.2)

# Inference logic to handle different API requests
def run_inference(params):
    config = {
        "baseurl": "http://127.0.0.1:5001",  # Updated to use port 5001
        "api": {
            # Retrieve max context length
            "true_max_context_length": ("GET", "/api/extra/true_max_context_length"),
            # Retrieve KoboldCpp backend version
            "version": ("GET", "/api/extra/version"),

            # KoboldAI United compatible core API
            "generate": ("POST", "/api/v1/generate"),
            
            # Kobold Extra API
            "generate_stream": ("POST", "/api/extra/generate/stream"),
            "check_generate": ("POST", "/api/extra/generate/check"),
            "token_count": ("POST", "/api/extra/tokencount"),
            "abort_generate": ("POST", "/api/extra/abort"),
            "transcribe": ("POST", "/api/extra/transcribe"),
            
            # SDAPI Image Gen
            "txt2img": ("POST", "/sdapi/v1/txt2img"),
            "img2img": ("POST", "/sdapi/v1/img2img"),
            "interrogate": ("POST", "/sdapi/v1/interrogate"),
        },
        "timeout": 600
    }

    api_name = params["api_name"]
    if api_name not in config["api"]:
        raise Exception(f"Method '{api_name}' not yet implemented")

    api_verb, api_path = config["api"][api_name]

    # For "generate_stream", enable streaming
    if api_name == "generate_stream":
        response = automatic_session.post(f'{config["baseurl"]}{api_path}', json=params, timeout=config["timeout"], stream=True)
        return response
    else:
        # For all other requests, return JSON
        if api_verb == "GET":
            response = automatic_session.get(f'{config["baseurl"]}{api_path}', timeout=config["timeout"])
        elif api_verb == "POST":
            response = automatic_session.post(f'{config["baseurl"]}{api_path}', json=params, timeout=config["timeout"])

        return response.json()

# ---------------------------------------------------------------------------- #
#                                RunPod Handler                                #
# ---------------------------------------------------------------------------- #

def handler(event):
    '''
    This is the handler function that will be called by the serverless.
    '''
    api_name = event["input"]["api_name"]

    # Call the run_inference function
    response = run_inference(event["input"])

    # Handle streaming response for "generate_stream"
    if api_name == "generate_stream":
        def stream_response():
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    yield line + "\n"
        return stream_response()
    else:
        # Return normal JSON response for other API calls
        return response

if __name__ == "__main__":
    wait_for_service(url='http://127.0.0.1:5001/api/v1/generate')

    print("KoboldCpp API Service is ready. Starting RunPod...")

    runpod.serverless.start({"handler": handler})
