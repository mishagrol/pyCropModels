FROM zalfrpm/monica-cluster:3.4.0.212
USER root

COPY requirements.txt . 
# && apt-get install -y python3\
RUN apt-get update -y\
    && apt-get install -y python3\
    && apt-get -y install python3-pip -y \
    && pip3 install --no-cache-dir --upgrade pip \
    && pip3 install -r requirements.txt\
    && apt-get install git -y\
    && apt-get clean\
    && git clone https://github.com/zalf-rpm/monica-parameters.git\
    && mv monica-parameters /run/monica 

ENV PATH="$PATH:/run/monica"
ENV MONICA_PARAMETERS="/run/monica/monica-parameters"

EXPOSE 8888