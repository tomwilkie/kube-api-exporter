#!/usr/bin/python3
#
# Kubernetes API Exporter - expose various numbers from the Kubernetes API as
# Prometheus metrics, such that you can alert on them.

import numbers, string, optparse, time, signal, logging, sys
import pykube, prometheus_client, prometheus_client.core


class KubernetesAPIExporter(object):

  def __init__(self, api):
    self.api = api
    self.gauge_cache = {}

  def collect(self):
    self.gauge_cache = {}

    for deployment in pykube.Deployment.objects(api).all():
      labels = labels_for_deployment(deployment.obj)
      self.record_ts_for_obj(deployment.obj, labels, path=["k8s", "deployment"])

    for gauge in self.gauge_cache.values():
      yield gauge

  def record_ts_for_obj(self, obj, labels, path=[]):
    for key, value in obj.items():
      key_path = list(path)
      key_path.append(key)

      if isinstance(value, dict):
        self.record_ts_for_obj(value, labels, path=key_path)

      elif isinstance(value, numbers.Number):
        label_keys, label_values = zip(*labels.items())
        metric_name = "_".join(key_path)
        if metric_name not in self.gauge_cache:
          gauge = prometheus_client.core.GaugeMetricFamily(metric_name, "Help text", labels=label_keys)
          self.gauge_cache[metric_name] = gauge
        else:
          gauge = self.gauge_cache[metric_name]
        gauge.add_metric(label_values, value)


def labels_for_deployment(dep):
  return {
    "namespace": safe_lookup(dep, ["metadata", "namespace"], default="default"),
    "name": safe_lookup(dep, ["metadata", "labels", "name"], default=""),
  }


def safe_lookup(d, ks, default=None):
  for k in ks:
    if k not in d:
      return default
    d = d[k]
  return d


def sigterm_handler(_signo, _stack_frame):
  sys.exit(0)


if __name__ == "__main__":
  parser =  optparse.OptionParser("""usage: %prog [options]""")
  parser.add_option("--port",
    dest="port", default=80,
    help="Port to serve HTTP interface")
  (options, args) = parser.parse_args()

  logging.info("Listening on %d", options.port)

  api = pykube.HTTPClient(pykube.KubeConfig.from_service_account())
  prometheus_client.REGISTRY.register(KubernetesAPIExporter(api))
  prometheus_client.start_http_server(options.port)

  signal.signal(signal.SIGTERM, sigterm_handler)
  while True:
    time.sleep(1)
