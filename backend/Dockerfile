FROM python:3.12-slim

ARG TRIVY_VERSION=0.61.0
ARG CONFTEST_VERSION=0.56.0
ARG KUBECTL_VERSION=1.32.2
ARG TERRAFORM_VERSION=1.9.8
ARG ARGOCD_VERSION=2.13.3
ARG DOCKER_VERSION=27.3.1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git unzip \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sfL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
        | tar -xz -C /usr/local/bin trivy \
    && curl -sfL "https://github.com/open-policy-agent/conftest/releases/download/v${CONFTEST_VERSION}/conftest_${CONFTEST_VERSION}_Linux_x86_64.tar.gz" \
        | tar -xz -C /usr/local/bin conftest \
    && curl -sfL "https://dl.k8s.io/release/v${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
        -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl \
    && curl -sfL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
        -o /tmp/terraform.zip \
    && unzip /tmp/terraform.zip -d /usr/local/bin \
    && rm /tmp/terraform.zip \
    && curl -sfL "https://github.com/argoproj/argo-cd/releases/download/v${ARGOCD_VERSION}/argocd-linux-amd64" \
        -o /usr/local/bin/argocd \
    && chmod +x /usr/local/bin/argocd \
    && curl -sfL "https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz" \
        | tar xz -C /usr/local/bin --strip-components=1 docker/docker

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip==24.3.1 \
    && pip install --no-cache-dir -r requirements.txt

COPY app /app/app

RUN trivy --version \
    && checkov --version \
    && conftest --version \
    && git --version

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
