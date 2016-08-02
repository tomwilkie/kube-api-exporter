#!/usr/bin/python3

import numbers, string, optparse, time, signal, logging, sys
import pykube, prometheus_client, prometheus_client.core


class KubernetesAPICollector(object):

  def __init__(self, api):
    self.api = api

  def collect(self):
    for deployment in pykube.Deployment.objects(api).all():
      labels = labels_for_deployement(deployment.obj)
      for ts in ts_for_obj(deployment.obj, labels, path=["k8s", "deployment"]):
        yield ts


def labels_for_deployement(dep):
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


def ts_for_obj(obj, labels, path=[]):
  for key, value in obj.items():
    key_path = list(path)
    key_path.append(key)

    if isinstance(value, dict):
      for ts in ts_for_obj(value, labels, path=key_path):
        yield ts

    elif isinstance(value, numbers.Number):
      label_keys, label_values = zip(*labels.items())
      gauge = prometheus_client.core.GaugeMetricFamily("_".join(key_path), "Help text", labels=label_keys)
      gauge.add_metric(label_values, value)
      yield gauge


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
  prometheus_client.REGISTRY.register(KubernetesAPICollector(api))
  prometheus_client.start_http_server(options.port)

  signal.signal(signal.SIGTERM, sigterm_handler)
  while True:
    time.sleep(1)
