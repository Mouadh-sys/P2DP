package p2dp.kubernetes.security

resource_identifier(obj) = resource {
  kind := obj.kind
  name := obj.metadata.name
  resource := sprintf("%s/%s", [kind, name])
} else = resource {
  resource := obj.kind
} else = "unknown"

container_name(container) = name {
  name := container.name
} else = "unnamed"

pod_spec(obj) = spec {
  obj.kind == "Pod"
  spec := obj.spec
}

pod_spec(obj) = spec {
  obj.kind == "Deployment"
  spec := obj.spec.template.spec
}

pod_spec(obj) = spec {
  obj.kind == "ReplicaSet"
  spec := obj.spec.template.spec
}

pod_spec(obj) = spec {
  obj.kind == "StatefulSet"
  spec := obj.spec.template.spec
}

pod_spec(obj) = spec {
  obj.kind == "DaemonSet"
  spec := obj.spec.template.spec
}

pod_spec(obj) = spec {
  obj.kind == "Job"
  spec := obj.spec.template.spec
}

pod_spec(obj) = spec {
  obj.kind == "CronJob"
  spec := obj.spec.jobTemplate.spec.template.spec
}

pod_spec(obj) = spec {
  obj.kind == "ReplicationController"
  spec := obj.spec.template.spec
}

pod_spec(obj) = spec {
  obj.kind == "PodTemplate"
  spec := obj.template.spec
}

all_containers[container] {
  spec := pod_spec(input)
  container := spec.containers[_]
}

all_containers[container] {
  spec := pod_spec(input)
  container := spec.initContainers[_]
}

effective_run_as_non_root(container, spec) = value {
  value := container.securityContext.runAsNonRoot
} else = value {
  value := spec.securityContext.runAsNonRoot
} else = false

has_justification(obj) {
  annotations := obj.metadata.annotations
  some key
  value := annotations[key]
  contains(lower(key), "justification")
  value != ""
}

violation_object(id, severity, resource, msg, recommendation) = output {
  output := {
    "msg": msg,
    "metadata": {
      "id": id,
      "severity": severity,
      "resource": resource,
      "recommendation": recommendation,
    },
  }
}

deny[violation] {
  spec := pod_spec(input)
  container := all_containers[_]
  container.securityContext.privileged == true
  resource := resource_identifier(input)
  msg := sprintf("Container %s is privileged.", [container_name(container)])
  violation := violation_object(
    "P2DP-K8S-001",
    "HIGH",
    resource,
    msg,
    "Remove privileged=true from the container securityContext.",
  )
}

deny[violation] {
  spec := pod_spec(input)
  spec.securityContext.runAsUser == 0
  resource := resource_identifier(input)
  violation := violation_object(
    "P2DP-K8S-002",
    "HIGH",
    resource,
    "Pod securityContext.runAsUser is set to root.",
    "Set runAsUser to a non-zero value or enforce runAsNonRoot.",
  )
}

deny[violation] {
  spec := pod_spec(input)
  container := all_containers[_]
  container.securityContext.runAsUser == 0
  resource := resource_identifier(input)
  msg := sprintf("Container %s sets runAsUser to root.", [container_name(container)])
  violation := violation_object(
    "P2DP-K8S-002",
    "HIGH",
    resource,
    msg,
    "Set runAsUser to a non-zero value or enforce runAsNonRoot.",
  )
}

deny[violation] {
  spec := pod_spec(input)
  container := all_containers[_]
  not effective_run_as_non_root(container, spec)
  resource := resource_identifier(input)
  msg := sprintf("Container %s does not set runAsNonRoot=true.", [container_name(container)])
  violation := violation_object(
    "P2DP-K8S-003",
    "MEDIUM",
    resource,
    msg,
    "Set runAsNonRoot: true at the pod or container level.",
  )
}

deny[violation] {
  spec := pod_spec(input)
  volume := spec.volumes[_]
  volume.hostPath
  resource := resource_identifier(input)
  volume_name := volume.name
  msg := sprintf("Volume %s uses hostPath.", [volume_name])
  violation := violation_object(
    "P2DP-K8S-004",
    "HIGH",
    resource,
    msg,
    "Use a PVC or emptyDir volume instead of hostPath.",
  )
}

deny[violation] {
  input.kind == "Service"
  input.spec.type == "LoadBalancer"
  not has_justification(input)
  resource := resource_identifier(input)
  violation := violation_object(
    "P2DP-K8S-005",
    "MEDIUM",
    resource,
    "Service type LoadBalancer requires justification.",
    "Provide a justification annotation or use ClusterIP.",
  )
}

deny[violation] {
  input.kind == "Service"
  input.spec.type == "NodePort"
  not has_justification(input)
  resource := resource_identifier(input)
  violation := violation_object(
    "P2DP-K8S-005",
    "MEDIUM",
    resource,
    "Service type NodePort requires justification.",
    "Provide a justification annotation or use ClusterIP.",
  )
}

deny[violation] {
  input.kind == "ClusterRoleBinding"
  input.roleRef.name == "cluster-admin"
  resource := resource_identifier(input)
  violation := violation_object(
    "P2DP-K8S-006",
    "HIGH",
    resource,
    "ClusterRoleBinding grants cluster-admin.",
    "Bind to a least-privilege ClusterRole instead of cluster-admin.",
  )
}

deny[violation] {
  input.kind == "RoleBinding"
  input.roleRef.name == "cluster-admin"
  resource := resource_identifier(input)
  violation := violation_object(
    "P2DP-K8S-006",
    "HIGH",
    resource,
    "RoleBinding grants cluster-admin.",
    "Bind to a least-privilege Role or ClusterRole instead of cluster-admin.",
  )
}
