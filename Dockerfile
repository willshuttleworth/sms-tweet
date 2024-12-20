FROM python:latest

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./python /code/python

# CMD ["fastapi", "run", "python/main.py", "--port", "80"]
CMD /bin/sh