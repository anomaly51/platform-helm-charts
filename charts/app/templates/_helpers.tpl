{{- define "app.name" -}}
{{- default .Chart.Name (default .Values.nameOverride .Values.name) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "app.fullname" -}}
{{- $resourceName := default .Values.fullnameOverride .Values.resourceName -}}
{{- if $resourceName -}}
{{- $resourceName | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "app.namespace" -}}
{{- default .Release.Namespace .Values.namespace.name -}}
{{- end -}}

{{- define "app.labels" -}}
app.kubernetes.io/name: {{ include "app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- with .Values.labels }}
{{- toYaml . | nindent 0 }}
{{- end }}
{{- end -}}

{{- define "app.selectorLabels" -}}
{{- if .Values.selectorLabels -}}
{{- toYaml .Values.selectorLabels -}}
{{- else -}}
app.kubernetes.io/name: {{ include "app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
{{- end -}}

{{- define "app.imagePullSecrets" -}}
{{- $secrets := .Values.imagePullSecrets | default (list) -}}
{{- if and (empty $secrets) .Values.registryPullSecret.enabled -}}
{{- $secrets = list (dict "name" .Values.registryPullSecret.name) -}}
{{- end -}}
{{- toYaml $secrets -}}
{{- end -}}
