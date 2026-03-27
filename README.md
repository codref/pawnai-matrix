# Matrix BOB

A Matrix https://matrix.org/ **bot** to experiment with autoregressive LLMs.  
The project aims at providing a usable instrument capable of carrying out any sort of activity which can help the other people in the Matrix room Bob joined. Among the various features we can highlight:

* remember things storing indexed documents on Qdrant vector database
* search for stuff over uploaded documents
* scrape the web and summarize the content
* schedule recurring tasks based on LLM queries
* transcribe audio messages and use them for both augmenting Bob knowledge or interact with him.

## Install

```bash 
python -m venv .venv
. ./.venv/bin/activate
pip install .
```

## Development

```bash
pip install --editable .
```

## Run 

Bob requires a Qdrant server instance; the `docker` directory contains an example `docker-compose.yml` file which can be just launched.  
A Dockerized version of Bob is not yet available.  

The `config.yaml` file must be configured as well!

```
./bin/bob
```

## Run database migration

```
alembic upgrade head
```

## Open source and how to contribute

The project is at its early stage, therefore I'd not suggest to push any valuable information yet, but anybody can contribute, just follow the contributing guidelines!  

### Thanks to

* matrix-nio library https://github.com/matrix-nio/matrix-nio
* nio-template project https://github.com/anoadragon453/nio-template


