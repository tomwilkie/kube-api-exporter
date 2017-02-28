#!/usr/bin/python3
#
# Kubernetes API Exporter - expose various numbers from the Kubernetes API as
# Prometheus metrics, such that you can alert on them.

import numbers, optparse, time, signal, logging, sys, collections
import pykube, prometheus_client, prometheus_client.core


class KubernetesAPIExporter(object):

  KINDS = {
    'deployment': pykube.Deployment,
    'pod': pykube.Pod,
    'job': pykube.Job,
    'rc': pykube.ReplicationController,
    'ds': pykube.DaemonSet,
  }

  def __init__(self, api):
    self.api = api

  def collect(self):
    for tag, kind in self.KINDS.items():
      gauge_cache = {}

      for thing in kind.objects(self.api).all():
        labels = labels_for(thing.obj)
        self.record_ts_for_thing(thing.obj, labels, ["k8s", tag], gauge_cache)

      for gauge in gauge_cache.values():
        yield gauge

  def record_ts_for_thing(self, value, labels, path, gauge_cache):
    if isinstance(value, dict):
      self.record_ts_for_obj(value, labels, path, gauge_cache)

    elif isinstance(value, list):
      self.record_ts_for_list(value, labels, path, gauge_cache)

    elif isinstance(value, numbers.Number):
      label_keys, label_values = zip(*labels.items())
      metric_name = "_".join(path)
      if metric_name not in gauge_cache:
        gauge = prometheus_client.core.GaugeMetricFamily(metric_name, "Help text", labels=label_keys)
        gauge_cache[metric_name] = gauge
      else:
        gauge = gauge_cache[metric_name]
      gauge.add_metric(label_values, float(value))

  def record_ts_for_obj(self, obj, labels, path, gauge_cache):
    for key, value in obj.items():
      self.record_ts_for_thing(value, labels, path + [key], gauge_cache)

  def record_ts_for_list(self, ls, labels, path, gauge_cache):
    new_path, key = path[:-1], path[-1]
    for i, value in enumerate(ls):
      labels = collections.OrderedDict(labels)
      labels[key] = str(i)
      self.record_ts_for_thing(value, labels, new_path, gauge_cache)


class PodLabelExporter(object):

  def __init__(self, api):
    self.api = api

  def collect(self):
    metric = prometheus_client.core.GaugeMetricFamily("k8s_pod_labels", "Timeseries with the labels for the pod, always 1.0, for joining.")
    for pod in pykube.Pod.objects(self.api).all():
      metric.samples.append((metric.name, get_pod_labels(pod), 1.0))
    yield metric


def get_pod_labels(pod):
  metadata = pod.obj.get('metadata', {})
  unprocessed_labels = metadata.get('labels', {})
  unprocessed_labels.update({
    'namespace': metadata.get('namespace', "default"),
    'pod_name': metadata.get('name', "")
  })
  return {k.replace('-', '_').replace('/', '_').replace('.', '_'): v for k, v in unprocessed_labels.items()}


def labels_for(obj):
  metadata = obj.get('metadata', {})
  labels = collections.OrderedDict()
  labels["namespace"] = metadata.get('namespace', "default")
  labels["name"] = metadata.get('name', "")
  return labels


def sigterm_handler(_signo, _stack_frame):
  sys.exit(0)


def main():
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


if __name__ == '__main__':
  main()
