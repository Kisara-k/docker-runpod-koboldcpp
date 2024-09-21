# ---------------------------------------------------------------------------- #
#                         Stage 1: Prepare the image                           #
# ---------------------------------------------------------------------------- #
FROM python:3.10.9-slim

ENV DEBIAN_FRONTEND=noninteractive

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install necessary tools: wget, etc.
RUN apt-get update && \
    apt install -y wget && \
    apt-get autoremove -y && rm -rf /var/lib/apt/lists/* && apt-get clean -y

# Create a working directory
WORKDIR /koboldcpp

# ---------------------------------------------------------------------------- #
#                            Download KoboldCpp                                #
# ---------------------------------------------------------------------------- #
# Set up environment and download KoboldCpp binary
RUN echo "Downloading KoboldCpp, please wait..." && \
    wget -O dlfile.tmp https://kcpplinux.concedo.workers.dev && \
    mv dlfile.tmp koboldcpp_linux && \
    chmod +x ./koboldcpp_linux && \
    test -f ./koboldcpp_linux && echo "Download Successful" || echo "Download Failed"

# ---------------------------------------------------------------------------- #
#                           Set up model path                                  #
# ---------------------------------------------------------------------------- #
# Assuming that model.gguf and imodel.gguf are stored in /runpod-volume/ directory
RUN ln -s /runpod-volume/model.gguf /koboldcpp/model.gguf && \
    ln -s /runpod-volume/imodel.gguf /koboldcpp/imodel.gguf

# ---------------------------------------------------------------------------- #
#                        Install Python Dependencies                           #
# ---------------------------------------------------------------------------- #
# Copy handler script and install dependencies
COPY src/handler.py /koboldcpp/src/handler.py
COPY requirements.txt /koboldcpp/requirements.txt

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r /koboldcpp/requirements.txt

# ---------------------------------------------------------------------------- #
#                        Run KoboldCpp and handler.py                          #
# ---------------------------------------------------------------------------- #
# Run both koboldcpp and handler.py in parallel
CMD ./koboldcpp_linux model.gguf --multiuser --usecublas 0 mmq --contextsize 4096 --gpulayers 999 --quiet --sdmodel imodel.gguf --sdthreads 4 --sdquant --sdclamped & \
    python3 /koboldcpp/src/handler.py
