#!/bin/bash
docker build . -t csm_jupyter
docker run --rm -it -p 8895:8888 -v "$PWD":/notebooks/ csm_jupyter jupyter notebook --no-browser\
     --NotebookApp.token=SecretToken --port 8888 --ip 0.0.0.0 --allow-root
