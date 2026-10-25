"""
Automated unit tests validating Kubernetes production manifests using standard library.
Ensures zero external dependency requirements for test execution.
"""

import os
import re
import subprocess
import unittest


class TestKubernetesManifests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def run_kustomize(self, target_dir: str) -> str:
        full_path = os.path.join(self.repo_root, target_dir)
        result = subprocess.run(
            ["kubectl", "kustomize", full_path],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout

    def test_base_kustomize_build(self):
        output = self.run_kustomize("base")
        self.assertIn("kind: Deployment", output)
        self.assertIn("kind: NetworkPolicy", output)
        self.assertIn("kind: Namespace", output)
        self.assertIn("kind: Ingress", output)
        self.assertIn("kind: HorizontalPodAutoscaler", output)
        self.assertIn("kind: PodDisruptionBudget", output)

    def test_dev_overlay_build(self):
        output = self.run_kustomize("overlays/dev")
        self.assertIn("dev-app.contoso.com", output)
        self.assertIn("letsencrypt-staging", output)
        self.assertIn("replicas: 1", output)

    def test_prod_overlay_build(self):
        output = self.run_kustomize("overlays/prod")
        self.assertIn("compliance: pci-dss", output)
        self.assertIn("replicas: 5", output)
        self.assertIn("cpu: 1000m", output)
        self.assertIn("memory: 1Gi", output)

    def test_zero_trust_network_policies(self):
        output = self.run_kustomize("base")
        self.assertIn("name: default-deny-all", output)
        self.assertIn("name: allow-dns-egress", output)
        self.assertIn("name: allow-ingress-to-frontend", output)

    def test_security_context_hardening(self):
        output = self.run_kustomize("overlays/prod")

        # 1. Non-root user enforcement
        self.assertTrue(re.search(r"runAsNonRoot:\s*true", output), "Must enforce runAsNonRoot")
        self.assertTrue(re.search(r"runAsUser:\s*10001", output), "Must run as unprivileged user 10001")

        # 2. Immutable root filesystem
        self.assertTrue(re.search(r"readOnlyRootFilesystem:\s*true", output), "Must enforce readOnlyRootFilesystem")

        # 3. Privilege escalation prevention
        self.assertTrue(re.search(r"allowPrivilegeEscalation:\s*false", output), "Must disallow privilege escalation")

        # 4. Capabilities drop ALL
        self.assertTrue(re.search(r"drop:\s*\n\s*-\s*ALL", output), "Must drop ALL capabilities")

        # 5. Availability & Probes
        self.assertTrue(re.search(r"livenessProbe:", output), "Must define liveness probe")
        self.assertTrue(re.search(r"readinessProbe:", output), "Must define readiness probe")
        self.assertTrue(re.search(r"startupProbe:", output), "Must define startup probe")


if __name__ == "__main__":
    unittest.main()
