# common-apps

Reusable Helm chart for small GitOps-managed applications.

The chart supports two deployment styles:

- native chart resources through `image`, `service`, `ingress`, `persistence`, `externalSecrets`, and `configMaps`;
- structured Kubernetes objects through `objects` for workloads that need multiple resources while still avoiding raw manifest strings.

## OCI Release

Use SemVer tags for chart releases:

```bash
git tag common-apps-v0.3.0
git push origin common-apps-v0.3.0
```

The release workflow publishes:

```bash
helm package charts/common-apps
helm push common-apps-0.3.0.tgz oci://harbor.api-api-api.com/helm-charts
```

Consumer app charts should pin the chart version:

```yaml
dependencies:
- name: common-apps
  alias: common-app
  version: 0.3.0
  repository: oci://harbor.api-api-api.com/helm-charts
```

## Image Updates

CI should update app `values.yaml`, not live cluster state. For structured objects, update:

```yaml
common-app:
  images:
    api:
      repository: harbor.api-api-api.com/example/api
      tag: sha-0123456789ab
```

The chart renders `__IMAGE_api__` as `repository:tag`. Use immutable `sha-*` or SemVer image tags for deployed revisions.
