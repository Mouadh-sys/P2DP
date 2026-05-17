from opentelemetry import trace


def get_tracer(name: str = "p2dp"):
    return trace.get_tracer(name)
