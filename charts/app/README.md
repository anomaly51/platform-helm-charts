# app

Reusable Helm chart for small GitOps-managed applications.

The default chart renders no resources. Each optional capability is enabled by
the application wrapper, so the chart has no implicit dependency on a specific
namespace, registry, Vault instance, or image pull secret.

The chart supports two deployment styles:

- native chart resources through `image`, `service`, `httpRoute`, `ingress`,
  `persistence`, `externalSecrets`, `vaultStaticSecrets`, `configMaps`, and
  `additionalWorkloads`;
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

## Workload settings

Keep the main application's image at `image.repository` and `image.tag`.
The default values preserve the 0.5.1 Deployment and Service shape, apart from
the chart-version label. An empty main image repository disables both the main
and additional workloads.

Set these optional fields at the root or inside an `additionalWorkloads` entry:

- `nodeSelector`, `affinity`, `tolerations` for placement;
- `podSecurityContext` for the Pod and `securityContext` for the main container;
- `serviceAccountName` and `automountServiceAccountToken` for Pod credentials;
- `startupProbe`, `readinessProbe`, `livenessProbe` for container health checks;
- `deploymentAnnotations`, `strategy`, `revisionHistoryLimit`, and
  `progressDeadlineSeconds` for Deployment configuration.

Use `automountServiceAccountToken: false` to disable token mounting. Leave it
`null` to omit the field. You can set `revisionHistoryLimit: 0` to retain no old
ReplicaSets. Set `service.protocol` to include a protocol in the Service port;
the default omits this field.

Set `ephemeral: true` for preview workloads. This setting overrides the
Deployment sync wave with `argocd.argoproj.io/sync-wave: "3"` and the rollout
strategy with `RollingUpdate`, `maxSurge: 0`, `maxUnavailable: 1`. It does not
change the workload's replica count, namespace, or secret ownership.

For an existing resource, set `resourceName`, `name`, `containerName`, and
`selectorLabels` to its current identities. Set `includeStandardLabels: false`
and supply `labels` to omit the generated metadata labels. `podLabels` adds
labels to the Pod template; it does not change the Deployment or Service
selectors.

## Additional workloads

Define independent Deployments and Services under `additionalWorkloads`:

```yaml
image:
  repository: example/api
  tag: sha-0123456789ab
env:
  LOG_LEVEL: info
  MODE: api
nodeSelector:
  kubernetes.io/os: linux
automountServiceAccountToken: false
additionalWorkloads:
  worker:
    replicaCount: 2
    command: [node, worker.js]
    env:
      MODE: worker
    ports:
      - name: http
        containerPort: 9090
    service:
      port: 9090
      targetPort: http
    readinessProbe:
      httpGet:
        path: /ready
        port: http
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
```

The worker uses the main image, `LOG_LEVEL`, node selector, and token policy.
Its `MODE` overrides the main value. It runs in a separate Deployment with its
own selector, Service, command, replica count, ports, and resources. Set
`enabled: false` on an entry to omit it, or `service.enabled: false` to omit its
Service.

Additional workloads inherit these root fields:

- `namespace`, `includeStandardLabels`, `image`, `imagePullSecrets`,
  `registryPullSecret`;
- `env`, `envList`, `envFrom`, `nodeSelector`, `affinity`, `tolerations`;
- `podSecurityContext`, `securityContext`, `serviceAccountName`,
  `automountServiceAccountToken`, `terminationGracePeriodSeconds`;
- `ephemeral`, `strategy`, `revisionHistoryLimit`, `progressDeadlineSeconds`,
  `deploymentAnnotations`, `podAnnotations`, `podLabels`;
- `extraVolumes`, `extraVolumeMounts`.

Workload overrides merge maps, including `image` and `env`; they replace lists,
including `envList`, `envFrom`, and `tolerations`. An empty map does not clear
an inherited map. Use an empty list to clear an inherited list. These merges
do not modify the main workload or another additional workload.

Other fields use independent defaults: one replica, port 80 named `http`,
a ClusterIP Service on port 80, and no commands, probes, resources, sidecars,
init containers, or persistence. Metadata `labels` and `selectorLabels` also
start empty. Default names append `-<key>` to the main application and resource
names. Override `name`, `resourceName`, `containerName`, or `selectorLabels`
when adopting an existing workload.

Configure a PVC through root `persistence` or another chart resource if an
additional workload needs persistent storage; additional workloads do not
create PVCs. To use a pre-existing claim, set the workload's `persistence`
fields, including `claimName`, `name`, and `mountPath`.

## Wrapper entrypoint

For a wrapper that keeps its public values at the root, include `app.workloads`
with the dependency defaults merged into those values:

```gotemplate
{{- $values := mergeOverwrite (deepCopy .Subcharts.app.Values) .Values -}}
{{- include "app.workloads" (dict "Values" $values "Release" .Release "Chart" .Subcharts.app.Chart) -}}
```

Keep the dependency's own `app.image.repository` empty to prevent duplicate
resources. The native chart entrypoint uses this same renderer.
`app.workloads` renders Deployments and Services; other native resources use
their own templates and dependency values.

## Vault Secrets Operator

Keep `vaultStaticSecrets: []` unless you use Vault Secrets Operator. Each entry
requires a name and a native `VaultStaticSecret` spec:

```yaml
vaultStaticSecrets:
  - name: application-credentials
    annotations:
      argocd.argoproj.io/sync-wave: "-1"
    spec:
      vaultAuthRef: application-auth
      mount: kv
      type: kv-v2
      path: application/credentials
      refreshAfter: 1m
      destination:
        create: true
        name: application-credentials
```

You can supply `namespace` and `labels` per entry. Install the
`secrets.hashicorp.com/v1beta1` CRDs and configure Vault authentication outside
this chart. Existing `externalSecrets` and `registryPullSecret` settings still
use External Secrets Operator without changes.

## OCI Release

Run chart validation before publishing a release. The GitHub workflow validates
the chart; it does not publish packages. Use SemVer tags to identify releases:

```bash
git tag app-v0.6.0
git push origin app-v0.6.0
```

Package and publish to the OCI registry with your registry credentials:

```bash
helm package charts/app
helm push app-0.6.0.tgz oci://harbor.internal.api-api-api.com/helm-charts
```

Consumer app charts should pin the chart version:

```yaml
dependencies:
- name: app
  alias: app
  version: 0.6.0
  repository: oci://harbor.internal.api-api-api.com/helm-charts
```

## Image Updates

CI should update app `values.yaml`, not live cluster state. For structured objects, update:

```yaml
app:
  images:
    api:
      repository: harbor.internal.api-api-api.com/example/api
      tag: sha-0123456789ab
```

The chart renders `__IMAGE_api__` as `repository:tag`. Use immutable `sha-*` or SemVer image tags for deployed revisions.
