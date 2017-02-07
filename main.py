#!/usr/bin/python3
#
# Kubernetes API Exporter - expose various numbers from the Kubernetes API as
# Prometheus metrics, such that you can alert on them.

import numbers, string, optparse, time, signal, logging, sys, collections
import pykube, prometheus_client, prometheus_client.core

class KubernetesAPIExporter(object):

  def __init__(self, api):
    self.api = api
    self.gauge_cache = {}

  def collect(self):
    self.gauge_cache = {}

    for deployment in pykube.Deployment.objects(api).all():
      labels = labels_for(deployment.obj)
      self.record_ts_for_thing(deployment.obj, labels, ["k8s", "deployment"])

    for pod in pykube.Pod.objects(api).all():
      labels = labels_for(pod.obj)
      self.record_ts_for_thing(pod.obj, labels, ["k8s", "pod"])

    for job in pykube.Job.objects(api).all():
      labels = labels_for(job.obj)
      self.record_ts_for_thing(job.obj, labels, ["k8s", "job"])

    for pod in pykube.ReplicationController.objects(api).all():
      labels = labels_for(pod.obj)
      self.record_ts_for_thing(pod.obj, labels, ["k8s", "rc"])

    for pod in pykube.DaemonSet.objects(api).all():
      labels = labels_for(pod.obj)
      self.record_ts_for_thing(pod.obj, labels, ["k8s", "ds"])

    for gauge in self.gauge_cache.values():
      yield gauge

  def record_ts_for_thing(self, value, labels, path):
    if isinstance(value, dict):
      self.record_ts_for_obj(value, labels, path)

    elif isinstance(value, list):
      self.record_ts_for_list(value, labels, path)

    elif isinstance(value, numbers.Number):
      label_keys, label_values = zip(*labels.items())
      metric_name = "_".join(path)
      if metric_name not in self.gauge_cache:
        gauge = prometheus_client.core.GaugeMetricFamily(metric_name, "Help text", labels=label_keys)
        self.gauge_cache[metric_name] = gauge
      else:
        gauge = self.gauge_cache[metric_name]
      gauge.add_metric(label_values, float(value))

  def record_ts_for_obj(self, obj, labels, path):
    for key, value in obj.items():
      key_path = list(path)
      key_path.append(key)
      self.record_ts_for_thing(value, labels, key_path)

  def record_ts_for_list(self, ls, labels, path):
    key = path.pop()
    for i, value in enumerate(ls):
      labels = collections.OrderedDict(labels)
      labels[key] = str(i)
      self.record_ts_for_thing(value, labels, path)


class PodLabelExporter(object):

  def __init__(self, api):
    self.api = api

  def collect(self):
    metric = prometheus_client.core.GaugeMetricFamily("k8s_pod_labels", "Timeseries with the labels for the pod, always 1.0, for joining.")

    for pod in pykube.Pod.objects(api).all():
      unprocessed_labels = safe_lookup(pod.obj, ["metadata", "labels"], {})
      unprocessed_labels["namespace"] = safe_lookup(pod.obj, ["metadata", "namespace"], "default")
      unprocessed_labels["pod_name"] = safe_lookup(pod.obj, ["metadata", "name"])
      labels = {k.replace('-', '_').replace('/', '_').replace('.', '_'): v for k, v in unprocessed_labels.items()}
      metric.samples.append((metric.name, labels, 1.0))

    yield metric


def labels_for(obj):
  labels = collections.OrderedDict()
  labels["namespace"] = safe_lookup(obj, ["metadata", "namespace"], default="default")
  labels["name"] = safe_lookup(obj, ["metadata", "name"], default="")
  return labels


def safe_lookup(d, ks, default=None):
  for k in ks:
    if k not in d:
      return default
    d = d[k]
  return d


def sigterm_handler(_signo, _stack_frame):
  sys.exit(0)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)

  parser =  optparse.OptionParser("""usage: %prog [options]""")
  parser.add_option("--port",
    dest="port", default=80, type="int",
    help="Port to serve HTTP interface")
  (options, args) = parser.parse_args()

  logging.info("Listening on %d", options.port)

  api = pykube.HTTPClient(pykube.KubeConfig.from_service_account())
  api.config.contexts[api.config.current_context]["namespace"] = None # Hack to fetch objects from all namespaces
  prometheus_client.REGISTRY.register(KubernetesAPIExporter(api))
  prometheus_client.REGISTRY.register(PodLabelExporter(api))
  prometheus_client.start_http_server(options.port)

  signal.signal(signal.SIGTERM, sigterm_handler)
  while True:
    time.sleep(1)
