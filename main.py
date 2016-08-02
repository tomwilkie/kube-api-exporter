#!/usr/bin/python

import numbers, operator, string
import pykube
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY


class KubernetesAPICollector(object):

  def __init__(self, api):
    self.api = api

  def collect(self):
    for deployment in pykube.Deployment.objects(api):
      labels = labels_for_deployement(deployment)
      for ts in ts_for_obj(deployement, labels, path=["k8s", "deployment"]):
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
  for key, value in obj.iteritems():
    key_path = list(path)
    key_path.append(key)

    if isinstance(value, dict):
      for ts in ts_for_obj(value, labels, path=key_path):
        yield ts

    elif is_instance(value, labels, numbers.Number):
      label_keys, label_values = zip(*key_path.items())
      gauge = GaugeMetricFamily(string.join(path, "_"), labels=label_keys)
      gauge.add_metric(label_values, value)
      yield gauge


if __name__ == "__main__":
  parser =  optparse.OptionParser("""usage: %prog [options]""")
  parser.add_option("--port",
    dest="port", default=80,
    help="Port to serve HTTP interface")
  (options, args) = parser.parse_args()

  api = pykube.HTTPClient(pykube.KubeConfig.from_service_account())
  REGISTRY.register(KubernetesAPICollector(api))
  start_http_server(options.port)

