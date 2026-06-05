# app

Reusable Helm chart for small GitOps-managed applications.

The chart supports two deployment styles:

- native chart resources through `image`, `service`, `ingress`, `persistence`, `externalSecrets`, and `configMaps`;
- structured Kubernetes objects through `objects` for workloads that need multiple resources while still avoiding raw manifest strings.

Use native fields for typical single-workload applications:

- `deployment.strategy`, `containerName`, `lifecycle`, `terminationGracePeriodSeconds`;
- `registryPullSecret`, `externalSecrets`, `env`, `envList`, `envFrom`;
- `persistence`, `extraVolumes`, `extraVolumeMounts`, `initContainers`;
- `ingress.host`, `ingress.path`, or `ingress.paths` for multiple paths on one host.

## OCI Release

Use SemVer tags for chart releases:

```bash
git tag app-v0.4.3
git push origin app-v0.4.3
```

The release workflow publishes:

```bash
helm package charts/app
helm push app-0.4.3.tgz oci://harbor.api-api-api.com/helm-charts
```

Consumer app charts should pin the chart version:

```yaml
dependencies:
- name: app
  alias: app
  version: 0.4.3
  repository: oci://harbor.api-api-api.com/helm-charts
```

## Image Updates

CI should update app `values.yaml`, not live cluster state. For structured objects, update:

```yaml
app:
  images:
    api:
      repository: harbor.api-api-api.com/example/api
      tag: sha-0123456789ab
```

The chart renders `__IMAGE_api__` as `repository:tag`. Use immutable `sha-*` or SemVer image tags for deployed revisions.
