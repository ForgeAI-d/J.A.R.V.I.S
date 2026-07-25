from core.common import BaseComponent
from core.types import APIStatus, BuildStatus


class FakeComponent(BaseComponent):
    COMPONENT_ID = "testing.fake_component"
    NAME = "Fake Component"
    VERSION = "1.0.0"
    BUILD_STATUS = BuildStatus.COMPLETE
    API_STATUS = APIStatus.FROZEN
    CAPABILITIES = ("testing",)
