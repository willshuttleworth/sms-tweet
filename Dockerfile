FROM python:latest

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./python /code/python
COPY ./templates/ /code/templates/

CMD ["fastapi", "run", "python/main.py", "--port", "80"]
