FROM osgeo/gdal:ubuntu-full-3.4.0

COPY requirements.txt /tmp/requirements.txt

RUN apt-get update && apt-get install -y python3-pip git
RUN pip3 install --upgrade pip
RUN pip3 install -r /tmp/requirements.txt

RUN echo 'alias python=python3' >> ~/.bashrc
RUN echo 'alias pip=pip3' >> ~/.bashrc
