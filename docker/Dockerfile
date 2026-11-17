FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d AS builder

ARG TAHOE_VERSION=1.20.0
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev \
    && pip wheel --no-cache-dir --wheel-dir /wheels "tahoe-lafs==${TAHOE_VERSION}"

FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d
ARG TAHOE_VERSION=1.20.0
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels "tahoe-lafs==${TAHOE_VERSION}" \
    && rm -rf /wheels \
    && useradd --uid 10001 --create-home tahoe \
    && mkdir /data && chown tahoe:tahoe /data
COPY docker/entrypoint.py /opt/entrypoint.py
USER 10001:10001
ENV PYTHONUNBUFFERED=1
VOLUME /data
ENTRYPOINT ["python", "/opt/entrypoint.py"]
