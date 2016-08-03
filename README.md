# Kubernetes API Exporter for Prometheus

Kubernetes API Exporter - a Python job, delivered as a Docker image, that automatically exposes various numbers from the Kubernetes API as Prometheus metrics, such that you can alert on them.

This is useful when you are continually deploying changes from a CI pipeline to a Kubernetes cluster, and you want to generate alerts when a deployments fails.

For instance, the following deployment:

    $ kubectl get deployment helloworld -o json
    {
        "kind": "Deployment",
        "apiVersion": "extensions/v1beta1",
        "metadata": {
            "name": "helloworld",
            "namespace": "default",
            "generation": 2,
            ...
        },
        "spec": {
            "replicas": 1,
            ...
        },
        "status": {
            "observedGeneration": 2,
            "replicas": 1,
            "updatedReplicas": 1,
            "availableReplicas": 1
        }
    }

Is translated into the following Prometheus metrics:

    k8s_deployment_metadata_generation{name="helloworld",namespace="default"} 2.0
    k8s_deployment_spec_replicas{name="helloworld",namespace="default"} 1.0
    k8s_deployment_spec_strategy_rollingUpdate_maxSurge{name="helloworld",namespace="default"} 1.0
    k8s_deployment_spec_template_spec_terminationGracePeriodSeconds{name="helloworld",namespace="default"} 30.0
    k8s_deployment_status_availableReplicas{name="helloworld",namespace="default"} 1.0
    k8s_deployment_status_observedGeneration{name="helloworld",namespace="default"} 2.0
    k8s_deployment_status_replicas{name="helloworld",namespace="default"} 1.0
    k8s_deployment_status_updatedReplicas{name="helloworld",namespace="default"} 1.0

With this, you can configure the following rules to generate alerts when deployments fails:

    ALERT DeploymentGenerationMismatch
      IF          k8s_deployment_status_observedGeneration{job="kube-api-exporter"} != k8s_deployment_metadata_generation{job="kube-api-exporter"}
      FOR         5m
      LABELS      { severity="critical" }
      ANNOTATIONS {
        summary = "Deployment of {{$labels.exported_namespace}}/{{$labels.name}} failed",
        description = "Deployment of {{$labels.exported_namespace}}/{{$labels.name}} failed - observed generation != intended generation.",
      }

    ALERT DeploymentReplicasMismatch
      IF          k8s_deployment_spec_replicas{job="kube-api-exporter"} != k8s_deployment_status_availableReplicas{job="kube-api-exporter"}
      FOR         5m
      LABELS      { severity="critical" }
      ANNOTATIONS {
        summary = "Deployment of {{$labels.exported_namespace}}/{{$labels.name}} failed",
        description = "Deployment of {{$labels.exported_namespace}}/{{$labels.name}} failed - observed replicas != intended replicas.",
      }

# Installation

To run kube-api-exporter on your own cluster, clone this repo and run:

    $ kubectl create -f kube-api-exporter/k8s
