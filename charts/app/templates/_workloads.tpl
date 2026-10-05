{{/*
The native entrypoint and dependency wrappers share this renderer. Wrappers may
pass Values merged over the dependency defaults, plus the dependency Chart and
their own Release. Nothing is rendered until the main image is configured.
*/}}
{{- define "app.workloads" -}}
{{- if .Values.image.repository }}
{{ include "app.deployment" . }}
{{ include "app.service" . }}
{{- $root := . }}
{{- range $key, $overrides := .Values.additionalWorkloads }}
{{- if or (not (hasKey $overrides "enabled")) $overrides.enabled }}
{{- $name := printf "%s-%s" (include "app.name" $root) $key }}
{{- $resourceName := printf "%s-%s" (include "app.fullname" $root) $key }}
{{- $defaults := dict
  "name" $name "nameOverride" "" "resourceName" $resourceName "fullnameOverride" ""
  "containerName" "" "labels" (dict) "selectorLabels" (dict) "podLabels" (dict)
  "replicaCount" 1 "command" (list) "args" (list) "lifecycle" (dict)
  "ports" (list (dict "name" "http" "containerPort" 80))
  "service" (dict "enabled" true "type" "ClusterIP" "port" 80 "targetPort" "http" "annotations" (dict))
  "resources" (dict) "readinessProbe" (dict) "livenessProbe" (dict) "startupProbe" (dict)
  "persistence" (dict "enabled" false) "extraVolumes" (list) "extraVolumeMounts" (list)
  "extraContainers" (list) "initContainers" (list)
}}
{{- $inherited := pick $root.Values
  "namespace" "includeStandardLabels" "image" "imagePullSecrets" "registryPullSecret"
  "env" "envList" "envFrom" "nodeSelector" "affinity" "tolerations"
  "podSecurityContext" "securityContext" "serviceAccountName" "automountServiceAccountToken"
  "terminationGracePeriodSeconds" "ephemeral" "strategy" "revisionHistoryLimit" "progressDeadlineSeconds"
  "deploymentAnnotations" "podAnnotations" "podLabels" "extraVolumes" "extraVolumeMounts"
}}
{{- $values := mergeOverwrite $defaults (deepCopy $inherited) (deepCopy $overrides) }}
{{- $context := dict "Values" $values "Chart" $root.Chart "Release" $root.Release }}
{{ include "app.deployment" $context }}
{{ include "app.service" $context }}
{{- end }}
{{- end }}
{{- end }}
{{- end -}}

{{- define "app.deployment" -}}
{{- if .Values.image.repository }}
{{- $imagePullSecrets := include "app.imagePullSecrets" . | fromYamlArray }}
{{- $annotations := deepCopy (.Values.deploymentAnnotations | default dict) }}
{{- $strategy := deepCopy (.Values.strategy | default dict) }}
{{- if .Values.ephemeral }}
{{- $_ := set $annotations "argocd.argoproj.io/sync-wave" "3" }}
{{- $strategy = dict "type" "RollingUpdate" "rollingUpdate" (dict "maxSurge" 0 "maxUnavailable" 1) }}
{{- end }}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "app.fullname" . }}
  namespace: {{ include "app.namespace" . }}
  labels:
    {{- include "app.labels" . | nindent 4 }}
  {{- with $annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  replicas: {{ .Values.replicaCount }}
  {{- with $strategy }}
  strategy:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  {{- if ne .Values.revisionHistoryLimit nil }}
  revisionHistoryLimit: {{ .Values.revisionHistoryLimit }}
  {{- end }}
  {{- if ne .Values.progressDeadlineSeconds nil }}
  progressDeadlineSeconds: {{ .Values.progressDeadlineSeconds }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "app.selectorLabels" . | nindent 8 }}
        {{- with .Values.podLabels }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      {{- with .Values.podAnnotations }}
      annotations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
    spec:
      {{- with .Values.terminationGracePeriodSeconds }}
      terminationGracePeriodSeconds: {{ . }}
      {{- end }}
      {{- with .Values.serviceAccountName }}
      serviceAccountName: {{ . }}
      {{- end }}
      {{- if ne .Values.automountServiceAccountToken nil }}
      automountServiceAccountToken: {{ .Values.automountServiceAccountToken }}
      {{- end }}
      {{- with .Values.podSecurityContext }}
      securityContext:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with $imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.initContainers }}
      initContainers:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      containers:
        - name: {{ default (include "app.name" .) .Values.containerName }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          {{- with .Values.securityContext }}
          securityContext:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.lifecycle }}
          lifecycle:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.command }}
          command:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.args }}
          args:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- if or .Values.env .Values.envList }}
          env:
            {{- range $key, $value := .Values.env }}
            - name: {{ $key }}
              value: {{ $value | quote }}
            {{- end }}
            {{- with .Values.envList }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
          {{- end }}
          {{- with .Values.envFrom }}
          envFrom:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.ports }}
          ports:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.readinessProbe }}
          readinessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.livenessProbe }}
          livenessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.startupProbe }}
          startupProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.resources }}
          resources:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- if or .Values.persistence.enabled .Values.extraVolumeMounts }}
          volumeMounts:
            {{- if .Values.persistence.enabled }}
            - name: {{ .Values.persistence.name }}
              mountPath: {{ .Values.persistence.mountPath }}
            {{- end }}
            {{- with .Values.extraVolumeMounts }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
          {{- end }}
        {{- with .Values.extraContainers }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      {{- if or .Values.persistence.enabled .Values.extraVolumes }}
      volumes:
        {{- if .Values.persistence.enabled }}
        - name: {{ .Values.persistence.name }}
          persistentVolumeClaim:
            claimName: {{ default (printf "%s-data" (include "app.fullname" .)) .Values.persistence.claimName }}
        {{- end }}
        {{- with .Values.extraVolumes }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      {{- end }}
{{- end }}
{{- end -}}

{{- define "app.service" -}}
{{- if and .Values.service.enabled .Values.image.repository }}
---
apiVersion: v1
kind: Service
metadata:
  name: {{ include "app.fullname" . }}
  namespace: {{ include "app.namespace" . }}
  labels:
    {{- include "app.labels" . | nindent 4 }}
  {{- with .Values.service.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  type: {{ .Values.service.type }}
  selector:
    {{- include "app.selectorLabels" . | nindent 4 }}
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
      {{- with .Values.service.protocol }}
      protocol: {{ . }}
      {{- end }}
{{- end }}
{{- end -}}
