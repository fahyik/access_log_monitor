FROM python:3.6-alpine

COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt && rm -rf /requirements


RUN touch /var/log/access.log  # since the program will read this by default
RUN touch /tmp/access.log

COPY . /app

WORKDIR /app

ENTRYPOINT ["python", "main.py"]