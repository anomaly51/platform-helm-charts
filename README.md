# platform-helm-charts

Repository for custom platform Helm charts.

This repository stores reusable charts that are published to the internal OCI
Helm registry and consumed by GitOps repositories. Individual charts keep their
own names and release contracts under `charts/`.

## Charts

- `common-apps`: reusable application chart for small GitOps-managed workloads.

## Release Model

- Chart versions are SemVer and immutable once pushed.
- Chart artifacts can be packaged manually and stored as OCI artifacts in
  `harbor.api-api-api.com/helm-charts`.
- Application repositories pin chart versions in `Chart.yaml`.
- Application image tags are updated in GitOps repositories by CI.

## Tag Contract

- `common-apps-vX.Y.Z` publishes chart `common-apps` version `X.Y.Z`.
- Docker images should use immutable tags for deployed revisions.

## Required Secrets

- `HARBOR_USERNAME`
- `HARBOR_PASSWORD`
- `TELEGRAM_BOT_TOKEN` optional
- `TELEGRAM_CHAT_ID` optional
