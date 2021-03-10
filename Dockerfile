FROM python:3.8.8

# tshark needs to be installed separately otherwise the security prompt breaks the build
RUN apt-get update \
&& DEBIAN_FRONTEND=noninteractive apt-get install -y tshark \
&& apt-get install -y \
  docker \
  tshark

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY munin.py .

CMD [ "python", "-u", "./munin.py", "/config/munin.yaml"]
