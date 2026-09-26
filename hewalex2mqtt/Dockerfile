FROM python:3.12-alpine
RUN apk add --no-cache git
RUN git clone --depth 1 https://github.com/Chibald/Hewalex2Mqtt.git /app
WORKDIR /app
RUN sed -i "s/if reg\['options'\] and/if reg.get('options') and/" hewalex_geco/devices/base.py
RUN pip install --no-cache-dir -r requirements.txt
COPY start.py /start.py
CMD ["python", "-u", "/start.py"]
