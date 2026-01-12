#!/bin/bash
cd app
celery -A tasks worker --loglevel=info

