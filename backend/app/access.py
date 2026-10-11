"""Request roles are assigned by the backend, never by a submitted user ID."""


def hosted(request):
    return getattr(request.app.state, "hosted_app", False)


def private(request):
    if hosted(request):
        return getattr(request.state, "workspace", None) == "personal" and hasattr(request.state, "identity")
    return not request.app.state.public_demo and request.cookies.get("moniq_workspace") == "personal"


def demo(request):
    return not private(request) if hosted(request) else request.app.state.public_demo
