# app

Reusable Helm chart for small GitOps-managed applications.

The default chart renders no resources. Each optional capability is enabled by
the application wrapper, so the chart has no implicit dependency on a specific
namespace, registry, Vault instance, or image pull secret.

The chart supports two deployment styles:

- native chart resources through `image`, `service`, `httpRoute`, `ingress`,
  `persistence`, `externalSecrets`, and `configMaps`;
- structured Kubernetes objects through `objects` for the rare workload that
  needs multiple resources. Objects are rendered as supplied, except for
  `__IMAGE_<name>__` image placeholders.

Use native fields for typical single-workload applications:

- `name` for the application label name;
- `resourceName` for generated Kubernetes resource names;
- `registryPullSecret.enabled` only for images hosted in the private registry;
- `containerName`, `lifecycle`, `terminationGracePeriodSeconds`;
- `externalSecrets`, `env`, `envList`, `envFrom`;
- `persistence`, `extraVolumes`, `extraVolumeMounts`, `initContainers`;
- `httpRoute` for the cluster's Gateway API public route;
- `ingress.host`, `ingress.path`, or `ingress.paths` for multiple paths on one host.

## OCI Release

Use SemVer tags for chart releases:

```bash
git tag app-v0.5.0
git push origin app-v0.5.0
```

The release workflow publishes:

```bash
helm package charts/app
helm push app-0.5.0.tgz oci://harbor.api-api-api.com/helm-charts
```

Consumer app charts should pin the chart version:

```yaml
dependencies:
- name: app
  alias: app
  version: 0.5.0
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
