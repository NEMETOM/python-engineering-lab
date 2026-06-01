{{/*
Return the image name for a given service.
Usage: {{ include "fix-simulator.image" (dict "root" . "name" "fix-gateway") }}
*/}}
{{- define "fix-simulator.image" -}}
{{- $registry := .root.Values.image.registry -}}
{{- $tag := .root.Values.image.tag -}}
{{- if $registry -}}
{{ $registry }}/{{ .name }}:{{ $tag }}
{{- else -}}
{{ .name }}:{{ $tag }}
{{- end -}}
{{- end -}}

{{/*
Common labels applied to all resources.
*/}}
{{- define "fix-simulator.labels" -}}
app.kubernetes.io/part-of: fix-simulator-pro
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{/*
Database URL constructed from postgres values.
*/}}
{{- define "fix-simulator.databaseUrl" -}}
postgresql://{{ .Values.postgres.credentials.user }}:{{ .Values.postgres.credentials.password }}@postgres:5432/{{ .Values.postgres.credentials.database }}
{{- end -}}
