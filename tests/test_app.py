"""Offline render contracts for the reusable app chart.

Run with ``python -m unittest discover -s tests -v`` after installing Helm and
PyYAML. These tests do not need a registry, a cluster, or repository history.
"""

from copy import deepcopy
from pathlib import Path
import subprocess
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "charts/app"
RELEASE = "example-release"
NAMESPACE = "example-namespace"


def render(values=None):
    result = subprocess.run(
        ["helm", "template", RELEASE, str(CHART), "--namespace", NAMESPACE,
         "--values", "-"],
        input=yaml.safe_dump(values or {}), text=True, capture_output=True,
    )
    if result.returncode:
        raise AssertionError(f"Helm rendering failed:\n{result.stderr}")
    return [document for document in yaml.safe_load_all(result.stdout) if document]


def resource(documents, kind, name=None):
    matches = [document for document in documents if document["kind"] == kind
               and (name is None or document["metadata"]["name"] == name)]
    if len(matches) != 1:
        raise AssertionError(f"Expected one {kind} {name!r}; found {len(matches)}")
    return matches[0]


class NativeAppCompatibilityTests(unittest.TestCase):
    """The native 0.5.1 behavior stays available without wrapper options."""

    def test_empty_chart_still_emits_no_workloads(self):
        self.assertEqual(render(), [])

    def test_default_image_render_preserves_complete_legacy_manifest(self):
        version = yaml.safe_load((CHART / "Chart.yaml").read_text())["version"]
        labels = {
            "app.kubernetes.io/name": "app",
            "app.kubernetes.io/instance": RELEASE,
            "app.kubernetes.io/managed-by": "Helm",
            "helm.sh/chart": "app-" + version,
        }
        selector = {key: labels[key] for key in (
            "app.kubernetes.io/name", "app.kubernetes.io/instance")}
        metadata = {"name": RELEASE, "namespace": NAMESPACE, "labels": labels}
        expected = [
            {"apiVersion": "v1", "kind": "Service", "metadata": metadata,
             "spec": {"type": "ClusterIP", "selector": selector,
                      "ports": [{"name": "http", "port": 80, "targetPort": "http"}]}},
            {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": metadata,
             "spec": {"replicas": 1, "selector": {"matchLabels": selector},
                      "template": {"metadata": {"labels": selector}, "spec": {
                          "containers": [{"name": "app", "image": "example/api:v1",
                                          "imagePullPolicy": "IfNotPresent",
                                          "ports": [{"name": "http", "containerPort": 80}]}]}}}},
        ]
        actual = render({"image": {"repository": "example/api", "tag": "v1"}})
        self.assertEqual(actual, expected)

    def test_legacy_aliases_explicit_names_and_selector_are_preserved(self):
        values = {
            "image": {"repository": "example/api", "tag": "v1"},
            "nameOverride": "legacy-app", "fullnameOverride": "legacy-resource",
            "selectorLabels": {"app": "legacy-selector"},
            "namespace": {"name": "custom-namespace"},
            "podLabels": {"component": "api"}, "labels": {"owner": "example"},
        }
        for modern in (False, True):
            with self.subTest(modern=modern):
                selected = deepcopy(values)
                if modern:
                    selected.update(name="modern-app", resourceName="modern-resource")
                documents = render(selected)
                deployment = resource(documents, "Deployment")
                service = resource(documents, "Service")
                self.assertEqual(deployment["metadata"]["name"],
                                 "modern-resource" if modern else "legacy-resource")
                self.assertEqual(deployment["metadata"]["namespace"], "custom-namespace")
                self.assertEqual(deployment["metadata"]["labels"]["owner"], "example")
                self.assertEqual(deployment["spec"]["selector"]["matchLabels"], {"app": "legacy-selector"})
                self.assertEqual(service["spec"]["selector"], {"app": "legacy-selector"})
                pod = deployment["spec"]["template"]
                self.assertEqual(pod["metadata"]["labels"],
                                 {"app": "legacy-selector", "component": "api"})
                self.assertEqual(pod["spec"]["containers"][0]["name"],
                                 "modern-app" if modern else "legacy-app")

    def test_existing_container_extension_points_are_preserved(self):
        values = {
            "image": {"repository": "example/api", "tag": "v1"},
            "containerName": "api", "command": ["node"], "args": ["server.js"],
            "env": {"FEATURE": "false", "PORT": 8080},
            "envList": [{"name": "TOKEN", "valueFrom": {
                "secretKeyRef": {"name": "credentials", "key": "token"}}}],
            "envFrom": [{"configMapRef": {"name": "app-settings"}}],
            "lifecycle": {"preStop": {"exec": {"command": ["sleep", "5"]}}},
            "ports": [{"name": "http", "containerPort": 8080}],
            "readinessProbe": {"tcpSocket": {"port": "http"}},
            "livenessProbe": {"httpGet": {"path": "/health", "port": "http"}},
            "resources": {"requests": {"cpu": "25m", "memory": "32Mi"}},
            "extraVolumeMounts": [{"name": "scratch", "mountPath": "/tmp"}],
            "extraVolumes": [{"name": "scratch", "emptyDir": {"sizeLimit": "32Mi"}}],
            "initContainers": [{"name": "init", "image": "example/init:v1"}],
            "extraContainers": [{"name": "sidecar", "image": "example/sidecar:v1"}],
            "podAnnotations": {"example.com/config": "v1"},
            "terminationGracePeriodSeconds": 15,
        }
        deployment = resource(render(values), "Deployment")
        template = deployment["spec"]["template"]
        pod = template["spec"]
        container = pod["containers"][0]
        for key in ("command", "args", "envFrom", "lifecycle", "ports", "readinessProbe",
                    "livenessProbe", "resources"):
            self.assertEqual(container[key], values[key])
        self.assertEqual(container["name"], "api")
        self.assertEqual(container["env"], [
            {"name": "FEATURE", "value": "false"}, {"name": "PORT", "value": "8080"},
            *values["envList"],
        ])
        self.assertEqual(container["volumeMounts"], values["extraVolumeMounts"])
        self.assertEqual(pod["volumes"], values["extraVolumes"])
        self.assertEqual(pod["initContainers"], values["initContainers"])
        self.assertEqual(pod["containers"][1:], values["extraContainers"])
        self.assertEqual(template["metadata"]["annotations"], values["podAnnotations"])
        self.assertEqual(pod["terminationGracePeriodSeconds"], 15)

    def test_pull_secret_fallback_does_not_replace_explicit_secrets(self):
        values = {"image": {"repository": "example/api", "tag": "v1"},
                  "registryPullSecret": {"enabled": True, "name": "registry"}}
        for explicit in ([], [{"name": "explicit"}]):
            with self.subTest(explicit=explicit):
                documents = render(dict(values, imagePullSecrets=explicit))
                pod = resource(documents, "Deployment")["spec"]["template"]["spec"]
                self.assertEqual(pod["imagePullSecrets"], explicit or [{"name": "registry"}])
                self.assertEqual(resource(documents, "ExternalSecret")["metadata"]["name"], "registry")

    def test_persistence_and_extra_objects_remain_independent(self):
        values = {
            "image": {"repository": "example/api", "tag": "v1"},
            "persistence": {"enabled": True, "claimName": "retained-data"},
            "images": {"job": {"repository": "example/job", "tag": "v2"}},
            "objects": [{"apiVersion": "v1", "kind": "ConfigMap",
                         "metadata": {"name": "first"}, "data": {"image": "__IMAGE_job__"}}],
            "extraObjects": [{"apiVersion": "v1", "kind": "ConfigMap",
                              "metadata": {"name": "second"}, "data": {"setting": "value"}}],
        }
        documents = render(values)
        claim = resource(documents, "PersistentVolumeClaim", "retained-data")
        self.assertEqual(claim["spec"]["resources"]["requests"]["storage"], "1Gi")
        pod = resource(documents, "Deployment")["spec"]["template"]["spec"]
        self.assertEqual(pod["volumes"], [
            {"name": "data", "persistentVolumeClaim": {"claimName": "retained-data"}}])
        self.assertEqual(pod["containers"][0]["volumeMounts"], [{"name": "data", "mountPath": "/data"}])
        self.assertEqual(resource(documents, "ConfigMap", "first")["data"]["image"], "example/job:v2")
        self.assertEqual(resource(documents, "ConfigMap", "second")["data"], {"setting": "value"})


class GenericWorkloadTests(unittest.TestCase):
    def values(self):
        return {"name": "api", "resourceName": "api", "replicaCount": 3,
                "image": {"repository": "example/api", "tag": "v1"}}

    def test_optional_deployment_pod_and_container_fields_round_trip(self):
        values = self.values()
        deployment_fields = {
            "revisionHistoryLimit": 0, "progressDeadlineSeconds": 600,
            "strategy": {"type": "RollingUpdate", "rollingUpdate": {
                "maxUnavailable": 0, "maxSurge": 1}},
        }
        pod_fields = {
            "serviceAccountName": "runtime", "automountServiceAccountToken": False,
            "nodeSelector": {"kubernetes.io/hostname": "worker-2"},
            "affinity": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {
                "nodeSelectorTerms": [{"matchExpressions": [{
                    "key": "node-role.kubernetes.io/control-plane", "operator": "DoesNotExist"}]}]}}},
            "tolerations": [{"key": "dedicated", "operator": "Equal", "value": "apps", "effect": "NoSchedule"}],
        }
        container_fields = {
            "securityContext": {"runAsNonRoot": True, "readOnlyRootFilesystem": True,
                                "allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}},
            "startupProbe": {"httpGet": {"path": "/healthz", "port": "http"}, "failureThreshold": 60},
        }
        values.update(deployment_fields)
        values.update(pod_fields)
        values.update(container_fields)
        values["podSecurityContext"] = {"fsGroup": 1000, "seccompProfile": {"type": "RuntimeDefault"}}
        values["deploymentAnnotations"] = {"example.com/rollout": "controlled"}
        deployment = resource(render(values), "Deployment")
        self.assertEqual(deployment["metadata"]["annotations"], values["deploymentAnnotations"])
        for key, expected in deployment_fields.items():
            self.assertEqual(deployment["spec"][key], expected)
        pod = deployment["spec"]["template"]["spec"]
        for key, expected in pod_fields.items():
            self.assertEqual(pod[key], expected)
        self.assertEqual(pod["securityContext"], values["podSecurityContext"])
        for key, expected in container_fields.items():
            self.assertEqual(pod["containers"][0][key], expected)

    def test_custom_labels_and_service_protocol_do_not_gain_managed_labels(self):
        values = self.values()
        values.update(
            includeStandardLabels=False,
            labels={"app.kubernetes.io/name": "api", "app.kubernetes.io/part-of": "example"},
            selectorLabels={"app.kubernetes.io/name": "api", "app.kubernetes.io/instance": RELEASE},
            podLabels={"app.kubernetes.io/component": "backend"},
            service={"port": 8080, "targetPort": "http", "protocol": "TCP"},
        )
        documents = render(values)
        for document in documents:
            self.assertEqual(document["metadata"]["labels"], values["labels"])
        service = resource(documents, "Service")
        self.assertEqual(service["spec"]["ports"], [{
            "name": "http", "port": 8080, "targetPort": "http", "protocol": "TCP"}])
        deployment = resource(documents, "Deployment")
        self.assertEqual(deployment["spec"]["template"]["metadata"]["labels"],
                         dict(values["selectorLabels"], **values["podLabels"]))

    def test_additional_workload_inherits_shared_fields_without_mutating_parent(self):
        values = self.values()
        values.update(
            env={"SHARED": "inherited", "OVERRIDE": "parent"},
            envList=[{"name": "ROOT_LIST", "value": "parent"}],
            envFrom=[{"secretRef": {"name": "runtime-env"}}],
            nodeSelector={"kubernetes.io/hostname": "worker-2"},
            serviceAccountName="runtime", automountServiceAccountToken=False,
            imagePullSecrets=[{"name": "registry"}],
            securityContext={"runAsUser": 1000}, podSecurityContext={"fsGroup": 1000},
            resources={"requests": {"memory": "128Mi"}},
            command=["node", "api.js"], args=["--serve"],
            ports=[{"name": "http", "containerPort": 8080}],
            readinessProbe={"httpGet": {"path": "/ready", "port": "http"}},
            service={"port": 8080},
            additionalWorkloads={
                "worker": {
                    "env": {"OVERRIDE": "child", "CHILD": "only"},
                    "envList": [{"name": "CHILD_LIST", "value": "child"}],
                    "command": ["node", "worker.js"],
                },
                "disabled": {"enabled": False},
            },
        )
        documents = render(values)
        self.assertEqual({(d["kind"], d["metadata"]["name"]) for d in documents}, {
            ("Deployment", "api"), ("Service", "api"),
            ("Deployment", "api-worker"), ("Service", "api-worker"),
        })
        main = resource(documents, "Deployment", "api")
        worker = resource(documents, "Deployment", "api-worker")
        self.assertEqual(main["spec"]["replicas"], 3)
        self.assertEqual(worker["spec"]["replicas"], 1)
        pod = worker["spec"]["template"]["spec"]
        for key in ("nodeSelector", "serviceAccountName", "automountServiceAccountToken", "imagePullSecrets"):
            self.assertEqual(pod[key], values[key])
        self.assertEqual(pod["securityContext"], values["podSecurityContext"])
        container = pod["containers"][0]
        self.assertEqual(container["image"], "example/api:v1")
        self.assertEqual(container["securityContext"], values["securityContext"])
        self.assertEqual(container["envFrom"], values["envFrom"])
        environment = {item["name"]: item["value"] for item in container["env"]}
        self.assertEqual(environment, {"SHARED": "inherited", "OVERRIDE": "child",
                                       "CHILD": "only", "CHILD_LIST": "child"})
        parent_environment = {item["name"]: item["value"] for item in
                              main["spec"]["template"]["spec"]["containers"][0]["env"]}
        self.assertEqual(parent_environment, {"SHARED": "inherited", "OVERRIDE": "parent", "ROOT_LIST": "parent"})
        self.assertEqual(container["command"], ["node", "worker.js"])
        for independent in ("args", "resources", "readinessProbe"):
            self.assertNotIn(independent, container)
        self.assertEqual(container["ports"], [{"name": "http", "containerPort": 80}])
        self.assertEqual(resource(documents, "Service", "api-worker")["spec"]["ports"][0]["port"], 80)
        self.assertNotEqual(main["spec"]["selector"], worker["spec"]["selector"])

    def test_additional_workload_explicit_overrides_and_disabled_service(self):
        values = self.values()
        child = {
            "name": "relay", "resourceName": "outbox-relay", "containerName": "relay-process",
            "replicaCount": 2, "image": {"repository": "example/relay", "tag": "v2"},
            "nodeSelector": {"kubernetes.io/hostname": "worker-3"},
            "resources": {"limits": {"memory": "256Mi"}},
            "startupProbe": {"tcpSocket": {"port": 3005}},
            "ports": [{"name": "http", "containerPort": 3005}],
            "service": {"enabled": False},
        }
        values["additionalWorkloads"] = {"worker": child}
        documents = render(values)
        self.assertEqual(len(documents), 3)
        deployment = resource(documents, "Deployment", "outbox-relay")
        self.assertEqual(deployment["spec"]["replicas"], 2)
        pod = deployment["spec"]["template"]["spec"]
        self.assertEqual(pod["nodeSelector"], child["nodeSelector"])
        container = pod["containers"][0]
        self.assertEqual(container["name"], "relay-process")
        self.assertEqual(container["image"], "example/relay:v2")
        for key in ("resources", "startupProbe", "ports"):
            self.assertEqual(container[key], child[key])

    def test_ephemeral_strategy_and_wave_apply_to_main_and_additional_workloads(self):
        values = self.values()
        values.update(
            ephemeral=True,
            deploymentAnnotations={"example.com/owner": "preview"},
            strategy={"type": "RollingUpdate", "rollingUpdate": {"maxUnavailable": 0, "maxSurge": 1}},
            additionalWorkloads={"worker": {}},
        )
        for deployment in (d for d in render(values) if d["kind"] == "Deployment"):
            with self.subTest(name=deployment["metadata"]["name"]):
                self.assertEqual(deployment["metadata"]["annotations"], {
                    "example.com/owner": "preview", "argocd.argoproj.io/sync-wave": "3"})
                self.assertEqual(deployment["spec"]["strategy"], {
                    "type": "RollingUpdate", "rollingUpdate": {"maxUnavailable": 1, "maxSurge": 0}})


class VaultStaticSecretTests(unittest.TestCase):
    def test_optional_vso_resources_preserve_metadata_and_spec_without_eso(self):
        spec = {
            "type": "kv-v2", "mount": "kv", "path": "apps/example",
            "vaultAuthRef": "runtime", "refreshAfter": "1m",
            "destination": {"create": True, "name": "runtime-env", "transformation": {
                "excludeRaw": True, "templates": {"TOKEN": {"text": '{{ get .Secrets "token" }}'}}}},
            "rolloutRestartTargets": [{"kind": "Deployment", "name": "api"}],
        }
        entries = [
            {"name": "runtime-env", "namespace": "custom-namespace",
             "labels": {"app.kubernetes.io/part-of": "example"},
             "annotations": {"argocd.argoproj.io/sync-wave": "-1"}, "spec": spec},
            {"name": "default-namespace-env", "spec": spec},
        ]
        documents = render({"vaultStaticSecrets": entries})
        self.assertEqual(documents, [
            {"apiVersion": "secrets.hashicorp.com/v1beta1", "kind": "VaultStaticSecret",
             "metadata": {"name": entry["name"], "namespace": entry.get("namespace", NAMESPACE),
                          **{key: entry[key] for key in ("labels", "annotations") if key in entry}},
             "spec": spec}
            for entry in entries
        ])

    def test_missing_required_vso_fields_fail_with_clear_diagnostics(self):
        valid = {"name": "runtime-env", "spec": {"type": "kv-v2", "mount": "kv", "path": "apps/example"}}
        for missing in ("name", "spec"):
            with self.subTest(missing=missing):
                entry = {key: value for key, value in valid.items() if key != missing}
                with self.assertRaisesRegex(AssertionError, "vaultStaticSecrets entries require " + missing):
                    render({"vaultStaticSecrets": [entry]})


if __name__ == "__main__":
    unittest.main()
