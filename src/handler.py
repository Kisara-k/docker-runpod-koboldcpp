import time
import json

import runpod
import requests
from requests.adapters import HTTPAdapter, Retry

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
    path = None

    if api_name in config["api"]:
        api_config = config["api"][api_name]
    else:
        raise Exception(f"Method '{api_name}' not yet implemented")

    api_verb = api_config[0]
    api_path = api_config[1]

    if api_verb == "GET":
        # For GET requests, we do not need to pass a body
        response = automatic_session.get(
            url='%s%s' % (config["baseurl"], api_path),
            timeout=config["timeout"]
        )
        return response.json()

    elif api_verb == "POST":
        if api_name == "generate_stream":
            # Handle stream response
            response = automatic_session.post(
                url='%s%s' % (config["baseurl"], api_path),
                json=params,
                timeout=config["timeout"],
                stream=True
            )
            # Collect streaming data
            result = ''
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    result += line + '\n'
            return {"result": result}

        else:
            response = automatic_session.post(
                url='%s%s' % (config["baseurl"], api_path),
                json=params, 
                timeout=config["timeout"]
            )
            return response.json()


# ---------------------------------------------------------------------------- #
#                                RunPod Handler                                #
# ---------------------------------------------------------------------------- #
def handler(event):
    '''
    This is the handler function that will be called by the serverless.
    '''

    json_output = run_inference(event["input"])

    # return the output that you want to be returned like pre-signed URLs to output artifacts
    return json_output


if __name__ == "__main__":
    wait_for_service(url='http://127.0.0.1:5001/api/v1/generate')

    print("KoboldCpp API Service is ready. Starting RunPod...")

    runpod.serverless.start({"handler": handler})
