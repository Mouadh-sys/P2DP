package p2dp.kubernetes.security

violation[msg] {
  input.kind == "Pod"
  input.spec.containers[_].securityContext.privileged == true
  msg := "Privileged container is not allowed"
}
