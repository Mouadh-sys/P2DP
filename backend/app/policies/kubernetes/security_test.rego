package p2dp.kubernetes.security_test

import data.p2dp.kubernetes.security.deny

test_privileged_container if {
	count(deny) > 0 with input as {
		"kind": "Pod",
		"metadata": {"name": "bad-pod"},
		"spec": {"containers": [{
			"name": "app",
			"image": "nginx:1.25",
			"securityContext": {"privileged": true},
		}]},
	}
}

test_run_as_root if {
	count(deny) > 0 with input as {
		"kind": "Pod",
		"metadata": {"name": "root-pod"},
		"spec": {
			"securityContext": {"runAsUser": 0},
			"containers": [{"name": "app", "image": "nginx:1.25"}],
		},
	}
}

test_missing_run_as_non_root if {
	count(deny) > 0 with input as {
		"kind": "Pod",
		"metadata": {"name": "missing-non-root"},
		"spec": {"containers": [{"name": "app", "image": "nginx:1.25"}]},
	}
}

test_hostpath_volume if {
	count(deny) > 0 with input as {
		"kind": "Pod",
		"metadata": {"name": "hostpath-pod"},
		"spec": {
			"containers": [{"name": "app", "image": "nginx:1.25"}],
			"volumes": [{"name": "data", "hostPath": {"path": "/var/data"}}],
		},
	}
}

test_loadbalancer_without_justification if {
	count(deny) > 0 with input as {
		"kind": "Service",
		"metadata": {"name": "public-api"},
		"spec": {"type": "LoadBalancer", "ports": [{"port": 80}]},
	}
}

test_nodeport_without_justification if {
	count(deny) > 0 with input as {
		"kind": "Service",
		"metadata": {"name": "nodeport-api"},
		"spec": {"type": "NodePort", "ports": [{"port": 80}]},
	}
}

test_loadbalancer_with_justification if {
	count(deny) == 0 with input as {
		"kind": "Service",
		"metadata": {
			"name": "public-api",
			"annotations": {"p2dp.justification": "approved edge ingress"},
		},
		"spec": {"type": "LoadBalancer", "ports": [{"port": 80}]},
	}
}

test_cluster_admin_binding if {
	count(deny) > 0 with input as {
		"kind": "ClusterRoleBinding",
		"metadata": {"name": "admin-binding"},
		"roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "ClusterRole", "name": "cluster-admin"},
		"subjects": [{"kind": "ServiceAccount", "name": "default", "namespace": "default"}],
	}
}

test_compliant_pod if {
	count(deny) == 0 with input as {
		"kind": "Pod",
		"metadata": {"name": "good-pod"},
		"spec": {
			"securityContext": {"runAsNonRoot": true, "runAsUser": 10001},
			"containers": [{"name": "app", "image": "nginx:1.25"}],
		},
	}
}
