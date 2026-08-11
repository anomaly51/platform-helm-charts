# platform-helm-charts

Repository for custom platform Helm charts.

This repository stores reusable charts that are published to the internal OCI
Helm registry and consumed by GitOps repositories. Individual charts keep their
own names and release contracts under `charts/`.

## Charts

- `app`: reusable application chart for small GitOps-managed workloads.
- `cloudflared`: Cloudflare Tunnel deployment and ArgoCD ingress wiring.
- `vault-store`: External Secrets `ClusterSecretStore` for the centralized
  utility-cluster Vault.
- `cert-manager`: pinned cert-manager dependency wrapper.
- `cert-manager-issuers`: shared Let's Encrypt issuer and Cloudflare DNS token
  ExternalSecret.
- `external-secrets`: pinned external-secrets dependency wrapper.
- `external-dns`: ExternalDNS plus Cloudflare token ExternalSecret.
- `nfs-provisioner`: pinned NFS subdir provisioner wrapper.

## Release Model

- Chart versions are SemVer and immutable once pushed.
- Chart artifacts can be packaged manually and stored as OCI artifacts in
  `harbor.internal.api-api-api.com/helm-charts`.
- Application repositories pin chart versions in `Chart.yaml`.
- Application image tags are updated in GitOps repositories by CI.

## Tag Contract

- `app-vX.Y.Z` publishes chart `app` version `X.Y.Z`.
- `<chart-name>-vX.Y.Z` publishes chart `<chart-name>` version `X.Y.Z`.
- Docker images should use immutable tags for deployed revisions.

## Required Secrets

- `HARBOR_USERNAME`
- `HARBOR_PASSWORD`
- `TELEGRAM_BOT_TOKEN` optional
- `TELEGRAM_CHAT_ID` optional
