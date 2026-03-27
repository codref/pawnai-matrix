FROM python:3.12-bullseye
RUN mkdir -p /app
COPY . /app
WORKDIR /app
RUN pip install .
WORKDIR /app/bin
CMD ["bob"] 
