FROM python:3.6-alpine 
COPY requirements.txt /
RUN pip install -r /requirements.txt
ENV ETL_METADATA_URL mongodb+srv://zeyuan:melody@nhttv2-mzjhc.mongodb.net/test
COPY src/ /app
WORKDIR /app
ENTRYPOINT ["bin/entrypoint.sh"]