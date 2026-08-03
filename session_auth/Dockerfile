FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /var/task

COPY requirements.txt ./requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir awslambdaric -r requirements.txt

COPY rer_session_auth ./rer_session_auth

ENTRYPOINT ["python", "-m", "awslambdaric"]
CMD ["rer_session_auth.handler.handler"]
