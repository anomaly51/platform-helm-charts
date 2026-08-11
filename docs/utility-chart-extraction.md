# Utility Chart Extraction

Date: 2026-06-05

## Before

Both GitOps repositories carried duplicate local chart code under
`utility-apps/*`.

- `cloudflared`: full templates duplicated in both clusters; only tunnel UUID,
  tunnel target, Vault key, and ArgoCD hostname differed.
- `vault-store`: duplicated `ClusterSecretStore`; only Vault server differed.
- `cert-manager`: duplicated wrapper over the upstream Jetstack chart.
- `cert-manager-issuers`: identical local issuer and Cloudflare ExternalSecret
  templates.
- `external-secrets`: duplicated wrapper over the upstream external-secrets
  chart.
- `external-dns`: duplicated wrapper over the upstream external-dns chart; only
  `txtOwnerId` differed.
- `external-dns-config`: separate duplicated chart for namespace and Cloudflare
  token ExternalSecret.
- `nfs-provisioner`: duplicated wrapper over the upstream NFS provisioner chart;
  workload-1 also set `storageClass.provisionerName`.

Baseline manifests were rendered into:

```text
/tmp/devops-v2-helm-baseline-before/rendered
```

## After

Reusable implementation now lives in `platform-helm-charts/charts/*`.

- `cloudflared` is a shared chart. Cluster repos keep only tunnel and hostname
  values under `platform-cloudflared`.
- `vault-store` is a shared chart. Utility points at the in-cluster Vault
  service; workload clusters point at `https://vault.api-api-api.com`.
- `cert-manager`, `external-secrets`, and `nfs-provisioner` are shared pinned
  dependency wrappers.
- `cert-manager-issuers` is a shared chart with parameterized issuer and
  ExternalSecret fields.
- `external-dns-config` was folded into the shared `external-dns` chart, so
  `external-dns` now renders the namespace, Cloudflare token ExternalSecret,
  and upstream controller together.

Cluster GitOps repositories consume the platform charts from:

```text
oci://harbor.internal.api-api-api.com/helm-charts
```

Each consumer chart pins version `0.1.0` and uses an alias such as
`platform-cloudflared` or `platform-external-dns` for cluster-specific values.

## Vault Rule

HashiCorp Vault remains deployed only in the utility cluster. Workload clusters
reuse the centralized Vault via `vault-store` and must not deploy a separate
Vault instance for the same platform secret data.

## Verification

Before manifests were rendered from the original local cluster charts.

After manifests were rendered by packaging the new platform charts in a
temporary directory and placing those packages into temporary copies of the
consumer chart `charts/` directories. This verifies the same dependency shape
that ArgoCD will use after the `0.1.0` chart versions are published to Harbor.

Verification commands covered:

- `helm dependency build` for platform charts with upstream dependencies.
- `helm lint` for every new platform chart.
- `helm package` for every new platform chart.
- `helm lint` for every changed consumer wrapper.
- `helm template` for both clusters after dependency packaging.
- Ruby YAML comparison by `apiVersion/kind/namespace/name` between before and
  after rendered Kubernetes objects.

Result:

```text
utility-k3s-argocd/cloudflared: semantic-identical
utility-k3s-argocd/vault-store: semantic-identical
utility-k3s-argocd/cert-manager: semantic-identical
utility-k3s-argocd/cert-manager-issuers: semantic-identical
utility-k3s-argocd/external-secrets: semantic-identical
utility-k3s-argocd/nfs-provisioner: semantic-identical
utility-k3s-argocd/external-dns combined: semantic-identical
workload-1-k3s-argocd/cloudflared: semantic-identical
workload-1-k3s-argocd/vault-store: semantic-identical
workload-1-k3s-argocd/cert-manager: semantic-identical
workload-1-k3s-argocd/cert-manager-issuers: semantic-identical
workload-1-k3s-argocd/external-secrets: semantic-identical
workload-1-k3s-argocd/nfs-provisioner: semantic-identical
workload-1-k3s-argocd/external-dns combined: semantic-identical
```

The first verification pass exposed one migration bug: the NFS consumer wrapper
still referenced the upstream chart name `nfs-subdir-external-provisioner`
instead of the new platform chart name `nfs-provisioner`. The wrapper dependency
names were corrected in both cluster repositories before the final successful
render comparison.
