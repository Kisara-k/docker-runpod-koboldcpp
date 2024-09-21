import time
import json
import requests
from requests.adapters import HTTPAdapter, Retry
import runpod

# Configure retry mechanism for the session
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


def run_inference(params):
    config = {
        "baseurl": "http://127.0.0.1:5001",  # Base URL for the API
        "api": {
            "true_max_context_length": ("GET", "/api/extra/true_max_context_length"),
            "version": ("GET", "/api/extra/version"),
            "generate": ("POST", "/api/v1/generate"),
            "generate_stream": ("POST", "/api/extra/generate/stream"),
            "check_generate": ("POST", "/api/extra/generate/check"),
            "token_count": ("POST", "/api/extra/tokencount"),
            "abort_generate": ("POST", "/api/extra/abort"),
            "transcribe": ("POST", "/api/extra/transcribe"),
            "txt2img": ("POST", "/sdapi/v1/txt2img"),
            "img2img": ("POST", "/sdapi/v1/img2img"),
            "interrogate": ("POST", "/sdapi/v1/interrogate"),
        },
        "timeout": 600
    }

    api_name = params["api_name"]

    if api_name in config["api"]:
        api_config = config["api"][api_name]
    else:
        raise Exception(f"Method '{api_name}' not yet implemented")

    api_verb = api_config[0]
    api_path = api_config[1]

    # Generator handler for streaming tokens
    if api_verb == "POST":
        if api_name == "generate_stream":
            # Handle stream response
            response = automatic_session.post(
                url='%s%s' % (config["baseurl"], api_path),
                json=params,
                timeout=config["timeout"],
                stream=True  # Stream the response for real-time token output
            )
            # Iterate over streaming response and yield tokens
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith('data:'):
                    # Parse the JSON token message
                    try:
                        token_data = json.loads(line[6:].strip())  # Skip "data: "
                        token = token_data.get('token', '')
                        if token:
                            yield token  # Yield token to client
                    except json.JSONDecodeError:
                        yield "Failed to decode token data"
            # Indicate that the stream has completed
            yield "\n\nStream completed."
        else:
            # For non-streaming POST requests, return JSON response
            response = automatic_session.post(
                url='%s%s' % (config["baseurl"], api_path),
                json=params,
                timeout=config["timeout"]
            )
            yield json.dumps(response.json())

    elif api_verb == "GET":
        # For GET requests, return JSON response
        response = automatic_session.get(
            url='%s%s' % (config["baseurl"], api_path),
            timeout=config["timeout"]
        )
        yield json.dumps(response.json())

# ---------------------------------------------------------------------------- #
#                                RunPod Handler                                #
# ---------------------------------------------------------------------------- #
def handler(event):
    '''
    This is the handler function that will be called by the serverless.
    '''
    # Yield each token or response progressively
    for output in run_inference(event["input"]):
        yield output


if __name__ == "__main__":
    wait_for_service(url='http://127.0.0.1:5001/api/v1/generate')

    print("KoboldCpp API Service is ready. Starting RunPod...")

    # Start the serverless function with generator streaming
    runpod.serverless.start({
        'handler': handler,
        'return_aggregate_stream': False  # Set this to False to enable streaming response
    })